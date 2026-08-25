"""
app/services/vision/preprocessor.py

Image ingestion and preprocessing utilities for the Legal Metrology
compliance vision pipeline.

Scope (strict):
    - Accept raw image bytes or a file path.
    - Resize to a sane maximum width to bound memory/CPU usage.
    - Convert to grayscale.
    - Apply CLAHE to normalize contrast / suppress glare from glossy
      plastic packaging.

Explicitly out of scope: barcode calibration, OCR, NLP parsing,
database or API routing code. See calibrator.py and ocr.py.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Sane default cap on image width (pixels). Large phone/camera captures
# (4000px+) are downscaled to this before any further processing to keep
# OCR and barcode detection fast and memory-bounded.
DEFAULT_MAX_WIDTH: int = 1600

# CLAHE tuning. clipLimit controls contrast amplification; tileGridSize
# controls the local neighborhood size used for equalization.
DEFAULT_CLAHE_CLIP_LIMIT: float = 2.0
DEFAULT_CLAHE_TILE_GRID_SIZE: tuple[int, int] = (8, 8)

ImageInput = Union[bytes, bytearray, str, Path]


class ImageDecodeError(ValueError):
    """Raised when input bytes/path cannot be decoded into a valid image."""


def _load_image(image_input: ImageInput) -> np.ndarray:
    """
    Load an image from raw bytes or a filesystem path into a BGR
    cv2/numpy array.

    Args:
        image_input: Raw image bytes (e.g. from an uploaded file) or a
            path to an image file on disk.

    Returns:
        A BGR numpy array as returned by cv2.imread / cv2.imdecode.

    Raises:
        ImageDecodeError: If the input cannot be decoded into a valid
            image (corrupt file, unsupported format, empty buffer, or
            a path that does not resolve to an image).
    """
    if isinstance(image_input, (bytes, bytearray)):
        if not image_input:
            raise ImageDecodeError("Received empty image byte buffer.")
        buffer = np.frombuffer(image_input, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise ImageDecodeError(
                "Failed to decode image from bytes; buffer is not a "
                "valid/supported image format."
            )
        return image

    if isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            raise ImageDecodeError(f"Image path does not exist: {path}")
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            raise ImageDecodeError(
                f"Failed to decode image at path: {path} "
                "(unsupported or corrupt file)."
            )
        return image

    raise ImageDecodeError(
        f"Unsupported image_input type: {type(image_input)!r}. "
        "Expected bytes, bytearray, str, or Path."
    )


def _resize_to_max_width(
    image: np.ndarray, max_width: int = DEFAULT_MAX_WIDTH
) -> np.ndarray:
    """
    Downscale an image so its width does not exceed max_width, preserving
    aspect ratio. Images already narrower than max_width are returned
    unchanged (no upscaling, to avoid introducing interpolation artifacts
    that could distort measured font heights).

    Args:
        image: BGR or grayscale numpy image array.
        max_width: Maximum allowed width in pixels.

    Returns:
        The resized (or original) image array.
    """
    height, width = image.shape[:2]
    if width <= max_width:
        return image

    scale_factor = max_width / float(width)
    new_width = max_width
    new_height = max(1, int(round(height * scale_factor)))

    resized = cv2.resize(
        image, (new_width, new_height), interpolation=cv2.INTER_AREA
    )
    logger.debug(
        "Resized image from %sx%s to %sx%s (scale_factor=%.4f)",
        width,
        height,
        new_width,
        new_height,
        scale_factor,
    )
    return resized


def _apply_clahe(
    gray_image: np.ndarray,
    clip_limit: float = DEFAULT_CLAHE_CLIP_LIMIT,
    tile_grid_size: tuple[int, int] = DEFAULT_CLAHE_TILE_GRID_SIZE,
) -> np.ndarray:
    """
    Apply Contrast Limited Adaptive Histogram Equalization to a
    single-channel (grayscale) image. This locally normalizes contrast,
    which helps recover embossed/printed text detail washed out by glare
    or specular highlights on glossy plastic/foil packaging.

    Args:
        gray_image: Single-channel grayscale numpy image array.
        clip_limit: Threshold for contrast limiting (higher = more
            aggressive local contrast boost).
        tile_grid_size: Size of the grid for histogram equalization
            (rows, cols).

    Returns:
        The CLAHE-equalized single-channel image array.
    """
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(gray_image)


def preprocess_image(
    image_input: ImageInput,
    max_width: int = DEFAULT_MAX_WIDTH,
    clahe_clip_limit: float = DEFAULT_CLAHE_CLIP_LIMIT,
    clahe_tile_grid_size: tuple[int, int] = DEFAULT_CLAHE_TILE_GRID_SIZE,
) -> np.ndarray:
    """
    Full preprocessing pipeline: load -> resize -> grayscale -> CLAHE.

    This is the single entry point downstream services (calibrator.py,
    ocr.py) should call to obtain a clean, analysis-ready image array.

    Args:
        image_input: Raw image bytes or a filesystem path to the source
            product-label image.
        max_width: Maximum output width in pixels; larger images are
            downscaled preserving aspect ratio.
        clahe_clip_limit: CLAHE contrast clip limit.
        clahe_tile_grid_size: CLAHE tile grid size.

    Returns:
        A single-channel (grayscale) numpy array with CLAHE applied,
        ready for barcode calibration and OCR.

    Raises:
        ImageDecodeError: If the input image cannot be loaded/decoded.
    """
    raw_image = _load_image(image_input)
    resized_image = _resize_to_max_width(raw_image, max_width=max_width)

    if len(resized_image.shape) == 3:
        gray_image = cv2.cvtColor(resized_image, cv2.COLOR_BGR2GRAY)
    else:
        gray_image = resized_image

    equalized_image = _apply_clahe(
        gray_image,
        clip_limit=clahe_clip_limit,
        tile_grid_size=clahe_tile_grid_size,
    )

    logger.info(
        "Preprocessed image: final shape=%s dtype=%s",
        equalized_image.shape,
        equalized_image.dtype,
    )
    return equalized_image