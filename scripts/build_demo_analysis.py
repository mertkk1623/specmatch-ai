"""Build the precomputed sample analysis.

Runs the real pipeline (Docling PDF parsing + Deploy DeepSeek extraction +
deterministic comparison) once, then stores the validated result so the sample
demo page can display it without any API call.

Run:  python scripts/build_demo_analysis.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from config import PRECOMPUTED_DIR, SAMPLE_DOCS_DIR, get_settings  # noqa: E402
from src.pipeline import AnalysisInput, run_analysis  # noqa: E402
from src.report import build_report_html, report_filename  # noqa: E402

OUTPUT = PRECOMPUTED_DIR / "demo_analysis.json"
REPORT = PRECOMPUTED_DIR / "demo_report.html"


def main() -> int:
    load_dotenv(ROOT / ".env")
    settings = get_settings()
    if not settings.api_configured:
        print("DEPLOY_API_KEY is not configured; cannot build the sample analysis.")
        return 1

    data = AnalysisInput(
        spec_path=str(SAMPLE_DOCS_DIR / "demo_specification.pdf"),
        manufacturer_paths=[
            str(SAMPLE_DOCS_DIR / "demo_manufacturer_a.pdf"),
            str(SAMPLE_DOCS_DIR / "demo_manufacturer_b.pdf"),
        ],
        manufacturer_names=["Anadolu Profil", "Ege Metal"],
    )

    def progress(message: str, fraction: float) -> None:
        print(f"  [{fraction * 100:5.1f}%] {message}")

    result = run_analysis(
        data,
        api_key=settings.api_key or "",
        settings=settings,
        enable_ai_explanations=True,
        progress=progress,
    )
    result.demo = True

    PRECOMPUTED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    REPORT.write_text(build_report_html(result), encoding="utf-8")

    print("\nWrote:")
    print(f"  {OUTPUT.relative_to(ROOT)}")
    print(f"  {REPORT.relative_to(ROOT)}  (static preview of {report_filename(result)})")
    print(f"\nDuration: {result.duration_seconds}s  Model: {result.model}")
    for manufacturer in result.manufacturers:
        counts = manufacturer.counts
        print(
            f"  {manufacturer.name}: {counts.compliant} compliant / "
            f"{counts.non_compliant} non-compliant / {counts.unverified} unverified"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
