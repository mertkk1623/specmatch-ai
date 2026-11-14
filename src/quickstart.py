"""Quick Start data: precomputed four-scenario analysis, blank templates, dataset.

The Quick Start demo works like the sample analysis page: the result is read
from a JSON file that was produced once by the real pipeline, so opening it
needs no API key, no upload and no network call.

Everything here is synthetic. The PDFs carry a visible banner and the templates
are blank, so nothing can be mistaken for a real specification or datasheet.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from config import PRECOMPUTED_DIR, SAMPLE_DOCS_DIR
from src.schemas import AnalysisResult

QUICKSTART_DIR = SAMPLE_DOCS_DIR / "quickstart"
TEMPLATES_DIR = SAMPLE_DOCS_DIR / "templates"
QUICKSTART_JSON = PRECOMPUTED_DIR / "quickstart_analysis.json"

#: The three inputs of the precomputed demo, in pipeline order.
QUICKSTART_DOCUMENTS = [
    (
        "Project specification",
        "quickstart_specification.pdf",
        "Square hollow sections, 60 × 60 mm, S235JRH, hot-dip galvanized",
    ),
    (
        "Manufacturer A — Marmara Çelik",
        "quickstart_manufacturer_a.pdf",
        "Datasheet: exact size, thicker wall, heavier coating, same grade",
    ),
    (
        "Manufacturer B — Karadeniz Boru",
        "quickstart_manufacturer_b.pdf",
        "Catalogue: thinner nominal wall, different grade, pre-galvanized strip",
    ),
]

#: Blank input templates plus the field guide (documentation, not an input file).
TEMPLATE_FILES = [
    (
        "Specification template",
        "template_specification.pdf",
        "Blank PDF carrying the five labels the specification parser looks for.",
    ),
    (
        "Manufacturer template",
        "template_manufacturer.pdf",
        "Blank PDF for a catalogue page or datasheet.",
    ),
    (
        "Field guide",
        "field_guide.csv",
        "The five fields, accepted units and the rule behind each status. "
        "Documentation only — the application accepts PDFs, not CSV.",
    ),
]

#: The four demonstration scenarios, matching the precomputed result exactly.
SCENARIOS = [
    {
        "tag": "Exact match",
        "title": "Profile dimensions",
        "detail": "60 × 60 mm stated on both sides of the comparison.",
        "result": "Compliant",
        "tone": "ok",
    },
    {
        "tag": "Semantic match",
        "title": "Grade and standard wording",
        "detail": "S235JRH vs S 235 JRH · EN 10219 vs EN 10219-1.",
        "result": "Compliant",
        "tone": "ok",
    },
    {
        "tag": "Over-spec",
        "title": "Thicker wall, heavier coating",
        "detail": "3.0 mm minimum met with 3.2 mm; 505 g/m² met with 620 g/m².",
        "result": "Compliant — exceeds",
        "tone": "ok",
    },
    {
        "tag": "Critical deviation",
        "title": "Karadeniz Boru offer",
        "detail": "2.5 mm nominal vs 3.0 mm minimum, S275J0H, pre-galvanized strip.",
        "result": "3 non-compliant · 1 unverified",
        "tone": "bad",
    },
]


class QuickStartUnavailable(RuntimeError):
    """Raised when the generated Quick Start files are missing."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def available() -> bool:
    return QUICKSTART_JSON.exists()


def document_path(filename: str) -> Path:
    return QUICKSTART_DIR / filename


def template_path(filename: str) -> Path:
    return TEMPLATES_DIR / filename


# ---------------------------------------------------------------------------
# Precomputed result
# ---------------------------------------------------------------------------


def load_result() -> AnalysisResult:
    if not QUICKSTART_JSON.exists():
        raise QuickStartUnavailable(
            "The Quick Start analysis has not been generated yet. Run "
            "`python scripts/build_quickstart_analysis.py` first."
        )
    return AnalysisResult.model_validate_json(QUICKSTART_JSON.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------


def _archive(files: list[tuple[str, Path]], extra: dict[str, str] | None = None) -> bytes:
    """Zip the files that exist, plus optional generated text entries."""

    missing = [path.name for _name, path in files if not path.exists()]
    if missing:
        raise QuickStartUnavailable(
            "Missing generated file(s): "
            + ", ".join(missing)
            + ". Run `python scripts/build_templates.py` and "
            "`python scripts/build_quickstart_docs.py` to create them."
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in files:
            archive.write(path, arcname=name)
        for name, text in (extra or {}).items():
            archive.writestr(name, text)
    return buffer.getvalue()


def templates_archive() -> bytes:
    return _archive([(name, template_path(name)) for _label, name, _desc in TEMPLATE_FILES])


def dataset_archive() -> bytes:
    files = [(name, document_path(name)) for _role, name, _desc in QUICKSTART_DOCUMENTS]
    return _archive(files, extra={"README.txt": _dataset_readme()})


def _dataset_readme() -> str:
    lines = [
        "SpecMatch AI — Quick Start sample dataset",
        "",
        "SYNTHETIC DEMO DATA. These documents were generated for this project.",
        "They do not describe a real project, a real supplier or a real product.",
        "",
        "How to use them",
        "  1. Open the New analysis page.",
        "  2. Upload quickstart_specification.pdf as the project specification.",
        "  3. Upload one or both manufacturer PDFs.",
        "  4. Run the analysis.",
        "",
        "Files",
    ]
    for role, name, description in QUICKSTART_DOCUMENTS:
        lines.append(f"  - {name}")
        lines.append(f"      {role}: {description}")
    lines += [
        "",
        "The four demonstration scenarios",
        "  Exact match        dimensions identical on both sides",
        "  Semantic match     S235JRH vs S 235 JRH, EN 10219 vs EN 10219-1",
        "  Over-spec          3.2 mm against a 3.0 mm minimum, 620 g/m2 against 505 g/m2",
        "  Critical deviation 2.5 mm nominal vs 3.0 mm minimum, S275J0H, pre-galvanized",
        "",
        "Compliance statuses are produced by deterministic Python rules, not by the",
        "language model. Missing information is reported as unverified, never as",
        "compliant. There is no numeric matching score in V1.",
        "",
    ]
    return "\n".join(lines)
