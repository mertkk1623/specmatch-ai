"""Application configuration.

All secrets come from the environment (``.env`` locally). Nothing here writes
or logs the API key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_DOCS_DIR = PROJECT_ROOT / "sample_docs"
PRECOMPUTED_DIR = SAMPLE_DOCS_DIR / "precomputed"
SCREENSHOTS_DIR = PROJECT_ROOT / "docs" / "screenshots"

load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_BASE_URL = "https://api-cdn.deploy.com/api/v1"
DEFAULT_MODEL = "deepseek-ai/deepseek-v4.1-flash-1017"

# Upload guards (V1 keeps PDFs small and single-product-family focused).
# Must match maxUploadSize in .streamlit/config.toml.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_SPEC_PAGES = 60
MAX_CATALOGUE_PAGES = 80


@dataclass(frozen=True)
class Settings:
    """Runtime settings resolved from the environment."""

    api_key: str | None
    base_url: str
    model: str
    timeout_seconds: float
    max_completion_tokens: int
    reasoning_effort: str

    @property
    def api_configured(self) -> bool:
        return bool(self.api_key)


def get_settings() -> Settings:
    """Read settings fresh so a changed ``.env`` is picked up on rerun."""

    load_dotenv(PROJECT_ROOT / ".env", override=False)
    key = os.getenv("DEPLOY_API_KEY", "").strip()
    return Settings(
        api_key=key or None,
        base_url=os.getenv("DEPLOY_BASE_URL", DEFAULT_BASE_URL).strip(),
        model=os.getenv("DEPLOY_MODEL", DEFAULT_MODEL).strip(),
        timeout_seconds=float(os.getenv("DEPLOY_TIMEOUT_SECONDS", "180")),
        max_completion_tokens=int(os.getenv("DEPLOY_MAX_COMPLETION_TOKENS", "4000")),
        reasoning_effort=os.getenv("DEPLOY_REASONING_EFFORT", "high").strip(),
    )


CRITERIA_LABELS: dict[str, str] = {
    "dimensions": "Profile dimensions",
    "wall_thickness": "Wall thickness",
    "material_grade": "Material grade",
    "galvanizing": "Galvanizing / coating",
    "standard": "Applicable standard",
}

STATUS_LABELS: dict[str, str] = {
    "compliant": "Compliant",
    "non_compliant": "Non-compliant",
    "unverified": "Unverified",
    "not_specified": "Not specified",
}
