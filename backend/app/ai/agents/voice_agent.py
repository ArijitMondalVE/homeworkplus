"""
Voice Agent — Whisper STT and TTS for voice tutoring.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from loguru import logger

from app.config import settings


class VoiceAgent:
    """Speech-to-text (Whisper) and text-to-speech (gTTS/OpenAI TTS) agent."""

    def __init__(self):
        self._whisper_model = None

    def _get_whisper(self, model_size: str = "base"):
        if self._whisper_model is None:
            try:
                import whisper
                self._whisper_model = whisper.load_model(model_size)
                logger.info(f"[VoiceAgent] Whisper model '{model_size}' loaded")
            except ImportError:
                logger.warning("[VoiceAgent] openai-whisper not installed")
        return self._whisper_model

    async def transcribe(self, audio_path: str, language: str = "en") -> dict[str, Any]:
        """
        Transcribe audio file to text using Whisper.
        Returns {text, language, confidence, segments}.
        """
        logger.info(f"[VoiceAgent] Transcribing: {audio_path}")

        # Try OpenAI API (standard transcription mechanism)
        if settings.OPENAI_API_KEY:
            return await self._transcribe_openai_api(audio_path, language)

        logger.warning("[VoiceAgent] OpenAI API Key is missing and local whisper fallback is removed.")
        return {"text": "", "language": language, "confidence": 0, "segments": [], "engine": "none"}

    async def _transcribe_openai_api(self, audio_path: str, language: str) -> dict[str, Any]:
        """Use OpenAI Whisper API for transcription."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            with open(audio_path, "rb") as audio_file:
                response = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language if language != "auto" else None,
                    response_format="verbose_json",
                )
            return {
                "text": response.text,
                "language": getattr(response, "language", language),
                "confidence": 0.95,
                "segments": getattr(response, "segments", []),
                "engine": "openai_api",
            }
        except Exception as e:
            logger.error(f"[VoiceAgent] OpenAI Whisper API failed: {e}")
            return {"text": "", "language": language, "confidence": 0, "segments": [], "engine": "error"}

    async def text_to_speech(
        self,
        text: str,
        output_path: str | None = None,
        language: str = "en",
        voice: str = "alloy",
    ) -> str | None:
        """
        Convert text to speech. Returns path to audio file.
        Uses OpenAI TTS API if available, else gTTS.
        """
        if output_path is None:
            output_path = tempfile.mktemp(suffix=".mp3", dir=settings.UPLOAD_DIR)

        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Try OpenAI TTS
        if settings.OPENAI_API_KEY:
            result = await self._tts_openai(text, output_path, voice)
            if result:
                return result

        # Fallback to gTTS
        return self._tts_gtts(text, output_path, language)

    async def _tts_openai(self, text: str, output_path: str, voice: str = "alloy") -> str | None:
        """Use OpenAI TTS API."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text[:4096],  # API limit
            )
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.info(f"[VoiceAgent] OpenAI TTS → {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"[VoiceAgent] OpenAI TTS failed: {e}")
            return None

    def _tts_gtts(self, text: str, output_path: str, language: str = "en") -> str | None:
        """Use gTTS (Google Text-to-Speech) as fallback."""
        try:
            from gtts import gTTS
            tts = gTTS(text=text[:5000], lang=language, slow=False)
            tts.save(output_path)
            logger.info(f"[VoiceAgent] gTTS → {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"[VoiceAgent] gTTS failed: {e}")
            return None
