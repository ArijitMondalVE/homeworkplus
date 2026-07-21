"""
Tutor Agent — LLM-powered homework tutor using GPT-4o or Claude.
Generates detailed explanations, hints, and step-by-step solutions.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger

from app.config import settings


TUTOR_SYSTEM_PROMPT = """You are HomeworkPlus AI Tutor, an expert educational assistant for students.

Your role:
- Explain concepts clearly and at the student's level
- Provide step-by-step solutions with detailed explanations
- Use examples and analogies to make concepts easier to understand
- Encourage the student and boost their confidence
- If a question involves math, include LaTeX notation wrapped in $...$ for inline or $$...$$ for display
- Always check your work and be accurate

Response format (JSON):
{
  "answer": "Main answer text",
  "steps": ["Step 1...", "Step 2...", "Step 3..."],
  "hints": ["Hint 1...", "Hint 2..."],
  "explanation": "Detailed conceptual explanation",
  "latex": "LaTeX equation if applicable",
  "confidence": 0.95
}
"""


class TutorAgent:
    """Multi-LLM tutor agent with GPT-4o primary and Claude fallback."""

    def __init__(self):
        self._openai_client = None
        self._anthropic_client = None

    def _get_openai(self):
        if self._openai_client is None and settings.OPENAI_API_KEY:
            from langchain_openai import ChatOpenAI
            self._openai_client = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.3,
                max_tokens=4096,
            )
        return self._openai_client

    def _get_anthropic(self):
        if self._anthropic_client is None and settings.ANTHROPIC_API_KEY:
            from langchain_anthropic import ChatAnthropic
            self._anthropic_client = ChatAnthropic(
                model=settings.ANTHROPIC_MODEL,
                api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.3,
                max_tokens=4096,
            )
        return self._anthropic_client

    async def generate_answer(
        self,
        question: str,
        context: str | None = None,
        rag_sources: list[dict] | None = None,
        language: str = "en",
        question_type: str = "general",
        image_path: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a comprehensive answer with steps, hints, and explanation.
        """
        prompt = self._build_prompt(question, context, rag_sources, language, question_type)

        if settings.PRIMARY_LLM == "anthropic":
            llm = self._get_anthropic()
        else:
            llm = self._get_openai()

        if llm is None:
            # Try any available LLM in priority order
            llm = self._get_openai() or self._get_anthropic()

        if llm is None:
            logger.warning("[TutorAgent] No LLM configured, using mock response")
            return self._mock_response(question)

        try:
            # Build messages: use multimodal format if image is provided and supported
            if image_path and (settings.PRIMARY_LLM in ["openai", "anthropic"]):
                import base64
                try:
                    mime_type = "image/jpeg"
                    if image_path.lower().endswith(".png"):
                        mime_type = "image/png"
                    elif image_path.lower().endswith(".webp"):
                        mime_type = "image/webp"
                    elif image_path.lower().endswith(".gif"):
                        mime_type = "image/gif"
                    
                    with open(image_path, "rb") as f:
                        base64_image = base64.b64encode(f.read()).decode("utf-8")
                    
                    content = [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            }
                        }
                    ]
                    messages = [
                        SystemMessage(content=TUTOR_SYSTEM_PROMPT),
                        HumanMessage(content=content)
                    ]
                except Exception as img_err:
                    logger.warning(f"[TutorAgent] Multimodal content building failed: {img_err}")
                    messages = [
                        SystemMessage(content=TUTOR_SYSTEM_PROMPT),
                        HumanMessage(content=prompt)
                    ]
            else:
                messages = [
                    SystemMessage(content=TUTOR_SYSTEM_PROMPT),
                    HumanMessage(content=prompt)
                ]

            response = await llm.ainvoke(messages)
            content = response.content

            # Try to parse JSON response
            result = self._parse_llm_response(content)
            result["llm_provider"] = settings.PRIMARY_LLM
            result["llm_model"] = settings.OPENAI_MODEL if settings.PRIMARY_LLM == "openai" else settings.ANTHROPIC_MODEL
            result["tokens_used"] = response.usage_metadata.get("total_tokens", 0) if hasattr(response, "usage_metadata") else 0

            logger.info(f"[TutorAgent] Generated answer for: {question[:60]}...")
            return result

        except Exception as e:
            logger.error(f"[TutorAgent] LLM call failed: {e}")
            # Try fallback LLM
            return await self._fallback_generate(question, prompt, e)

    async def _fallback_generate(self, question: str, prompt: str, original_error: Exception) -> dict[str, Any]:
        """Try alternate LLM if primary fails."""
        fallback = self._get_anthropic() if settings.PRIMARY_LLM == "openai" else self._get_openai()
        if fallback is None:
            return self._mock_response(question)

        try:
            messages = [
                SystemMessage(content=TUTOR_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            response = await fallback.ainvoke(messages)
            result = self._parse_llm_response(response.content)
            result["llm_provider"] = "anthropic" if settings.PRIMARY_LLM == "openai" else "openai"
            return result
        except Exception as e2:
            logger.error(f"[TutorAgent] Fallback LLM also failed: {e2}")
            return self._mock_response(question)

    def _build_prompt(
        self,
        question: str,
        context: str | None,
        rag_sources: list[dict] | None,
        language: str,
        question_type: str,
    ) -> str:
        parts = []
        if language != "en":
            parts.append(f"Please respond in {language}.")
        parts.append(f"Question Type: {question_type}")
        parts.append(f"\nStudent Question:\n{question}")

        if rag_sources:
            sources_text = "\n\n".join([
                f"[Source: {s.get('title', 'Textbook')}]\n{s.get('content', '')}"
                for s in rag_sources[:3]
            ])
            parts.append(f"\n\nRelevant Textbook Content:\n{sources_text}")

        if context:
            parts.append(f"\n\nAdditional Context:\n{context}")

        parts.append("\n\nPlease provide a comprehensive answer in the JSON format specified.")
        return "\n".join(parts)

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """Parse JSON from LLM response, with fallback to plain text."""
        import json
        import re

        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    "answer": data.get("answer", content),
                    "steps": data.get("steps", []),
                    "hints": data.get("hints", []),
                    "explanation": data.get("explanation", ""),
                    "latex": data.get("latex"),
                    "confidence": data.get("confidence", 0.85),
                }
            except json.JSONDecodeError:
                pass

        return {
            "answer": content,
            "steps": [],
            "hints": [],
            "explanation": "",
            "latex": None,
            "confidence": 0.75,
        }

    def _mock_response(self, question: str) -> dict[str, Any]:
        """Mock response when no LLM is configured."""
        return {
            "answer": f"[Mock] This is a placeholder answer for: {question[:100]}. Please configure an LLM API key.",
            "steps": ["Step 1: Configure OPENAI_API_KEY in .env", "Step 2: Restart the server"],
            "hints": ["Check your .env file", "See the README for setup instructions"],
            "explanation": "LLM not configured.",
            "latex": None,
            "confidence": 0.0,
            "llm_provider": "mock",
            "llm_model": "none",
            "tokens_used": 0,
        }

    async def generate_chat_response(
        self,
        messages: list[dict],
        session_id: str,
        language: str = "en",
    ) -> dict[str, Any]:
        """Generate a conversational response for the chat tutor."""
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        llm = self._get_openai() or self._get_anthropic()
        if llm is None:
            return {"reply": "LLM not configured.", "tokens_used": 0}

        lc_messages = [SystemMessage(content=TUTOR_SYSTEM_PROMPT)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        response = await llm.ainvoke(lc_messages)
        return {
            "reply": response.content,
            "tokens_used": response.usage_metadata.get("total_tokens", 0) if hasattr(response, "usage_metadata") else 0,
        }
