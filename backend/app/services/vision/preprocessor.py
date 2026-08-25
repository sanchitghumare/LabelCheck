"""Image preprocessing tailored to printed and dot-matrix package labels."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MAX_WIDTH = 1600
DOT_MATRIX_SCALE = 2
DEFAULT_CLAHE_CLIP_LIMIT = 2.0
DEFAULT_CLAHE_TILE_GRID_SIZE = (8, 8)
ImageInput = Union[bytes, bytearray, str, Path]


class ImageDecodeError(ValueError):
    """Raised when an image input cannot be decoded."""


def _load_image(image_input: ImageInput) -> np.ndarray:
    if isinstance(image_input, (bytes, bytearray)):
        if not image_input:
            raise ImageDecodeError("Received an empty image byte buffer.")
        image = cv2.imdecode(np.frombuffer(image_input, np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(image_input, (str, Path)):
        path = Path(image_input)
        if not path.exists():
            raise ImageDecodeError(f"Image path does not exist: {path}")
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    else:
        raise ImageDecodeError(
            f"Unsupported image_input type: {type(image_input)!r}. "
            "Expected bytes, bytearray, str, or Path."
        )
    if image is None:
        raise ImageDecodeError("Could not decode the supplied image.")
    return image


def _resize_to_max_width(image: np.ndarray, max_width: int) -> np.ndarray:
    height, width = image.shape[:2]
    if max_width <= 0 or width <= max_width:
        return image
    scale = max_width / float(width)
    return cv2.resize(
        image, (max_width, max(1, round(height * scale))), interpolation=cv2.INTER_AREA
    )


def preprocess_image(
    image_input: ImageInput,
    max_width: int = DEFAULT_MAX_WIDTH,
    clahe_clip_limit: float = DEFAULT_CLAHE_CLIP_LIMIT,
    clahe_tile_grid_size: tuple[int, int] = DEFAULT_CLAHE_TILE_GRID_SIZE,
) -> np.ndarray:
    """Decode and prepare a label image for Tesseract.

    Contrast is increased before a small blur and closing operation join
    detached dot-matrix ink dots. Bicubic upscaling gives Tesseract usable
    character strokes without the block artefacts of nearest-neighbour resize.
    """
    image = _resize_to_max_width(_load_image(image_input), max_width)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    enhanced = cv2.createCLAHE(
        clipLimit=clahe_clip_limit, tileGridSize=clahe_tile_grid_size
    ).apply(gray)

    height, width = enhanced.shape[:2]
    upscaled = cv2.resize(
        enhanced,
        (width * DOT_MATRIX_SCALE, height * DOT_MATRIX_SCALE),
        interpolation=cv2.INTER_CUBIC,
    )
    smoothed = cv2.GaussianBlur(upscaled, (3, 3), 0)
    bridged = cv2.morphologyEx(
        smoothed, cv2.MORPH_CLOSE, np.ones((2, 2), dtype=np.uint8)
    )
    logger.info("Preprocessed image from %s to %s", image.shape, bridged.shape)
    return bridged
