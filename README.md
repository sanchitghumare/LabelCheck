# LabelCheck

**Automated Legal Metrology compliance scanner for pre-packaged commodities.**

Smart India Hackathon 2026 · Problem Statement **SIH26034** · Team **TechTonic**
Ministry of Consumer Affairs, Food & Public Distribution

---

## What this is

A system that reads the label of a pre-packaged commodity from a photograph and verifies it against the mandatory declarations required by **Rule 6 and Rule 9 of the Legal Metrology (Packaged Commodities) Rules, 2011**.

The output is not a score. It is a verdict naming the specific declaration that is missing or non-conforming, with the extracted evidence attached — so a Legal Metrology officer can act on it, and a manufacturer can contest it.

## Design principle

> **AI extracts. Rules decide.**

Optical character recognition and field mapping are probabilistic and can be wrong. The compliance decision is not. Extracted fields are passed to a **deterministic rule engine** with no machine learning in the decision path, so every verdict is reproducible and traceable to a specific requirement.

Where extraction confidence falls below threshold, the package is routed to **manual review** rather than receiving a verdict. The system does not guess about legal compliance.

## Pipeline

```
1. Scan capture       phone camera / bulk upload · auto-crop, deskew
        ↓
2. Pre-processing     glare and blur handling · label region detection
        ↓
3. Text extraction    vision OCR · multi-script (Latin, Devanagari, regional)
        ↓
4. Field mapping      regex for MRP, quantity, date · LLM fallback for messy text
        ↓
5. Confidence gate    per-field score vs threshold  ──low──▶  Manual review
        ↓
6. Rule engine        deterministic checks  ◀──  rules.json (versioned config)
        ↓
   ┌────┴────┐
Compliant   Violation report
   └────┬────┘
        ↓
7. Audit record       image + fields + rule outcome + timestamp
```

## Repository contents

| File | Purpose |
|---|---|
| `rules.json` | The Rule 6 declarations encoded as machine-readable checks |
| `README.md` | This file |

`rules.json` is the core artifact. It encodes each mandatory declaration with its requirement, whether it is unconditional or conditional, the check that determines compliance, and the message emitted on failure. It also encodes scope exemptions and the e-commerce variant under Rule 6(10).

## Declarations checked

| # | Declaration | Required |
|---|---|---|
| 1 | Name and complete address of manufacturer / packer / importer | Always |
| 2 | Common or generic name of the commodity | Always |
| 3 | Net quantity in standard units | Always |
| 4 | Month and year of manufacture or packing | Always |
| 5 | Retail sale price (MRP), inclusive of all taxes | Always |
| 6 | Consumer care details | Always |
| 7 | Country of origin | Imported packages |
| 8 | Unit sale price | Unless exempt under Rule 6(11) |

## Out of scope for v1

Deliberately deferred, with reasons:

- **Rule 9 — legibility and prominence.** Requires assessment of contrast and placement, not presence alone.
- **Rule 9 / Rule 7 — minimum letter and numeral height.** Requires real-world scale calibration from a photograph.
- **Altered date markings.** Would be flagged for manual inspection only, never auto-rejected.
- **Departmental workflow integration.** Requires access to existing inspection systems.

## Rules as configuration

The Rules are amended by notification. `rules.json` is versioned configuration, not hard-coded logic, so an amendment is a config change rather than a code change and a redeploy.

## Status

Ruleset drafted. Clause references are being verified against the consolidated Rules published by the Department of Consumer Affairs; entries marked `VERIFY` in `rules.json` are not yet confirmed against the gazette text.

## References

- Legal Metrology (Packaged Commodities) Rules, 2011 — Department of Consumer Affairs
- Legal Metrology Act, 2009
- SIH 2026 Problem Statement SIH26034 — Ministry of Consumer Affairs, Food & Public Distribution

## Team

**TechTonic** — Smart India Hackathon 2026
