"""Build the precomputed Quick Start analysis.

Runs the real pipeline once on the three Quick Start PDFs and stores the result,
so the homepage demo button opens a full analysis with no API call and no upload.

Run:  python scripts/build_quickstart_analysis.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from config import PRECOMPUTED_DIR, get_settings  # noqa: E402
from src.pipeline import AnalysisInput, run_analysis  # noqa: E402

QUICKSTART_DIR = ROOT / "sample_docs" / "quickstart"
OUTPUT = PRECOMPUTED_DIR / "quickstart_analysis.json"


def main() -> int:
    load_dotenv(ROOT / ".env")
    settings = get_settings()
    if not settings.api_configured:
        print("DEPLOY_API_KEY is not configured; cannot build the Quick Start analysis.")
        return 1

    data = AnalysisInput(
        spec_path=str(QUICKSTART_DIR / "quickstart_specification.pdf"),
        manufacturer_paths=[
            str(QUICKSTART_DIR / "quickstart_manufacturer_a.pdf"),
            str(QUICKSTART_DIR / "quickstart_manufacturer_b.pdf"),
        ],
        manufacturer_names=["Marmara Çelik", "Karadeniz Boru"],
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

    print("\nWrote:")
    print(f"  {OUTPUT.relative_to(ROOT)}")
    print(f"\nDuration: {result.duration_seconds}s  Model: {result.model}")
    for manufacturer in result.manufacturers:
        counts = manufacturer.counts
        print(
            f"  {manufacturer.name}: {counts.compliant} compliant / "
            f"{counts.non_compliant} non-compliant / {counts.unverified} unverified / "
            f"{counts.not_specified} not specified"
        )
        for criterion in manufacturer.criteria:
            print(
                f"      {criterion.criterion:16s} {criterion.status.value:15s} "
                f"spec={criterion.spec_display!r} offer={criterion.offer_display!r}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
