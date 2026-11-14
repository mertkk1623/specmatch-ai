"""Load the precomputed sample analysis.

The sample demo must work without an API key and without any network call, so
the result is read from a JSON file that was produced once by the real pipeline.
"""

from __future__ import annotations

from pathlib import Path

from config import PRECOMPUTED_DIR, SAMPLE_DOCS_DIR
from src.schemas import AnalysisResult

DEMO_JSON = PRECOMPUTED_DIR / "demo_analysis.json"

DEMO_DOCUMENTS = [
    (
        "Project specification",
        "demo_specification.pdf",
        "Tender specification for galvanized square hollow sections",
    ),
    (
        "Manufacturer A",
        "demo_manufacturer_a.pdf",
        "Anadolu Profil — product datasheet (hot-dip galvanized)",
    ),
    (
        "Manufacturer B",
        "demo_manufacturer_b.pdf",
        "Ege Metal — catalogue extract (pre-galvanized strip)",
    ),
]


class DemoUnavailable(RuntimeError):
    pass


def demo_available() -> bool:
    return DEMO_JSON.exists()


def load_demo_result() -> AnalysisResult:
    if not DEMO_JSON.exists():
        raise DemoUnavailable(
            "The sample analysis has not been generated yet. Run "
            "`python scripts/build_demo_analysis.py` first."
        )
    return AnalysisResult.model_validate_json(DEMO_JSON.read_text(encoding="utf-8"))


def demo_document_path(filename: str) -> Path:
    return SAMPLE_DOCS_DIR / filename


def demo_report_path() -> Path:
    return PRECOMPUTED_DIR / "demo_report.html"
