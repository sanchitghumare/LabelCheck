from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import Any

from app.schemas.commodity import PackagedCommodity
from app.services.extraction.llm_fallback import extract_complex_fields
from app.services.extraction.regex_parser import parse_regex_fields

ComplexFieldExtractor = Callable[[str], Mapping[str, Any]]
TEXT_KEYS = ("text", "raw_text", "ocr_text", "full_text")


def _box_sort_key(token: Mapping[str, Any]) -> tuple[int, int]:
    box = token.get("box")
    if isinstance(box, (list, tuple)) and len(box) == 4:
        return int(box[1]), int(box[0])
    return (0, 0)


class ExtractionOrchestrator:
    """Combines complete OCR lines, deterministic parsing, and LLM fallback."""

    def __init__(self, llm_extractor: ComplexFieldExtractor = extract_complex_fields) -> None:
        self._llm_extractor = llm_extractor

    @staticmethod
    def _collect_ocr_lines(ocr_results: list[dict[str, Any]]) -> list[str]:
        """Reconstruct horizontally ordered physical lines from OCR tokens."""
        grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        plain_lines: list[str] = []

        for result in ocr_results:
            text = result.get("text", "").strip()
            line_id = result.get("line_id")
            if text and line_id is not None:
                # Convert a JSON-decoded list ID to a stable hashable key.
                key = tuple(line_id) if isinstance(line_id, (tuple, list)) else (line_id,)
                grouped[key].append(result)
                continue
            for text_key in TEXT_KEYS:
                value = result.get(text_key)
                if isinstance(value, str) and value.strip():
                    plain_lines.append(value.strip())
                    break

        reconstructed: list[tuple[int, int, str]] = []
        for tokens in grouped.values():
            ordered = sorted(tokens, key=lambda token: _box_sort_key(token)[1])
            text = " ".join(token["text"].strip() for token in ordered if token["text"].strip())
            if text:
                y, x = _box_sort_key(ordered[0])
                reconstructed.append((y, x, text))

        # Tesseract's block numbering is not necessarily visual reading order;
        # OCR geometry makes line ordering stable for both regex and the LLM.
        reconstructed.sort(key=lambda item: (item[0], item[1]))
        return [text for _, _, text in reconstructed] + plain_lines

    def process(self, ocr_results: list[dict[str, Any]]) -> PackagedCommodity:
        lines = self._collect_ocr_lines(ocr_results)
        full_text = "\n".join(lines)
        regex_fields = parse_regex_fields(lines)
        llm_fields = self._llm_extractor(full_text)
        # Deterministic fields take precedence; the full joined context is sent
        # to both parsers so a field is never evaluated as an isolated token.
        return PackagedCommodity.model_validate({**llm_fields, **regex_fields})
