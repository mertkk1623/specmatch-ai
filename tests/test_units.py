from __future__ import annotations

import pytest

from src.units import (
    allows_equivalence,
    contains_excerpt,
    normalize_grade,
    normalize_standard,
    normalize_unit,
    parse_standard,
    standards_compatible,
    to_g_per_m2,
    to_mm,
    to_um,
)


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (40, "mm", 40.0),
        (4, "cm", 40.0),
        (0.04, "m", 40.0),
        (1.5, "in", 38.1),
        (3, "MM", 3.0),
        (3, " mm ", 3.0),
    ],
)
def test_to_mm_supported_units(value, unit, expected):
    assert to_mm(value, unit) == pytest.approx(expected)


@pytest.mark.parametrize(("value", "unit"), [(3, "swg"), (3, None), (None, "mm"), (3, "gauge")])
def test_to_mm_unsupported_units_return_none(value, unit):
    assert to_mm(value, unit) is None


def test_coating_conversions():
    assert to_g_per_m2(505, "g/m²") == pytest.approx(505)
    assert to_g_per_m2(50.5, "mg/cm2") == pytest.approx(505)
    assert to_g_per_m2(5, "oz") is None
    assert to_um(85, "µm") == pytest.approx(85)
    assert to_um(0.085, "mm") == pytest.approx(85)
    assert to_um(85, "thou") is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("S235JRH", "S235JRH"),
        ("S 235 JRH", "S235JRH"),
        ("s235-jrh", "S235JRH"),
        ("S275J0H", "S275J0H"),
        ("Steel grade S355J2H per EN 10219", "S355J2H"),
        ("EN 10219 only", None),
        ("not a grade", None),
        (None, None),
    ],
)
def test_normalize_grade(raw, expected):
    assert normalize_grade(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("EN 10219-1", "EN 10219-1"),
        ("EN10219", "EN 10219"),
        ("EN 10219-1:2006", "EN 10219-1"),
        ("EN ISO 1461", "EN ISO 1461"),
        ("ASTM A500", "ASTM A500"),
        ("no standard here", None),
    ],
)
def test_normalize_standard(raw, expected):
    assert normalize_standard(raw) == expected


def test_parse_standard_drops_year_as_part():
    assert parse_standard("EN 10219-1:2006") == ("EN", "10219", "1")


def test_standards_compatible_family():
    ok, _ = standards_compatible("EN 10219", "EN 10219-1")
    assert ok
    ok, note = standards_compatible("EN 10219", "EN 10210")
    assert not ok
    assert "not the same standard" in note


def test_alternate_spelling_compatible():
    ok, _ = standards_compatible("EN 10219", "EN10219")
    assert ok


def test_allows_equivalence():
    assert allows_equivalence("S235JRH or equivalent")
    assert not allows_equivalence("S235JRH")


def test_contains_excerpt_ignores_whitespace():
    page = "Square hollow sections\n40 x 40 x 3.0 mm   S235JRH"
    assert contains_excerpt(page, "40 x 40 x 3.0 mm")
    assert contains_excerpt(page, "40x40x3.0mm")
    assert not contains_excerpt(page, "50 x 50 x 3.0 mm")


def test_normalize_unit():
    assert normalize_unit("G/M²") == "g/m2"
    assert normalize_unit("µm") == "um"
    assert normalize_unit("  ") is None
