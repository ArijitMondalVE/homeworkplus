"""
Photo-to-Answer Pipeline Orchestrator.
Runs the full pipeline: Upload → Vision → OCR → Math → RAG → LLM → Voice → Answer
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from loguru import logger

from app.ai.agents.vision_agent import VisionAgent
from app.ai.agents.ocr_agent import OCRAgent
from app.ai.agents.math_agent import MathAgent
from app.ai.agents.tutor_agent import TutorAgent
from app.ai.agents.rag_agent import RAGAgent
from app.ai.agents.voice_agent import VoiceAgent


class PhotoAnswerPipeline:
    """
    Orchestrates the full Photo-to-Answer workflow:

    1. OpenCV Enhancement (VisionAgent)
    2. PII Detection (VisionAgent)
    3. OCR Extraction (OCRAgent)
    4. Math Detection & LaTeX Conversion (MathAgent)
    5. Question Classification (MathAgent)
    6. RAG Knowledge Retrieval (RAGAgent)
    7. LLM Answer Generation (TutorAgent)
    8. (Optional) TTS Voice Output (VoiceAgent)
    """

    def __init__(self):
        self.vision = VisionAgent()
        self.ocr = OCRAgent()
        self.math = MathAgent()
        self.tutor = TutorAgent()
        self.rag = RAGAgent()
        self.voice = VoiceAgent()

    async def process(
        self,
        image_path: str,
        user_id: str,
        language: str = "en",
        include_voice: bool = False,
        include_whiteboard: bool = False,
    ) -> dict[str, Any]:
        """
        Run the complete Photo-to-Answer pipeline.
        Returns a comprehensive result dict.
        """
        start_time = time.time()
        pipeline_id = str(uuid.uuid4())

        logger.info(f"[Pipeline:{pipeline_id}] Starting Photo-to-Answer for {image_path}")
        result: dict[str, Any] = {
            "pipeline_id": pipeline_id,
            "image_path": image_path,
            "steps_completed": [],
            "error": None,
        }

        try:
            # ── Step 1: Vision Enhancement ────────────────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 1: Vision Enhancement")
            enhanced_path, vision_meta = self.vision.enhance_image(image_path)
            result["enhanced_path"] = enhanced_path
            result["has_math"] = vision_meta.get("has_math", False)
            result["has_diagram"] = vision_meta.get("has_diagram", False)
            result["steps_completed"].append("vision_enhancement")

            # ── Step 2: OCR Extraction ────────────────────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 2: OCR Extraction")
            ocr_result = self.ocr.extract_with_best_engine(enhanced_path)
            extracted_text = ocr_result.get("text", "")
            result["ocr_text"] = extracted_text
            result["ocr_confidence"] = ocr_result.get("confidence", 0)
            result["ocr_engine"] = ocr_result.get("engine", "unknown")
            result["steps_completed"].append("ocr_extraction")

            if not extracted_text.strip():
                result["error"] = "Could not extract text from image"
                return result

            # ── Step 3: PII Detection ─────────────────────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 3: PII Detection")
            has_pii, clean_text = self.vision.detect_pii(extracted_text)
            result["has_pii"] = has_pii
            question_text = clean_text
            result["steps_completed"].append("pii_detection")

            # ── Step 4: Math OCR & LaTeX Conversion ───────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 4: Math Analysis")
            is_math = self.math.is_math_content(question_text)
            latex_text = None
            math_solution = None

            if is_math:
                latex_text = self.math.text_to_latex(question_text)
                try:
                    math_solution = self.math.solve_equation(question_text)
                except Exception:
                    pass

            result["is_math"] = is_math
            result["latex_text"] = latex_text
            result["math_solution"] = math_solution
            result["steps_completed"].append("math_analysis")

            # ── Step 5: Question Classification ───────────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 5: Question Classification")
            question_type = self.math.classify_question_type(question_text)
            result["question_type"] = question_type
            result["steps_completed"].append("classification")

            # ── Step 6: RAG Knowledge Retrieval ───────────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 6: RAG Retrieval")
            rag_sources = self.rag.search_similar(question_text, top_k=3)
            result["rag_sources"] = rag_sources
            result["steps_completed"].append("rag_retrieval")

            # ── Step 7: LLM Answer Generation ─────────────────────────
            logger.info(f"[Pipeline:{pipeline_id}] Step 7: LLM Answer Generation")
            context = math_solution["solution"] if math_solution and math_solution.get("solution") else None
            llm_result = await self.tutor.generate_answer(
                question=question_text,
                context=context,
                rag_sources=rag_sources,
                language=language,
                question_type=question_type,
                image_path=enhanced_path,
            )

            result["answer"] = llm_result.get("answer", "")
            result["steps"] = llm_result.get("steps", [])
            result["hints"] = llm_result.get("hints", [])
            result["explanation"] = llm_result.get("explanation", "")
            result["latex"] = llm_result.get("latex") or latex_text
            result["confidence"] = llm_result.get("confidence", 0)
            result["llm_provider"] = llm_result.get("llm_provider")
            result["tokens_used"] = llm_result.get("tokens_used", 0)
            result["steps_completed"].append("llm_generation")

            # ── Step 8: Optional TTS Voice ────────────────────────────
            if include_voice and result["answer"]:
                logger.info(f"[Pipeline:{pipeline_id}] Step 8: TTS Generation")
                voice_text = f"{result['answer']}. {result.get('explanation', '')}"
                voice_path = await self.voice.text_to_speech(voice_text[:1000], language=language)
                if voice_path:
                    import os
                    filename = os.path.basename(voice_path)
                    result["voice_url"] = f"http://localhost:8000/uploads/{filename}"
                else:
                    result["voice_url"] = None
                result["steps_completed"].append("tts_generation")

            # ── Done ──────────────────────────────────────────────────
            elapsed_ms = int((time.time() - start_time) * 1000)
            result["processing_time_ms"] = elapsed_ms
            result["question_text"] = question_text

            logger.info(
                f"[Pipeline:{pipeline_id}] Complete in {elapsed_ms}ms. "
                f"Steps: {', '.join(result['steps_completed'])}"
            )
            return result

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(f"[Pipeline:{pipeline_id}] Failed after {elapsed_ms}ms: {e}")
            result["error"] = str(e)
            result["processing_time_ms"] = elapsed_ms
            return result
