"""
Translation Agent — Multi-language question/answer translation.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from app.config import settings

SUPPORTED_LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "zh": "Chinese", "hi": "Hindi", "ar": "Arabic", "pt": "Portuguese",
    "ru": "Russian", "ja": "Japanese", "ko": "Korean", "bn": "Bengali",
    "ur": "Urdu", "id": "Indonesian", "tr": "Turkish",
}


class TranslationAgent:
    """Translate questions and answers using OpenAI LLM."""

    async def translate(
        self,
        text: str,
        target_language: str,
        source_language: str = "auto",
    ) -> dict[str, Any]:
        """
        Translate text to target language.
        Returns {translated_text, detected_language, confidence}.
        """
        if target_language == "en" and source_language == "en":
            return {"translated_text": text, "detected_language": "en", "confidence": 1.0}

        target_name = SUPPORTED_LANGUAGES.get(target_language, target_language)

        if settings.OPENAI_API_KEY:
            return await self._translate_openai(text, target_name, source_language)

        return {"translated_text": text, "detected_language": source_language, "confidence": 0.0}

    async def _translate_openai(
        self, text: str, target_language_name: str, source_language: str
    ) -> dict[str, Any]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            prompt = f"Translate the following text to {target_language_name}. Return only the translated text, nothing else:\n\n{text}"

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional translator."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.1,
            )

            translated = response.choices[0].message.content.strip()
            return {
                "translated_text": translated,
                "detected_language": source_language,
                "confidence": 0.95,
            }
        except Exception as e:
            logger.error(f"[TranslationAgent] Translation failed: {e}")
            return {"translated_text": text, "detected_language": source_language, "confidence": 0.0}

    def get_supported_languages(self) -> dict[str, str]:
        return SUPPORTED_LANGUAGES
