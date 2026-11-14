# SpecMatch AI — Final V1 Project Brief

## 1. Project overview

SpecMatch AI is an AI-assisted technical specification comparison tool for construction procurement and technical-office workflows.

It compares one project specification PDF with up to two manufacturer catalogue/datasheet PDFs for one product family: **galvanized square steel hollow sections**.

It extracts requirements, compares manufacturer data, highlights discrepancies, and presents evidence-backed findings.

This is a first-pass comparison assistant—not an engineering approval, certification, or purchasing decision system.

## 2. V1 scope

### Inputs
- One technical specification PDF.
- One or two manufacturer catalogue/datasheet PDFs.

### Five comparison criteria
1. Profile dimensions (e.g. 40 × 40 mm)
2. Wall thickness
3. Material grade, when specified
4. Galvanizing/coating information
5. Applicable standard, when specified

### Statuses
- **Compliant:** available evidence meets the stated requirement.
- **Non-compliant:** available evidence clearly conflicts with the requirement.
- **Unverified:** information is missing, ambiguous, or cannot be reliably compared.

Missing information must never be treated as compliant.

### Outputs
- Extracted project requirements.
- Manufacturer-by-manufacturer comparison.
- Status for each criterion.
- Source document and page reference for each extracted value, when available.
- Short AI-generated explanation.
- Downloadable comparison report.

## 3. Processing workflow

1. User uploads the specification and manufacturer PDFs.
2. Python/Docling extracts document text and tables.
3. DeepSeek extracts structured technical fields into JSON.
4. Pydantic validates the extracted data.
5. Python comparison logic evaluates the five criteria.
6. The interface displays results with evidence and explanations.
7. User downloads the report.

**Separation of responsibilities**
- DeepSeek extracts information and explains findings.
- Python determines compliance status using explicit rules.
- The model must not independently decide whether a product is compliant.
- Never invent values, page numbers, standards, or evidence references.
- Unclear units or ambiguous values remain Unverified unless a tested conversion rule applies.

## 4. AI model and API

Use the existing Deploy API account.

| Setting | Value |
|---|---|
| Provider | Deploy |
| Model | `deepseek-ai/deepseek-v4.1-flash-1017` |
| Base URL | `https://api-cdn.deploy.com/api/v1` |
| SDK | `openai` Python package |
| API format | OpenAI-compatible Chat Completions |

Example:

```python
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://api-cdn.deploy.com/api/v1",
    api_key=os.getenv("DEPLOY_API_KEY"),
)

response = client.chat.completions.create(
    model="deepseek-ai/deepseek-v4.1-flash-1017",
    messages=[
        {
            "role": "system",
            "content": (
                "Extract technical requirements from the supplied document. "
                "Return only the requested structured data. "
                "Do not infer missing values."
            ),
        },
        {
            "role": "user",
            "content": "Extract the specified technical fields from this document.",
        },
    ],
    temperature=0,
    max_completion_tokens=4000,
    reasoning_effort="high",
)

print(response.choices[0].message.content)
```

Implementation notes:
- Store `DEPLOY_API_KEY` in `.env`.
- Provide `.env.example` with a placeholder only.
- Never commit secrets to GitHub.
- Validate model output before it reaches the comparison engine.
- Handle API errors, invalid JSON, timeouts, and incomplete responses.

## 5. Technology stack

- **Python:** application logic and comparison engine
- **Streamlit:** interface and multipage experience
- **Docling:** PDF text and table extraction
- **Deploy DeepSeek API:** structured extraction and explanations
- **Pydantic:** schema and output validation
- **Pytest:** automated tests
- **ReportLab or HTML export:** downloadable report

Keep the architecture lightweight. Do not add React, FastAPI, PostgreSQL, Docker, authentication, payments, or other infrastructure to V1.

## 6. Pages and user experience

The app must not open directly on an upload form. It should feel like a small, finished B2B software product.

### A. Landing page
- Clear headline explaining the problem solved.
- Short product explanation.
- Three-step workflow: Upload → Compare → Review evidence.
- Links to the sample specification and two sample manufacturer catalogues.
- Button to open a precomputed sample analysis.
- V1 / V2 / V3 roadmap.
- Primary CTA: **Start a new analysis**.

### B. Sample demo
- Use clearly labelled synthetic/demo documents.
- Show a precomputed analysis without requiring an API call.
- Let visitors inspect the comparison and evidence.
- Disclose that sample documents and results are demonstration data.

### C. New analysis
- Upload one specification PDF.
- Upload up to two manufacturer PDFs.
- Start analysis and show processing/error states.
- Display extracted requirements and validation issues.

### D. Results
- Clear comparison table.
- Compliant / Non-compliant / Unverified statuses.
- Evidence references and page numbers where available.
- Concise explanations.
- Downloadable report.

Include empty, loading, success, and error states. Desktop-first, but responsive.

## 7. Visual direction

- Modern, restrained B2B SaaS design.
- Professional typography and clear information hierarchy.
- Strong readability for technical tables and evidence.
- Consistent spacing and restrained use of color.
- Avoid generic AI-template styling, excessive gradients, decorative icons, unnecessary animations, and crowded dashboard cards.

The product should look credible to a technical-office or procurement hiring manager.

## 8. Roadmap

### V1 — Working portfolio demo
- One product family.
- PDF upload and extraction.
- Five comparison criteria.
- Up to two manufacturer documents.
- Three compliance statuses.
- Evidence references.
- AI explanations.
- Downloadable report.
- Precomputed sample demo.

### V2 — Planned improvements
- More profile dimensions and variants.
- Better extraction from complex catalogue tables.
- Tolerance-aware comparisons.
- Stronger evidence and confidence handling.

### V3 — Future direction
- Additional steel product families.
- Cross-document technical Q&A.
- Alternative product comparison.
- Broader standards and specification coverage.

Only implemented features may be presented as completed. Roadmap items must be labelled as planned.

## 9. Suggested project structure

```text
specmatch-ai/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── src/
│   ├── document_parser.py
│   ├── extraction.py
│   ├── schemas.py
│   ├── compliance.py
│   ├── evidence.py
│   └── report.py
├── pages/
│   ├── sample_demo.py
│   └── new_analysis.py
├── tests/
│   ├── test_compliance.py
│   └── test_extraction.py
└── sample_docs/
    ├── demo_specification.pdf
    ├── demo_manufacturer_a.pdf
    └── demo_manufacturer_b.pdf
```

Adjust only when implementation requires it; avoid unnecessary abstraction.

## 10. Four-day implementation plan

| Day | Deliverable |
|---|---|
| 1 | Create demo PDFs, implement PDF extraction, define Pydantic schemas |
| 2 | Integrate Deploy DeepSeek API and validate structured extraction |
| 3 | Build deterministic comparison engine, results interface, landing page and sample demo |
| 4 | Add report export, tests, README, screenshots and deployment |

## 11. Testing requirements

At minimum, test:
- Exact matching dimensions and thickness.
- Clear mismatch detection.
- Missing manufacturer information → Unverified.
- Ambiguous or unsupported units → Unverified.
- Optional criteria absent from the project specification.
- Invalid or incomplete model output.
- Evidence references are preserved and not fabricated.
- API failure does not crash the application.

The comparison engine must be testable independently of the AI API.

## 12. Definition of done

- [ ] Landing page works.
- [ ] Sample PDFs are available.
- [ ] Precomputed demo works without an API call.
- [ ] User can upload one specification and up to two manufacturer PDFs.
- [ ] Five criteria are extracted and compared.
- [ ] All three statuses work correctly.
- [ ] Missing or unclear information is marked Unverified.
- [ ] Evidence and page references are shown when available.
- [ ] A report can be downloaded.
- [ ] Automated tests pass.
- [ ] README explains the problem, workflow, stack, limitations, and setup.
- [ ] Deployed demo is accessible and contains no exposed secrets.


## 14. Documentation and final screenshots

Documentation is a required delivery item, not an optional cleanup task.

Create two separate, detailed README files:

- `README.md` — English, the default GitHub landing page.
- `README.tr.md` — Turkish.

At the top of each README, add a clear language switch link to the other version.

Both README files must cover:
- Project overview and the problem it solves.
- Key features and V1 scope.
- Screenshots of the actual application.
- How the workflow works.
- Technology stack and architecture.
- Installation and local setup.
- Deploy API configuration using `.env`.
- Usage instructions.
- Known limitations and responsible-use note.
- Roadmap, with V2 and V3 clearly marked as **Planned**.
- Live demo link, when deployment is complete.

### Screenshot capture — after the application is finished

Do not create illustrative or fabricated UI screenshots. Capture screenshots from the real, completed application after the main workflow has been tested.

Save and organize them under:

```text
docs/
└── screenshots/
    ├── 01-landing-page.png
    ├── 02-sample-demo.png
    ├── 03-document-upload.png
    ├── 04-comparison-results.png
    └── 05-report-preview.png
```

Capture the pages and states that actually exist. If a listed screen is not implemented, do not fabricate it; adjust the screenshot set and README accordingly.

Embed the screenshots in both README files in the same order, with concise captions. Use repository-relative image paths so they render on GitHub.

Before delivery:
- Verify both README files render correctly on GitHub.
- Verify every screenshot path and image link.
- Confirm screenshots show the final tested application.
- Confirm no API keys, private data, or sensitive local paths are visible.
- Keep English and Turkish documentation consistent.

## 13. Explicitly out of scope for V1

- General supplier discovery or web crawling.
- RFQ email generation or sending.
- SAP/ERP integration.
- Purchase orders or inventory management.
- Multiple sectors or unrestricted product categories.
- Engineering approval or certification.
- User accounts, roles, subscriptions, or payments.
- Full SaaS platform infrastructure.

**V1 principle:** one product family, a small set of measurable criteria, evidence-backed comparisons, and a polished working demo.


## Documentation and final screenshots

Create two detailed README files: `README.md` (English) and `README.tr.md` (Turkish), with language-switch links at the top. Both must explain the project, features, workflow, architecture, stack, installation, `.env`/Deploy API setup, usage, limitations, roadmap, and live demo when available.

After the application is complete and tested, capture screenshots from the real app and save them in `docs/screenshots/`. Suggested files: `01-landing-page.png`, `02-sample-demo.png`, `03-document-upload.png`, `04-comparison-results.png`, `05-report-preview.png`. Do not fabricate screens. Embed the actual screenshots in both README files using repository-relative paths and verify all links. Ensure no API keys or private data appear.


## Explicitly out of scope for V1

- General supplier discovery or web crawling.
- RFQ email generation or sending.
- SAP/ERP integration.
- Purchase orders or inventory management.
- Multiple sectors or unrestricted product categories.
- Engineering approval or certification.
- User accounts, roles, subscriptions, or payments.
- Full SaaS platform infrastructure.

**V1 principle:** one product family, a small set of measurable criteria, evidence-backed comparisons, and a polished working demo.
