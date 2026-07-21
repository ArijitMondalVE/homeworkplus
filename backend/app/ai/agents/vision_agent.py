"""
Vision Agent — OpenCV image enhancement and preprocessing.
Enhances image quality before OCR: denoising, deskewing, binarization.
"""
import base64
import io
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from loguru import logger


class VisionAgent:
    """Preprocesses uploaded images for optimal OCR accuracy."""

    def enhance_image(self, image_path: str) -> tuple[str, dict]:
        """
        Full enhancement pipeline:
        1. Load image
        2. Convert to grayscale
        3. Denoise
        4. Deskew
        5. Adaptive threshold (binarization)
        6. Save enhanced image

        Returns: (enhanced_path, metadata_dict)
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Cannot read image: {image_path}")

            original_shape = img.shape
            logger.info(f"[VisionAgent] Processing image {image_path}, shape={original_shape}")

            # Step 1: Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Step 2: Denoise
            denoised = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

            # Step 3: Deskew
            deskewed = self._deskew(denoised)

            # Step 4: Adaptive threshold for binarization
            binary = cv2.adaptiveThreshold(
                deskewed, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Step 5: Morphological cleanup
            kernel = np.ones((1, 1), np.uint8)
            cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # Save enhanced image
            enhanced_path = self._save_enhanced(image_path, cleaned)

            # Detect if image has diagrams or math symbols
            has_lines = self._detect_lines(img)
            has_math = self._detect_math_symbols(gray)

            metadata = {
                "original_shape": original_shape,
                "enhanced_path": enhanced_path,
                "has_diagram": has_lines,
                "has_math": has_math,
                "processing_steps": ["grayscale", "denoise", "deskew", "threshold", "morphology"],
            }

            logger.info(f"[VisionAgent] Enhancement complete → {enhanced_path}")
            return enhanced_path, metadata

        except Exception as e:
            logger.error(f"[VisionAgent] Enhancement failed: {e}")
            return image_path, {"error": str(e), "has_diagram": False, "has_math": False}

    def _deskew(self, gray: np.ndarray) -> np.ndarray:
        """Correct image skew using Hough line detection."""
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
            if lines is None:
                return gray

            angles = []
            for line in lines[:10]:
                rho, theta = line[0]
                angle = (theta - np.pi / 2) * (180 / np.pi)
                if abs(angle) < 45:
                    angles.append(angle)

            if not angles:
                return gray

            median_angle = np.median(angles)
            if abs(median_angle) < 0.5:
                return gray

            h, w = gray.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated
        except Exception:
            return gray

    def _detect_lines(self, img: np.ndarray, threshold: int = 50) -> bool:
        """Detect if image likely contains diagrams/graphs."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=threshold, minLineLength=50, maxLineGap=10)
        return lines is not None and len(lines) > 5

    def _detect_math_symbols(self, gray: np.ndarray) -> bool:
        """Simple heuristic — high symbol density suggests math content."""
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        small_contours = [c for c in contours if 5 < cv2.contourArea(c) < 500]
        density = len(small_contours) / (gray.shape[0] * gray.shape[1]) * 1e6
        return density > 20

    def _save_enhanced(self, original_path: str, enhanced_img: np.ndarray) -> str:
        """Save enhanced image with _enhanced suffix."""
        p = Path(original_path)
        enhanced_path = str(p.parent / f"{p.stem}_enhanced{p.suffix}")
        cv2.imwrite(enhanced_path, enhanced_img)
        return enhanced_path

    def detect_pii(self, text: str) -> tuple[bool, str]:
        """
        Basic PII detection — flag if text contains phone numbers, emails, or ID-like patterns.
        Returns (has_pii, redacted_text).
        """
        import re
        redacted = text
        patterns = [
            (r"\b\d{10}\b", "[PHONE]"),
            (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]"),
        ]
        has_pii = False
        for pattern, replacement in patterns:
            if re.search(pattern, redacted):
                has_pii = True
                redacted = re.sub(pattern, replacement, redacted)
        return has_pii, redacted

    def image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string for LLM vision APIs."""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
