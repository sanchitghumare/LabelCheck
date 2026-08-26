from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import Any

from app.schemas.commodity import PackagedCommodity
from app.services.extraction.llm_fallback import extract_complex_fields
from app.services.extraction.regex_parser import parse_regex_fields
from app.services.extraction.confidence import build_confidence
from app.services.extraction.evidence import build_evidence
from app.schemas.extraction import ExtractionResult, FieldEvidence


ComplexFieldExtractor = Callable[[str], Mapping[str, Any]]

TEXT_KEYS = ("text", "raw_text", "ocr_text", "full_text")


def _box_sort_key(token: Mapping[str, Any]) -> tuple[int, int]:
    box = token.get("box")

    if isinstance(box, (list, tuple)) and len(box) == 4:
        return int(box[1]), int(box[0])

    return (0, 0)


class ExtractionOrchestrator:
    """
    Coordinates OCR reconstruction, deterministic extraction,
    confidence/evidence generation, and LLM fallback.

    Deterministic extraction is preferred for legally significant
    structured fields such as MRP, quantity and dates.
    """

    def __init__(
        self,
        llm_extractor: ComplexFieldExtractor = extract_complex_fields,
    ) -> None:
        self._llm_extractor = llm_extractor

    @staticmethod
    def _collect_ocr_lines(
        ocr_results: list[dict[str, Any]],
    ) -> list[str]:
        """Reconstruct horizontally ordered physical lines from OCR tokens."""

        grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
        plain_lines: list[str] = []

        for result in ocr_results:
            text = result.get("text", "").strip()
            line_id = result.get("line_id")

            if text and line_id is not None:
                key = (
                    tuple(line_id)
                    if isinstance(line_id, (tuple, list))
                    else (line_id,)
                )

                grouped[key].append(result)
                continue

            for text_key in TEXT_KEYS:
                value = result.get(text_key)

                if isinstance(value, str) and value.strip():
                    plain_lines.append(value.strip())
                    break

        reconstructed: list[tuple[int, int, str]] = []

        for tokens in grouped.values():
            ordered = sorted(
                tokens,
                key=lambda token: _box_sort_key(token)[1],
            )

            text = " ".join(
                token["text"].strip()
                for token in ordered
                if token["text"].strip()
            )

            if text:
                y, x = _box_sort_key(ordered[0])
                reconstructed.append((y, x, text))

        reconstructed.sort(key=lambda item: (item[0], item[1]))

        return [
            text for _, _, text in reconstructed
        ] + plain_lines

    @staticmethod
    def _should_use_llm(
        regex_fields: Mapping[str, Any],
    ) -> bool:
        """
        Decide whether the LLM fallback is actually necessary.

        The LLM is primarily useful for messy semantic fields such as
        manufacturer/contact information. If the deterministic parser
        already found the legally important structured fields, there is
        no reason to let the LLM reinterpret them.
        """

        required_complex_fields = (
            "manufacturer_name",
            "manufacturer_address",
            "consumer_care_contact",
        )

        return any(
            not regex_fields.get(field)
            for field in required_complex_fields
        )

    def process(
        self,
        ocr_results: list[dict[str, Any]],
    ) -> ExtractionResult:

        # ---------------------------------------------------------------
        # 1. Reconstruct OCR into physical reading-order lines
        # ---------------------------------------------------------------

        lines = self._collect_ocr_lines(ocr_results)

        if not lines:
            return ExtractionResult(
                commodity=PackagedCommodity.model_validate({}),
                confidence={},
                evidence={},
            )

        full_text = "\n".join(lines)

        # ---------------------------------------------------------------
        # 2. Deterministic extraction FIRST
        # ---------------------------------------------------------------

        regex_fields = parse_regex_fields(lines)

        # ---------------------------------------------------------------
        # 3. LLM ONLY when complex fields need help
        # ---------------------------------------------------------------

        llm_fields: Mapping[str, Any] = {}

        if self._should_use_llm(regex_fields):
            try:
                llm_fields = self._llm_extractor(full_text)
            except Exception as exc:
                # LLM failure must not destroy a valid deterministic result.
                print(f"LLM extraction failed: {exc}")

        # ---------------------------------------------------------------
        # 4. Merge carefully
        # ---------------------------------------------------------------

        merged: dict[str, Any] = {
            **llm_fields,
            **regex_fields,
        }

        # Remove internal parser metadata before validating the
        # Pydantic commodity model.
       
        # ---------------------------------------------------------------
        # 5. Build confidence
        # ---------------------------------------------------------------

        # For now use average OCR confidence when available.
        # Later this will become field-specific using bounding boxes.
        ocr_confidence = self._average_ocr_confidence(ocr_results)

        confidence = build_confidence(
            {
                key: value
                for key, value in merged.items()
                if value is not None
            },
            ocr_confidence=ocr_confidence,
        )

        # ---------------------------------------------------------------
        # 6. Build evidence
        # ---------------------------------------------------------------

        evidence = {
            key: FieldEvidence.model_validate(value)
            for key, value in build_evidence(
                merged,
                full_text,
                confidence=confidence,
            ).items()
        }
        merged.pop("_mrp_meta", None)
        # These will eventually move into a dedicated audit/extraction
        # response schema. For now keep them available without sending
        # them into PackagedCommodity.
        print("\n--- EXTRACTION CONFIDENCE ---")
        print(confidence)

        print("\n--- EXTRACTION EVIDENCE ---")
        print(evidence)

        # ---------------------------------------------------------------
        # 7. Validate final commodity
        # ---------------------------------------------------------------

        commodity = PackagedCommodity.model_validate(merged)

        return ExtractionResult(
            commodity=commodity,
            confidence=confidence,
            evidence=evidence,
        )

    @staticmethod
    def _average_ocr_confidence(
        ocr_results: list[dict[str, Any]],
    ) -> float | None:
        """
        Calculate average OCR confidence.

        Supports common keys used by OCR engines:
            confidence
            score
        """

        values: list[float] = []

        for result in ocr_results:
            value = result.get("confidence")

            if value is None:
                value = result.get("score")

            if value is None:
                continue

            try:
                value = float(value)
            except (TypeError, ValueError):
                continue

            # Some OCR systems return 0-100 instead of 0-1.
            if value > 1:
                value /= 100.0

            if 0 <= value <= 1:
                values.append(value)

        if not values:
            return None

        return sum(values) / len(values)