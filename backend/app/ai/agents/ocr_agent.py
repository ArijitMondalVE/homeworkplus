"""
OCR Agent — Extract text from images using EasyOCR and PaddleOCR.
Falls back between engines for maximum accuracy.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger


class OCRAgent:
    """
    Multi-engine OCR agent:
    - Primary: EasyOCR (handwritten + printed)
    - Fallback: PaddleOCR (high accuracy for printed)
    """

    def __init__(self, languages: list[str] | None = None):
        self.languages = languages or ["en"]
        self._easy_ocr = None
        self._paddle_ocr = None

    def _get_easyocr(self):
        if self._easy_ocr is None:
            try:
                import easyocr
                self._easy_ocr = easyocr.Reader(self.languages, gpu=False)
                logger.info("[OCRAgent] EasyOCR initialized")
            except ImportError:
                logger.warning("[OCRAgent] EasyOCR not installed")
        return self._easy_ocr

    def _get_paddleocr(self):
        if self._paddle_ocr is None:
            try:
                import os
                os.environ["FLAGS_use_onednn"] = "0"
                from paddleocr import PaddleOCR
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
                logger.info("[OCRAgent] PaddleOCR initialized")
            except ImportError:
                logger.warning("[OCRAgent] PaddleOCR not installed")
        return self._paddle_ocr

    def extract_text(self, image_path: str, engine: str = "easyocr") -> dict[str, Any]:
        """
        Extract text from image.
        Returns: {text, confidence, engine, words, boxes}
        """
        logger.info(f"[OCRAgent] Extracting text from {image_path} using {engine}")

        if engine == "easyocr":
            return self._extract_easyocr(image_path)
        elif engine == "paddleocr":
            return self._extract_paddleocr(image_path)
        else:
            # Try EasyOCR first, fallback to PaddleOCR
            result = self._extract_easyocr(image_path)
            if result["confidence"] < 0.5:
                logger.info("[OCRAgent] Low confidence, falling back to PaddleOCR")
                paddle_result = self._extract_paddleocr(image_path)
                if paddle_result["confidence"] > result["confidence"]:
                    return paddle_result
            return result

    def _extract_easyocr(self, image_path: str) -> dict[str, Any]:
        reader = self._get_easyocr()
        if reader is None:
            return {"text": "", "confidence": 0.0, "engine": "easyocr", "words": [], "boxes": []}

        try:
            results = reader.readtext(image_path, detail=1, paragraph=False)
            words = []
            confidences = []
            boxes = []

            for (bbox, text, conf) in results:
                words.append(text)
                confidences.append(conf)
                boxes.append(bbox)

            full_text = " ".join(words)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": full_text,
                "confidence": avg_conf,
                "engine": "easyocr",
                "words": words,
                "boxes": boxes,
            }
        except Exception as e:
            logger.error(f"[OCRAgent] EasyOCR failed: {e}")
            return {"text": "", "confidence": 0.0, "engine": "easyocr", "words": [], "boxes": []}

    def _extract_paddleocr(self, image_path: str) -> dict[str, Any]:
        paddle = self._get_paddleocr()
        if paddle is None:
            return {"text": "", "confidence": 0.0, "engine": "paddleocr", "words": [], "boxes": []}

        try:
            results = paddle.ocr(image_path, cls=True)
            words = []
            confidences = []
            boxes = []

            if results and results[0]:
                for line in results[0]:
                    box, (text, conf) = line
                    words.append(text)
                    confidences.append(conf)
                    boxes.append(box)

            full_text = "\n".join(words)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": full_text,
                "confidence": avg_conf,
                "engine": "paddleocr",
                "words": words,
                "boxes": boxes,
            }
        except Exception as e:
            logger.error(f"[OCRAgent] PaddleOCR failed: {e}")
            return {"text": "", "confidence": 0.0, "engine": "paddleocr", "words": [], "boxes": []}

    def extract_with_best_engine(self, image_path: str) -> dict[str, Any]:
        """Run both engines and return the higher confidence result."""
        easy_result = self._extract_easyocr(image_path)
        paddle_result = self._extract_paddleocr(image_path)

        if paddle_result["confidence"] > easy_result["confidence"]:
            logger.info(f"[OCRAgent] PaddleOCR wins: {paddle_result['confidence']:.2f}")
            return paddle_result

        logger.info(f"[OCRAgent] EasyOCR wins: {easy_result['confidence']:.2f}")
        return easy_result
