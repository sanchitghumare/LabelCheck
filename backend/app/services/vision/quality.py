"""Image-quality checks performed before OCR."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class ImageQualityResult:
    """Quality measurements used to decide whether an image is OCR-ready."""

    is_acceptable: bool
    width_px: int
    height_px: int
    blur_score: float
    brightness: float
    contrast: float
    issues: list[str]


# These are intentionally conservative starting points.
# Tune them using real uploaded label images.
MIN_WIDTH_PX = 500
MIN_HEIGHT_PX = 500
MIN_BLUR_SCORE = 40.0
MIN_BRIGHTNESS = 35.0
MAX_BRIGHTNESS = 225.0
MIN_CONTRAST = 20.0


def assess_image_quality(image: np.ndarray) -> ImageQualityResult:
    """
    Assess whether an image is reasonably suitable for OCR.

    The function does not modify the image.
    """

    if image is None or image.size == 0:
        return ImageQualityResult(
            is_acceptable=False,
            width_px=0,
            height_px=0,
            blur_score=0.0,
            brightness=0.0,
            contrast=0.0,
            issues=["Image is empty or could not be decoded."],
        )

    if image.ndim == 2:
        gray = image
    elif image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        return ImageQualityResult(
            is_acceptable=False,
            width_px=0,
            height_px=0,
            blur_score=0.0,
            brightness=0.0,
            contrast=0.0,
            issues=["Unsupported image format."],
        )

    height, width = gray.shape[:2]

    # Variance of Laplacian is a simple and widely used blur indicator.
    # Higher values generally mean sharper edges.
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    issues: list[str] = []

    if width < MIN_WIDTH_PX or height < MIN_HEIGHT_PX:
        issues.append(
            f"Image resolution is too low ({width}x{height}px)."
        )

    if blur_score < MIN_BLUR_SCORE:
        issues.append(
            f"Image may be blurry (blur score {blur_score:.1f})."
        )

    if brightness < MIN_BRIGHTNESS:
        issues.append(
            f"Image is too dark (brightness {brightness:.1f})."
        )
    elif brightness > MAX_BRIGHTNESS:
        issues.append(
            f"Image is too bright (brightness {brightness:.1f})."
        )

    if contrast < MIN_CONTRAST:
        issues.append(
            f"Image has low contrast (contrast {contrast:.1f})."
        )

    return ImageQualityResult(
        is_acceptable=not issues,
        width_px=width,
        height_px=height,
        blur_score=round(blur_score, 2),
        brightness=round(brightness, 2),
        contrast=round(contrast, 2),
        issues=issues,
    )