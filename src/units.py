"""Deterministic unit conversion and normalization helpers.

Only tested conversions are applied. Anything unknown returns ``None`` so the
comparison engine can mark the criterion Unverified instead of guessing.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------

LENGTH_FACTORS_TO_MM: dict[str, float] = {
    "mm": 1.0,
    "millimeter": 1.0,
    "millimeters": 1.0,
    "millimetre": 1.0,
    "millimetres": 1.0,
    "cm": 10.0,
    "centimeter": 10.0,
    "centimeters": 10.0,
    "centimetre": 10.0,
    "centimetres": 10.0,
    "m": 1000.0,
    "meter": 1000.0,
    "meters": 1000.0,
    "metre": 1000.0,
    "metres": 1000.0,
    "in": 25.4,
    "inch": 25.4,
    "inches": 25.4,
    '"': 25.4,
    "”": 25.4,
    "''": 25.4,
}

LENGTH_FACTORS_TO_MM["mm."] = 1.0
LENGTH_FACTORS_TO_MM["m."] = 1000.0


def normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    text = unicodedata.normalize("NFKC", unit).strip().lower()
    text = text.replace("²", "2").replace("µ", "u").replace("μ", "u")
    text = re.sub(r"\s+", "", text)
    return text or None


def to_mm(value: float | None, unit: str | None) -> float | None:
    """Convert a printed length to millimetres, or return ``None``."""

    key = normalize_unit(unit)
    if value is None or key is None:
        return None
    factor = LENGTH_FACTORS_TO_MM.get(key)
    if factor is None:
        return None
    return round(float(value) * factor, 4)


# ---------------------------------------------------------------------------
# Coating
# ---------------------------------------------------------------------------

COATING_MASS_TO_G_M2: dict[str, float] = {
    "g/m2": 1.0,
    "g/m²": 1.0,
    "gram/m2": 1.0,
    "grams/m2": 1.0,
    "gsm": 1.0,
    "gr/m2": 1.0,
    "mg/cm2": 10.0,  # 1 mg/cm² = 10 g/m²
    "g/cm2": 10000.0,
}

COATING_THICKNESS_TO_UM: dict[str, float] = {
    "um": 1.0,
    "micron": 1.0,
    "microns": 1.0,
    "micrometer": 1.0,
    "micrometre": 1.0,
    "micrometres": 1.0,
    "mm": 1000.0,
    "mil": 25.4,
}


def to_g_per_m2(value: float | None, unit: str | None) -> float | None:
    key = normalize_unit(unit)
    if value is None or key is None:
        return None
    factor = COATING_MASS_TO_G_M2.get(key)
    if factor is None:
        return None
    return round(float(value) * factor, 4)


def to_um(value: float | None, unit: str | None) -> float | None:
    key = normalize_unit(unit)
    if value is None or key is None:
        return None
    factor = COATING_THICKNESS_TO_UM.get(key)
    if factor is None:
        return None
    return round(float(value) * factor, 4)


# ---------------------------------------------------------------------------
# Material grade
# ---------------------------------------------------------------------------

_GRADE_TOKEN = re.compile(r"\b([A-Z])\s*-?\s*(\d{2,3})\s*-?\s*([A-Z0-9]{0,4})\b")


def normalize_grade(raw: str | None) -> str | None:
    """Reduce a grade designation to a comparable key.

    ``"S 235 JRH"``, ``"S235JRH"`` and ``"s235-jrh"`` all become ``S235JRH``.
    Recognition is deliberately restricted to plain EN-style designations so
    that free text is not mistaken for a grade.
    """

    if not raw:
        return None
    text = unicodedata.normalize("NFKC", raw).upper().strip()
    match = _GRADE_TOKEN.search(text)
    if not match:
        return None
    prefix, number, suffix = match.groups()
    suffix = re.sub(r"[^A-Z0-9]", "", suffix)
    return f"{prefix}{number}{suffix}"


def extract_grade_token(raw: str | None) -> str | None:
    """Best-effort grade token used for display when normalization succeeds."""

    return normalize_grade(raw)


# ---------------------------------------------------------------------------
# Standards
# ---------------------------------------------------------------------------

_BODY_ALIASES = {
    "EN": "EN",
    "EURONORM": "EN",
    "ISO": "ISO",
    "ENISO": "EN ISO",
    "ASTM": "ASTM",
    "DIN": "DIN",
    "BS": "BS",
    "TS": "TS",
    "TSEN": "TS EN",
}

_STANDARD_RE = re.compile(
    r"\b(EN\s*ISO|EN|ISO|ASTM|DIN|BS|TS\s*EN|TS)\s*[-]?\s*([A-Z]?\s?\d{3,5})"
    r"(?:\s*[-/]?\s*(\d{1,2})\b)?",
    re.IGNORECASE,
)


def parse_standard(raw: str | None) -> tuple[str, str, str | None] | None:
    """Return ``(body, number, part)`` for a standard designation.

    ``"EN 10219-1:2006"`` → ``("EN", "10219", "1")``.
    """

    if not raw:
        return None
    text = unicodedata.normalize("NFKC", raw).upper()
    match = _STANDARD_RE.search(text)
    if not match:
        return None
    body = re.sub(r"\s+", " ", match.group(1)).strip()
    body = _BODY_ALIASES.get(body.replace(" ", ""), body)
    number = re.sub(r"\s+", "", match.group(2))
    part = match.group(3)
    if part and int(part) > 20:  # likely a year, not a part number
        part = None
    return body, number, part


def normalize_standard(raw: str | None) -> str | None:
    parsed = parse_standard(raw)
    if not parsed:
        return None
    body, number, part = parsed
    return f"{body} {number}" + (f"-{part}" if part else "")


def standards_compatible(spec: str | None, offer: str | None) -> tuple[bool, str]:
    """Compare a required and an offered standard designation.

    Returns ``(compatible, note)``. Same body and number are compatible even if
    only one side names a part (EN 10219 vs EN 10219-1). Different numbers or
    bodies are a clear conflict.
    """

    spec_parsed = parse_standard(spec)
    offer_parsed = parse_standard(offer)
    if not spec_parsed or not offer_parsed:
        return False, "Standard designation could not be normalized."
    spec_body, spec_number, spec_part = spec_parsed
    offer_body, offer_number, offer_part = offer_parsed
    if spec_body != offer_body or spec_number != offer_number:
        return False, f"{spec_body} {spec_number} is not the same standard as {offer_body} {offer_number}."
    if spec_part and offer_part and spec_part != offer_part:
        return False, f"Different part of {spec_body} {spec_number} (part {spec_part} vs {offer_part})."
    return True, "Same standard family."


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


_TOLERANCE_OR_EQUIVALENT = re.compile(
    r"\b(or\s+equivalent|or\s+equal|equivalent\s+grade|ve\s+muadili)\b",
    re.IGNORECASE,
)


def allows_equivalence(raw: str | None) -> bool:
    return bool(raw and _TOLERANCE_OR_EQUIVALENT.search(raw))


def normalize_space(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def contains_excerpt(page_text: str, excerpt: str) -> bool:
    """Containment check used for evidence verification.

    Three levels, from strict to tolerant: exact (case-insensitive) substring,
    whitespace-insensitive, then alphanumeric-only. The last level absorbs the
    noise introduced by table and layout extraction ("Grade | S235JRH" vs
    "Grade S235JRH") while still requiring the excerpt's characters to appear
    in order on the page.
    """

    haystack = normalize_space(page_text).lower()
    needle = normalize_space(excerpt).lower()
    if not needle:
        return False
    if needle in haystack:
        return True

    compact_haystack = re.sub(r"\s+", "", haystack)
    compact_needle = re.sub(r"\s+", "", needle)
    if compact_needle in compact_haystack:
        return True

    alnum_haystack = re.sub(r"[^a-z0-9]", "", haystack)
    alnum_needle = re.sub(r"[^a-z0-9]", "", needle)
    if len(alnum_needle) < 8:
        return False
    return alnum_needle in alnum_haystack
