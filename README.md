# LabelCheck

**Automated Legal Metrology compliance scanner for pre-packaged commodities.**

**Smart India Hackathon 2026** · Problem Statement **SIH26034** · Team **TechTonic**
Ministry of Consumer Affairs, Food & Public Distribution

---

## What this is

LabelCheck is an automated auditing system that reads the label of a pre-packaged commodity from a photograph and verifies it against the mandatory declarations required by **Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011**.

The output is a reproducible compliance verdict naming the specific declaration that is missing or non-conforming, complete with attached extraction evidence. This gives Legal Metrology officers unambiguous grounds for enforcement, while providing manufacturers with clear, auditable points to contest.

---

## Design Principle

> **AI extracts. Rules decide.**

Optical character recognition (OCR) and text field mapping are probabilistic and error-prone. The compliance decision must not be.

- **Deterministic Rule Engine** — Extracted text fields are routed to a deterministic rule engine with zero machine learning in the final decision loop. Every verdict remains auditable, traceable, and legally reproducible.
- **Controlled Fallback** — If extraction confidence metrics fall below the configurable threshold, the package drops out of the automated pipeline and is routed to **manual review** rather than receiving an unverified automated verdict.
- **Audit-First Philosophy** — Eliminates black-box AI guesswork from statutory legal evaluations.

---

## Pipeline

```text
1. Scan Capture
   Phone camera / bulk upload · auto-crop · deskew
                         │
                         ▼
2. Pre-processing
   Glare and blur handling · image quality assessment
                         │
                         ▼
3. Text Extraction
   OCR · bounding box evaluation · physical line reconstruction
                         │
                         ▼
4. Field Mapping
   Regex for MRP, quantity, dates · LLM fallback for
   complex manufacturer details and consumer-care data
                         │
                         ▼
5. Confidence & Evidence
   Field confidence scoring · extraction evidence isolation
                         │
               ┌─────────┴─────────┐
               │                   │
        High confidence       Low confidence
               │                   │
               ▼                   ▼
        Rule Engine          Manual Review
               │
               ▼
6. Physical Measurement
   Scale calibration · net-quantity font-height measurement
   · physical size conversion from pixels to millimetres
                         │
                         ▼
7. Compliance Evaluation
   Deterministic Legal Metrology boundary verification
                         │
               ┌─────────┴─────────┐
               │                   │
               ▼                   ▼
          COMPLIANT           NON_COMPLIANT
                                   │
                                   ▼
                            Violation Report
                                   │
                                   ▼
8. Audit Record
   Extracted fields · evidence · rule execution traces ·
   calibration data · physical measurements · timestamp
```

---

## System Architecture

```text
                    ┌─────────────────┐
                    │    Frontend     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   FastAPI API   │
                    └────────┬────────┘
                             │
                             ▼
              ┌────────────────────────────┐
              │       Scan Service         │
              └─────────────┬──────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌───────────┐   ┌────────────┐
        │  Vision  │    │ Extraction│   │ Compliance │
        │  Service │    │  Pipeline │   │   Engine   │
        └─────┬────┘    └─────┬─────┘   └──────┬─────┘
              │               │                │
              ▼               ▼                ▼
       OCR + Bounding    Regex + LLM         Rules
       Boxes + Scale
       + Measurements
              │               │                │
              └───────────────┼────────────────┘
                               ▼
                        ┌──────────────┐
                        │ Audit Record │
                        └───────┬──────┘
                                │
                                ▼
                          ┌───────────┐
                          │  MongoDB  │
                          └───────────┘
```

---

## Repository Structure

```text
LabelCheck/
│
├── backend/
│   ├── app/
│   │   ├── api/          # REST endpoints for scan triggering and report retrieval
│   │   ├── core/         # Core application configuration and infrastructure
│   │   ├── modules/      # Application-level scan, review, and reporting modules
│   │   ├── schemas/      # Pydantic schemas for verification and compliance payloads
│   │   └── services/     # Vision, extraction, compliance, audit, and persistence services
│   │
│   ├── requirements.txt  # Backend dependencies
│   └── ...
│
├── frontend/
│   ├── src/               # React frontend application components
│   ├── public/            # Static assets
│   └── ...
│
├── rules.json             # Version-controlled regulatory ruleset matrix
├── README.md              # Project documentation
└── ...
```

---

## Core Components

### Backend

The backend runs the entire image-processing, extraction, physical-measurement, and compliance pipeline:

- **Image Processing** — Image quality assessment with glare, blur, brightness, and contrast analysis.
- **OCR & Field Isolation** — Text extraction coupled with bounding-box analysis and geometric text-line reconstruction.
- **Hybrid Extraction Engine** — Multi-step architecture using high-speed regex for structured fields, with LLM fallback for complex manufacturer and consumer-care information.
- **Confidence & Evidence** — Field-level confidence scoring and extraction evidence generation to make every extracted value traceable.
- **Scale Calibration** — Determines the relationship between image pixels and physical millimetres using barcode-based calibration where available, with a controlled fallback when calibration is unavailable.
- **Font-Height Measurement** — Measures the pixel height of the detected net-quantity declaration and converts that measurement into physical millimetres using the calibrated image scale.
- **Deterministic Rule Engine** — Validates extracted declarations and physical measurements against configured Legal Metrology requirements.
- **Persistence** — Auditable MongoDB persistence layer capturing scan metadata, extracted fields, confidence scores, evidence, rule results, calibration information, and physical measurements.

### Frontend

The user-facing portal manages the application workflows:

- **Capture Interface** — Image upload supporting direct phone-camera inputs and batch uploads.
- **Visual Audit Explorer** — Side-by-side verification interface highlighting extraction regions alongside the compliance result.
- **Review Queue Workspace** — Human-in-the-loop interface for low-confidence and edge-case results.
- **Compliance Report** — Displays the final verdict, failed rules, extracted declarations, confidence, and supporting evidence.

---

## Rules Configuration

| File / Module | Purpose |
|---|---|
| `rules.json` | Machine-readable declarative matrix matching Legal Metrology requirements |
| `backend/` | Application APIs, vision processing, extraction, compliance, and data models |
| `frontend/` | Dashboard, manual inspection, and report interfaces |

The `rules.json` file decouples evolving statutory regulations from hardcoded application logic:

- Explicitly defines mandatory fields, situational exemptions, and distinct e-commerce variants under Rule 6(10).
- Amending guidelines across the platform requires zero changes to the core compliance logic; updates are handled through configuration versioning, allowing historical audits to preserve references to the ruleset active at the time of evaluation.

---

## Mandated Declarations Checked

| # | Declaration Type | Requirement Scope |
|---|---|---|
| 1 | Name and complete physical address of manufacturer / packer / importer | Always mandatory |
| 2 | Common or generic name of the commodity enclosed | Always mandatory |
| 3 | Net quantity declared in standard SI units of measurement | Always mandatory |
| 4 | Month and year of original manufacture or packaging | Always mandatory |
| 5 | Retail sale price (MRP), explicitly inclusive of all statutory taxes | Always mandatory |
| 6 | Comprehensive consumer care contact details | Always mandatory |
| 7 | Country of origin | Explicitly for imported commodities |
| 8 | Unit sale price calculation breakdown | Mandatory unless exempted via Rule 6(11) |

---

## Physical Measurement

LabelCheck does not only determine whether text is present. Where the image can be calibrated, it also performs physical measurements directly from the photograph.

### Scale Calibration

The system establishes a pixels-per-millimetre (px/mm) conversion factor:

- Barcode-based calibration is preferred when a suitable barcode is available.
- A controlled fallback scale is used when barcode calibration is unavailable.

### Net-Quantity Font Height

OCR bounding boxes are used to identify the token(s) corresponding to the net-quantity declaration, such as `100 g`, `500 g`, `1 kg`, `250 ml`, `1.5 L`.

The detected character/token height is measured in pixels. Using the calibrated scale:

```text
physical height (mm) = measured height (pixels) / pixels-per-mm
```

The resulting physical measurement is then passed to the deterministic compliance engine. This allows the system to evaluate the applicable minimum declaration height requirement rather than merely checking whether the net quantity appears somewhere on the package.

The measurement itself is kept separate from the OCR/extraction decision so that the compliance engine remains deterministic and auditable.

---

## Component Separation Matrix

### AI / Probabilistic Layers (Extraction Only)

These components accelerate initial unstructured reading but do not enforce legal status:

- Raw optical character recognition (OCR) engine pipelines.
- Character grouping and visual text-line reconstruction modules.
- Generative text extraction handling messy manufacturing labels and addresses.

### Deterministic / Non-ML Layers (Decisions & Geometry)

These layers run strict mathematical or logical functions to finalize compliance:

- Regular expression engines matching predictable numbers, dates, and retail-price formats.
- OCR bounding-box based physical measurements.
- Pixel-to-millimetre scale conversion.
- Net-quantity font-height calculation.
- Boundary checking against active rules.
- Confidence filters and evidence generation.
- Ruleset version tracking.
- Final compliance verdict generation.

---

## System Auditability Profile

Every finalized run commits an auditable validation record containing:

- **Identifications** — Unique Scan UUID, timestamp, and relevant scan metadata.
- **Evidence Traces** — OCR text, bounding boxes, and cropped extraction evidence.
- **Rules Matrix** — Applicable compliance requirements, active `rules.json` version, and specific rule outcomes.
- **Physical Diagnostics** — Scale calibration factor, measured net-quantity font height, pixel measurements, and parsed packaging barcode information where available.
- **Extraction Diagnostics** — Field-level confidence values and source evidence.

This ensures that a compliance verdict can be reviewed rather than treated as an unexplained AI prediction.

---

## Project Status

- **Rules Matrix** — Base parameters drafted. Specific clauses are currently undergoing validation against consolidated Department of Consumer Affairs publications; fields tagged with `VERIFY` inside `rules.json` await official gazette verification.
- **Backend Architecture** — Completed modules include preprocessing, OCR, text reconstruction, confidence scoring, extraction evidence, scale calibration, net-quantity font-height measurement, deterministic validation logic, audit-record generation, and MongoDB persistence.
- **Frontend Workflows** — Dashboard and interactive manual-review workflows are being wired to live endpoints.

---

## References

- **Statute Context** — Department of Consumer Affairs — *Legal Metrology (Packaged Commodities) Rules, 2011*
- **Parent Act** — *Legal Metrology Act, 2009*
- **Hackathon Context** — Ministry of Consumer Affairs, Food & Public Distribution — Problem Statement **SIH26034**

---

## Team

**TechTonic** — Smart India Hackathon 2026