"""Unit tests for the deterministic compliance engine.

The engine must be testable without the AI API. These tests cover every case
required by the project brief (section 11).
"""

from __future__ import annotations

import pytest

from src.compliance import (
    compare_document,
    compare_dimensions,
    compare_galvanizing,
    compare_material_grade,
    compare_standard,
    compare_wall_thickness,
    count_statuses,
    summarize_counts,
)
from src.schemas import (
    DimensionsField,
    ExtractedRequirements,
    GalvanizingField,
    GalvanizingProcess,
    MaterialGradeField,
    Quantity,
    StandardField,
    Status,
    ThicknessField,
    ThicknessKind,
)


def dims(width: float, height: float, unit: str = "mm", page: int | None = 1) -> DimensionsField:
    return DimensionsField(
        width=Quantity(value=width, unit=unit, page=page, excerpt=f"{width} x {height}"),
        height=Quantity(value=height, unit=unit, page=page, excerpt=f"{width} x {height}"),
        page=page,
        excerpt=f"{width} x {height}",
    )


def thickness(value: float, unit: str = "mm", kind: ThicknessKind = ThicknessKind.NOMINAL) -> ThicknessField:
    return ThicknessField(value=value, unit=unit, kind=kind, page=2, excerpt=f"t = {value} {unit}")


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------


def test_dimensions_exact_match_is_compliant():
    result = compare_dimensions(dims(40, 40), dims(40, 40))
    assert result.status is Status.COMPLIANT
    assert "40 × 40" in (result.spec_display or "")


def test_dimensions_mismatch_is_non_compliant():
    result = compare_dimensions(dims(40, 40), dims(50, 50))
    assert result.status is Status.NON_COMPLIANT
    assert any(check.outcome == "fail" for check in result.checks)


def test_dimensions_partial_mismatch_is_non_compliant():
    result = compare_dimensions(dims(40, 40), dims(40, 60))
    assert result.status is Status.NON_COMPLIANT


def test_dimensions_missing_offer_is_unverified():
    result = compare_dimensions(dims(40, 40), None)
    assert result.status is Status.UNVERIFIED
    assert "never treated as compliant" in result.rule_explanation


def test_dimensions_missing_spec_is_not_specified():
    result = compare_dimensions(None, dims(40, 40))
    assert result.status is Status.NOT_SPECIFIED


def test_dimensions_unsupported_unit_is_unverified():
    spec = DimensionsField(
        width=Quantity(value=40, unit="mm"),
        height=Quantity(value=40, unit="mm"),
    )
    offer = DimensionsField(
        width=Quantity(value=4, unit="furlong"),
        height=Quantity(value=4, unit="furlong"),
    )
    result = compare_dimensions(spec, offer)
    assert result.status is Status.UNVERIFIED


def test_dimensions_converted_units_are_compliant():
    spec = dims(40, 40, unit="mm")
    offer = dims(4, 4, unit="cm")
    result = compare_dimensions(spec, offer)
    assert result.status is Status.COMPLIANT


def test_dimensions_rounding_tolerance_is_compliant():
    result = compare_dimensions(dims(40, 40), dims(40.0, 40.04))
    assert result.status is Status.COMPLIANT


# ---------------------------------------------------------------------------
# Wall thickness
# ---------------------------------------------------------------------------


def test_thickness_exact_match_is_compliant():
    result = compare_wall_thickness(thickness(3), thickness(3))
    assert result.status is Status.COMPLIANT


def test_thickness_mismatch_is_non_compliant():
    result = compare_wall_thickness(thickness(3), thickness(2))
    assert result.status is Status.NON_COMPLIANT


def test_thickness_missing_offer_is_unverified():
    result = compare_wall_thickness(thickness(3), None)
    assert result.status is Status.UNVERIFIED


def test_thickness_unsupported_unit_is_unverified():
    result = compare_wall_thickness(thickness(3, unit="mm"), thickness(3, unit="swg"))
    assert result.status is Status.UNVERIFIED


def test_thickness_spec_missing_is_not_specified():
    result = compare_wall_thickness(None, thickness(3))
    assert result.status is Status.NOT_SPECIFIED


def test_thickness_minimum_requirement_met():
    spec = thickness(3, kind=ThicknessKind.MINIMUM)
    offer = thickness(3.2)
    result = compare_wall_thickness(spec, offer)
    assert result.status is Status.COMPLIANT


def test_thickness_minimum_requirement_failed():
    spec = thickness(3, kind=ThicknessKind.MINIMUM)
    offer = thickness(2.5)
    result = compare_wall_thickness(spec, offer)
    assert result.status is Status.NON_COMPLIANT


def test_thickness_nominal_spec_vs_offer_minimum_is_unverified():
    spec = thickness(3, kind=ThicknessKind.NOMINAL)
    offer = thickness(3.1, kind=ThicknessKind.MINIMUM)
    result = compare_wall_thickness(spec, offer)
    assert result.status is Status.UNVERIFIED


# ---------------------------------------------------------------------------
# Material grade
# ---------------------------------------------------------------------------


def test_material_grade_match_with_different_spacing():
    spec = MaterialGradeField(grade="S 235 JRH", page=3, excerpt="S 235 JRH")
    offer = MaterialGradeField(grade="S235JRH", page=4, excerpt="S235JRH")
    result = compare_material_grade(spec, offer)
    assert result.status is Status.COMPLIANT


def test_material_grade_mismatch():
    spec = MaterialGradeField(grade="S235JRH")
    offer = MaterialGradeField(grade="S275J0H")
    result = compare_material_grade(spec, offer)
    assert result.status is Status.NON_COMPLIANT


def test_material_grade_missing_offer_is_unverified():
    result = compare_material_grade(MaterialGradeField(grade="S235JRH"), None)
    assert result.status is Status.UNVERIFIED


def test_material_grade_absent_from_spec_is_not_specified():
    result = compare_material_grade(None, MaterialGradeField(grade="S235JRH"))
    assert result.status is Status.NOT_SPECIFIED


def test_material_grade_equivalence_allowed_is_unverified():
    spec = MaterialGradeField(grade="S235JRH", equivalence_allowed=True)
    offer = MaterialGradeField(grade="S275J0H")
    result = compare_material_grade(spec, offer)
    assert result.status is Status.UNVERIFIED


# ---------------------------------------------------------------------------
# Standard
# ---------------------------------------------------------------------------


def test_standard_exact_match_is_compliant():
    result = compare_standard(
        StandardField(designation="EN 10219-1"),
        StandardField(designation="EN 10219"),
    )
    assert result.status is Status.COMPLIANT


def test_standard_different_number_is_non_compliant():
    result = compare_standard(
        StandardField(designation="EN 10219"),
        StandardField(designation="EN 10210"),
    )
    assert result.status is Status.NON_COMPLIANT


def test_standard_missing_offer_is_unverified():
    result = compare_standard(StandardField(designation="EN 10219"), None)
    assert result.status is Status.UNVERIFIED


def test_standard_absent_from_spec_is_not_specified():
    result = compare_standard(None, StandardField(designation="EN 10219"))
    assert result.status is Status.NOT_SPECIFIED


# ---------------------------------------------------------------------------
# Galvanizing
# ---------------------------------------------------------------------------


def hot_dip(mass: float = 505) -> GalvanizingField:
    return GalvanizingField(
        process=GalvanizingProcess.HOT_DIP,
        standard="EN ISO 1461",
        coating_mass_value=mass,
        coating_mass_unit="g/m2",
        page=5,
        excerpt="Hot-dip galvanized EN ISO 1461",
    )


def test_galvanizing_full_match_is_compliant():
    result = compare_galvanizing(hot_dip(), hot_dip(610))
    assert result.status is Status.COMPLIANT


def test_galvanizing_process_conflict_is_non_compliant():
    offer = GalvanizingField(
        process=GalvanizingProcess.BARE,
        raw_text="Mill finish, untreated",
        page=6,
        excerpt="Mill finish",
    )
    result = compare_galvanizing(hot_dip(), offer)
    assert result.status is Status.NON_COMPLIANT


def test_galvanizing_low_coating_mass_is_non_compliant():
    result = compare_galvanizing(hot_dip(505), hot_dip(300))
    assert result.status is Status.NON_COMPLIANT


def test_galvanizing_missing_offer_is_unverified():
    result = compare_galvanizing(hot_dip(), None)
    assert result.status is Status.UNVERIFIED


def test_galvanizing_partial_information_is_unverified():
    offer = GalvanizingField(process=GalvanizingProcess.HOT_DIP, page=7, excerpt="Hot dip")
    result = compare_galvanizing(hot_dip(), offer)
    assert result.status is Status.UNVERIFIED


def test_galvanizing_absent_from_spec_is_not_specified():
    result = compare_galvanizing(None, hot_dip())
    assert result.status is Status.NOT_SPECIFIED


def test_galvanizing_unsupported_unit_is_unverified():
    spec = GalvanizingField(coating_thickness_value=85, coating_thickness_unit="µm")
    offer = GalvanizingField(
        coating_thickness_value=3.4, coating_thickness_unit="thou"
    )
    result = compare_galvanizing(spec, offer)
    assert result.status is Status.UNVERIFIED


def test_galvanizing_standard_inference():
    spec = GalvanizingField(standard="EN ISO 1461")
    offer = GalvanizingField(
        standard="EN ISO 1461",
        coating_mass_value=610,
        coating_mass_unit="g/m2",
    )
    result = compare_galvanizing(spec, offer)
    assert result.status is Status.COMPLIANT


# ---------------------------------------------------------------------------
# Document level
# ---------------------------------------------------------------------------


def test_compare_document_returns_five_criteria_in_order():
    spec = ExtractedRequirements(
        dimensions=dims(40, 40),
        wall_thickness=thickness(3),
        material_grade=MaterialGradeField(grade="S235JRH"),
        galvanizing=hot_dip(),
        standard=StandardField(designation="EN 10219"),
    )
    offer = ExtractedRequirements(
        dimensions=dims(40, 40),
        wall_thickness=thickness(3),
        material_grade=MaterialGradeField(grade="S235JRH"),
        galvanizing=hot_dip(),
        standard=StandardField(designation="EN 10219"),
    )
    results = compare_document(spec, offer)
    assert [r.criterion for r in results] == [
        "dimensions",
        "wall_thickness",
        "material_grade",
        "galvanizing",
        "standard",
    ]
    assert all(r.status is Status.COMPLIANT for r in results)


def test_counts_and_summary():
    results = compare_document(
        ExtractedRequirements(
            dimensions=dims(40, 40),
            wall_thickness=thickness(3),
            material_grade=MaterialGradeField(grade="S235JRH"),
            galvanizing=hot_dip(),
            standard=StandardField(designation="EN 10219"),
        ),
        ExtractedRequirements(
            dimensions=dims(40, 40),
            wall_thickness=thickness(2),
            material_grade=MaterialGradeField(grade="S235JRH"),
            galvanizing=hot_dip(200),
        ),
    )
    counts = count_statuses(results)
    assert counts.compliant == 2
    assert counts.non_compliant == 2
    assert counts.unverified == 1
    assert counts.not_specified == 0
    summary = summarize_counts(results)
    assert "2 of 5" in summary


def test_not_specified_does_not_inflate_compliance():
    results = compare_document(
        ExtractedRequirements(dimensions=dims(40, 40)),
        ExtractedRequirements(dimensions=dims(40, 40)),
    )
    counts = count_statuses(results)
    assert counts.compliant == 1
    assert counts.not_specified == 4
    assert counts.compared_total == 1
