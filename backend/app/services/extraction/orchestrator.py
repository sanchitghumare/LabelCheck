from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from app.schemas.commodity import PackagedCommodity
from app.services.extraction.llm_fallback import extract_complex_fields
from app.services.extraction.regex_parser import parse_regex_fields

ComplexFieldExtractor = Callable[[str], Mapping[str, Any]]

TEXT_KEYS = ("text", "raw_text", "ocr_text", "full_text")


class ExtractionOrchestrator:
    """Combines deterministic parsing with local-LLM extraction."""

    def __init__(
        self,
        llm_extractor: ComplexFieldExtractor = extract_complex_fields,
    ) -> None:
        self._llm_extractor = llm_extractor

    @staticmethod
    def _collect_ocr_lines(ocr_results: list[dict[str, Any]]) -> list[str]:
        lines: list[str] = []

        for result in ocr_results:
            for key in TEXT_KEYS:
                value = result.get(key)
                if isinstance(value, str) and value.strip():
                    lines.append(value.strip())
                    break

        return lines

    def process(self, ocr_results: list[dict[str, Any]]) -> PackagedCommodity:
        """
        Return a validated commodity contract.

        Expected OCR input items include one of: ``text``, ``raw_text``,
        ``ocr_text``, or ``full_text``.
        """
        lines = self._collect_ocr_lines(ocr_results)

        regex_fields = parse_regex_fields(lines)

        # Full label context is retained for address continuity; the LLM prompt
        # asks only for fields that regex extraction deliberately does not own.
        remaining_text = "\n".join(lines)
        llm_fields = self._llm_extractor(remaining_text)

        merged = {
            **llm_fields,
            **regex_fields,  # Deterministic values always take precedence.
        }
        return PackagedCommodity.model_validate(merged)