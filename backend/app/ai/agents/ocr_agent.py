"""
OCR Agent — Extract text from images using EasyOCR.
Includes math symbol normalization for handwritten equations.
"""
from __future__ import annotations

from typing import Any

from loguru import logger
from app.config import settings


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
                import paddle
                try:
                    paddle.set_flags({"FLAGS_use_onednn": 0})
                except Exception as flag_err:
                    logger.debug(f"[OCRAgent] Failed to set paddle flags: {flag_err}")
                from paddleocr import PaddleOCR
                self._paddle_ocr = PaddleOCR(use_angle_cls=True, lang="en")
                logger.info("[OCRAgent] PaddleOCR initialized")
            except ImportError:
                logger.warning("[OCRAgent] PaddleOCR not installed")
        return self._paddle_ocr

    def extract_text(self, image_path: str, engine: str = "easyocr") -> dict[str, Any]:
        """
        Extract text from image.
        Returns: {text, confidence, engine, words, boxes}
        """
        if settings.OPENAI_API_KEY:
            engine = "gpt4o"

        logger.info(f"[OCRAgent] Extracting text from {image_path} using {engine}")

        if engine == "gpt4o":
            return self._extract_gpt4o(image_path)
        elif engine == "easyocr":
            return self._extract_easyocr(image_path)
        elif engine == "paddleocr":
            return self._extract_paddleocr(image_path)
        elif engine == "tesseract":
            return self._extract_tesseract(image_path)
        else:
            return self.extract_with_best_engine(image_path)

    def normalize_math_ocr(self, words: list[str], boxes: list) -> tuple[list[str], str]:
        """
        Fix common OCR misreads in math/handwritten expressions.
        Returns (normalized_words, normalized_full_text).
        """
        import re

        # Step 1: Per-word symbol normalization
        normalized = []
        for w in words:
            # Division symbols → /
            w = w.replace('÷', '/').replace('\u00f7', '/')
            # Multiplication symbols → *
            w = w.replace('×', '*').replace('\u00d7', '*').replace('\u22c5', '*')
            # Minus/dash variants
            w = w.replace('\u2212', '-').replace('\u2014', '-').replace('\u2013', '-')
            # Common OCR confusions in math context
            w = w.replace('O', '0') if re.fullmatch(r'O', w) else w   # standalone O → 0
            w = w.replace('l', '1') if re.fullmatch(r'l', w) else w   # standalone l → 1
            # x as multiply only when sandwiched between numbers (handled below)
            normalized.append(w)

        # Step 2: Detect vertical fractions from spatial layout
        # If two numbers are vertically stacked (same x-center, different y), merge as a/b
        merged_words = self._merge_vertical_fractions(normalized, boxes)

        # Step 3: Join and clean up
        full_text = " ".join(merged_words)

        # Step 4: Regex fixes on full expression
        # "60 + 1 6 x 2" → catch lone digits that were fraction parts
        # standalone x between digits → *
        full_text = re.sub(r'(\d)\s+[xX]\s+(\d)', r'\1 * \2', full_text)
        # ÷ that survived → /
        full_text = re.sub(r'[÷\u00f7]', '/', full_text)
        # × that survived → *
        full_text = re.sub(r'[×\u00d7\u22c5]', '*', full_text)
        # "1 / 6" with spaces → keep as is (valid)
        # Remove stray equal signs at start
        full_text = re.sub(r'^\s*=\s*', '', full_text)
        # Remove lone question marks
        full_text = re.sub(r'\s*\?\s*$', '', full_text).strip()

        logger.debug(f"[OCRAgent] Math normalized: {' '.join(words)!r} → {full_text!r}")
        return merged_words, full_text

    def _merge_vertical_fractions(self, words: list[str], boxes: list) -> list[str]:
        """
        Detect numbers stacked vertically (fraction bar implicit) and merge as 'a/b'.
        boxes is a list of bounding polygons [[x1,y1],[x2,y2],[x3,y3],[x4,y4]].
        """
        if not boxes or len(words) != len(boxes):
            return words

        import re

        def center(box):
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            return sum(xs) / len(xs), sum(ys) / len(ys)

        merged = list(words)
        used = set()

        for i in range(len(words)):
            if i in used:
                continue
            if not re.fullmatch(r'\d+', words[i]):
                continue
            cx_i, cy_i = center(boxes[i])
            for j in range(len(words)):
                if j == i or j in used:
                    continue
                if not re.fullmatch(r'\d+', words[j]):
                    continue
                cx_j, cy_j = center(boxes[j])
                # Same horizontal center (within 20px), different vertical center (>15px apart)
                if abs(cx_i - cx_j) < 20 and abs(cy_i - cy_j) > 15:
                    top, bottom = (i, j) if cy_i < cy_j else (j, i)
                    merged[top] = f"{words[top]}/{words[bottom]}"
                    used.add(bottom)
                    merged[bottom] = ""
                    break

        return [w for w in merged if w != ""]

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

            # Apply math symbol normalization and vertical fraction detection
            _, full_text = self.normalize_math_ocr(words, boxes)
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
            results = paddle.ocr(image_path)
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

    def _extract_tesseract(self, image_path: str) -> dict[str, Any]:
        """Extract text using pytesseract."""
        try:
            import pytesseract
            import shutil
            import os
            from PIL import Image

            if not shutil.which("tesseract"):
                default_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                ]
                for path in default_paths:
                    if os.path.exists(path):
                        pytesseract.pytesseract.tesseract_cmd = path
                        break

            img = Image.open(image_path)
            # Fetch structured layout details to calculate confidence and retrieve words
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            
            confidences = []
            words = []
            for i, word in enumerate(data.get('text', [])):
                if word.strip():
                    words.append(word)
                    conf = data.get('conf', [])[i]
                    if conf != -1 and conf != '-1':
                        confidences.append(float(conf))

            # Apply math symbol normalization
            _, full_text = self.normalize_math_ocr(words, [])
            avg_conf = (sum(confidences) / len(confidences)) / 100.0 if confidences else 0.0

            return {
                "text": full_text,
                "confidence": avg_conf,
                "engine": "tesseract",
                "words": words,
                "boxes": [],
            }
        except Exception as e:
            logger.error(f"[OCRAgent] Tesseract failed: {e}")
            return {"text": "", "confidence": 0.0, "engine": "tesseract", "words": [], "boxes": []}

    def _extract_gpt4o(self, image_path: str) -> dict[str, Any]:
        """Extract text from image using GPT-4o Vision API directly to save RAM."""
        try:
            import base64
            from openai import OpenAI

            if not settings.OPENAI_API_KEY:
                logger.warning("[OCRAgent] No OpenAI key for GPT-4o vision OCR")
                return {"text": "", "confidence": 0.0, "engine": "gpt4o", "words": [], "boxes": []}

            mime_type = "image/jpeg"
            if image_path.lower().endswith(".png"):
                mime_type = "image/png"
            elif image_path.lower().endswith(".webp"):
                mime_type = "image/webp"

            with open(image_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode("utf-8")

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise OCR agent. Extract all text, equations, and math formulas from the image. Normalize division signs to / and multiplication signs to *. Do not add conversational text. Only reply with the extracted text."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text and equations from this image:"},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{mime_type};base64,{base64_image}"}
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.0
            )
            
            extracted_text = response.choices[0].message.content.strip()
            return {
                "text": extracted_text,
                "confidence": 0.99,
                "engine": "gpt4o",
                "words": extracted_text.split(),
                "boxes": []
            }
        except Exception as e:
            logger.error(f"[OCRAgent] GPT-4o Vision OCR failed: {e}")
            return {"text": "", "confidence": 0.0, "engine": "gpt4o", "words": [], "boxes": []}

    def extract_with_best_engine(self, image_path: str) -> dict[str, Any]:
        """Run all available engines and return the higher confidence result."""
        if settings.OPENAI_API_KEY:
            logger.info("[OCRAgent] Using GPT-4o Vision as the best engine for OCR")
            return self._extract_gpt4o(image_path)

        results = []
        
        # EasyOCR
        try:
            results.append(self._extract_easyocr(image_path))
        except Exception as e:
            logger.error(f"[OCRAgent] EasyOCR run failed: {e}")
            
        # PaddleOCR
        try:
            results.append(self._extract_paddleocr(image_path))
        except Exception as e:
            logger.error(f"[OCRAgent] PaddleOCR run failed: {e}")
            
        # Tesseract
        try:
            results.append(self._extract_tesseract(image_path))
        except Exception as e:
            logger.error(f"[OCRAgent] Tesseract run failed: {e}")

        # Filter out empty results and pick the one with highest confidence
        valid_results = [r for r in results if r.get("text")]
        if not valid_results:
            return {"text": "", "confidence": 0.0, "engine": "none", "words": [], "boxes": []}
            
        best_result = max(valid_results, key=lambda r: r["confidence"])
        logger.info(f"[OCRAgent] Best engine choice: {best_result['engine']} (confidence: {best_result['confidence']:.2f})")
        return best_result
