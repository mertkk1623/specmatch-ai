# SpecMatch AI — Implementation Plan (V1)

Source of truth: `SpecMatch_AI_Final_Project_Brief.md`.
Scope guard: one product family (galvanized square steel hollow sections), five criteria,
one specification + up to two manufacturer PDFs, three compliance statuses, evidence-backed
results, downloadable report, precomputed sample demo. No auth, no DB, no Docker, no FastAPI.

## Product decisions

| Topic | Decision |
|---|---|
| Statuses | `compliant`, `non_compliant`, `unverified` (brief). A separate neutral outcome `not_specified` is used **only** when the project spec does not state the criterion. It is not a compliance verdict and is excluded from compliance counts. |
| Who decides status | Python only (`src/compliance.py`). The model extracts fields and writes prose explanations; it never returns a status. |
| Units | The model returns values **as printed** plus the unit. Python converts only with tested rules (mm, cm, m, in; g/m²; µm, mm for coating). Anything else → `unverified`. |
| Tolerances | V1 compares nominally with a 0.1 mm precision guard (rounding only). Tolerance-aware comparison is V2. |
| Evidence | Every value carries a page number + verbatim excerpt. Excerpts are verified against parsed page text; unverifiable evidence is dropped and reported as a validation issue. |
| Requirements absent from spec | `not_specified`, no comparison, no count inflation. |
| AI explanations | Generated after deterministic comparison, statuses supplied to the model read-only. Deterministic fallback text on API failure. |
| Report | Self-contained HTML export (`src/report.py`) with print CSS. |
| Demo data | Real pipeline output generated once via the API and stored in `sample_docs/precomputed/`. Viewing the demo makes no API call. |
| Quick start | A second precomputed run (four scenarios: exact, semantic, over-spec, critical deviation) opens from the landing page in one click, plus blank PDF templates and the sample dataset as ZIP downloads. Still no API call and no upload. |
| Parser | Docling primary (`src/document_parser.py`), pypdf fallback with an explicit parser label in the UI when Docling is unavailable/fails. |

## Phases

1. **Foundation** — plan, directory skeleton, config, `.env`/`.env.example`, `.gitignore`, requirements, venv.
2. **Schemas & deterministic engine** — Pydantic extraction schemas, unit conversion/normalization, five comparison rules, status counts, pytest coverage for all brief test cases. No AI involved.
3. **Synthetic demo PDFs** — three clearly labelled PDFs (spec + manufacturer A + manufacturer B) built with ReportLab; visible "SYNTHETIC DEMO" banner on every page.
4. **Document parsing** — Docling text + table extraction with per-page text; pypdf fallback; parser metadata; tests against demo PDFs.
5. **AI extraction** — Deploy/DeepSeek OpenAI-compatible client, page-tagged prompt, JSON parsing, Pydantic validation, one repair retry, evidence verification, error/timeout handling; mocked tests.
6. **Pipeline & report** — orchestration, AI narrative with fallback, HTML report export; tests.
7. **UI** — custom top navigation, landing page, sample demo, new analysis (empty/loading/error/success), results, download. Desktop-first responsive CSS.
8. **Precomputed demo** — run the real pipeline on the demo PDFs, store JSON + metadata, verify demo renders without API.
9. **Verification** — full pytest run, manual workflow test, error-state checks.
10. **Documentation & screenshots** — real Playwright screenshots into `docs/screenshots/`, English + Turkish README with language switch, scope/limitations/roadmap, no fabricated completion (no live deployment claim).
11. **Quick start & demo data** — four-scenario dataset, blank PDF templates, field guide, precomputed result, landing-page panel and session-state integration; demo reproducible without an API key.

## Initial file tree

```text
app.py                  # nav shell + landing page
config.py               # env/config
requirements.txt
.env / .env.example     # local secret / placeholder
PLAN.md
src/
  document_parser.py
  extraction.py
  schemas.py
  units.py
  compliance.py
  evidence.py
  report.py
  pipeline.py
  demo.py
  ui/theme.py
  ui/results.py
pages/
  sample_demo.py
  new_analysis.py
  results.py
tests/
  test_compliance.py
  test_extraction.py
  test_units.py
  test_evidence.py
  test_report.py
scripts/
  build_demo_pdfs.py
  build_demo_analysis.py
  capture_screenshots.py
sample_docs/
  demo_specification.pdf
  demo_manufacturer_a.pdf
  demo_manufacturer_b.pdf
  precomputed/demo_analysis.json
docs/screenshots/
```

## Comparison rules (V1)

- **DIM**: spec width/height vs offered width/height, both required; equal within 0.1 mm → compliant, any clear difference → non-compliant.
- **THK**: nominal equal within 0.1 mm; `minimum` → offered ≥ min; `maximum` → offered ≤ max.
- **MAT**: normalized grade equality (spaces/hyphens/case ignored). Different grade → non-compliant; "or equivalent" wording in spec → unverified.
- **STD**: normalized designation containment (EN 10219 ↔ EN 10219-1). Different product standard → non-compliant.
- **GALV**: process (hot-dip vs pre-galvanized/bare), galvanizing standard, minimum coating mass/thickness. Conflict → non-compliant; different galvanizing standard or missing evidence → unverified; all specified sub-checks pass → compliant.
- Any missing/unconvertible manufacturer value → **unverified**, never compliant.
