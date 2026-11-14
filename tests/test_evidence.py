"""Tests for evidence verification (no fabricated page references)."""

from __future__ import annotations

from src.evidence import evidence_map, verify_evidence
from src.schemas import (
    DimensionsField,
    EvidenceRef,
    ExtractedRequirements,
    MaterialGradeField,
    ParsedPage,
    Quantity,
    StandardField,
)


PAGES = [
    ParsedPage(number=1, text="Project specification\nSquare hollow sections 40 x 40 x 3 mm"),
    ParsedPage(number=2, text="Material grade S235JRH to EN 10219"),
]


def requirements() -> ExtractedRequirements:
    return ExtractedRequirements(
        dimensions=DimensionsField(
            width=Quantity(value=40, unit="mm", page=1, excerpt="40 x 40 x 3 mm"),
            height=Quantity(value=40, unit="mm", page=1, excerpt="40 x 40 x 3 mm"),
            page=1,
            excerpt="40 x 40 x 3 mm",
        ),
        material_grade=MaterialGradeField(
            grade="S235JRH", page=2, excerpt="Material grade S235JRH"
        ),
        standard=StandardField(designation="EN 10219", page=2, excerpt="EN 10219"),
    )


def test_valid_evidence_is_preserved():
    cleaned, issues = verify_evidence(requirements(), PAGES, "spec.pdf")
    assert issues == []
    assert cleaned.dimensions is not None
    assert cleaned.dimensions.page == 1
    assert cleaned.material_grade is not None
    assert cleaned.material_grade.excerpt == "Material grade S235JRH"
    assert evidence_map(cleaned) == {
        "dimensions": 1,
        "material_grade": 2,
        "standard": 2,
    }


def test_fabricated_page_is_removed_and_reported():
    doc = requirements()
    doc.standard = StandardField(designation="EN 10219", page=99, excerpt="EN 10219")
    cleaned, issues = verify_evidence(doc, PAGES, "spec.pdf")
    assert cleaned.standard is not None
    assert cleaned.standard.page is None
    assert any("page 99" in issue.message for issue in issues)


def test_fabricated_excerpt_is_removed():
    doc = requirements()
    doc.dimensions = DimensionsField(
        width=Quantity(value=40, unit="mm"),
        height=Quantity(value=40, unit="mm"),
        page=1,
        excerpt="45 x 45 x 3 mm",
    )
    cleaned, issues = verify_evidence(doc, PAGES, "spec.pdf")
    assert cleaned.dimensions is not None
    assert cleaned.dimensions.excerpt is None
    assert cleaned.dimensions.page == 1
    assert any("could not be found" in issue.message for issue in issues)


def test_evidence_without_page_is_dropped():
    doc = requirements()
    doc.material_grade = MaterialGradeField(grade="S235JRH", excerpt="S235JRH")
    cleaned, issues = verify_evidence(doc, PAGES, "spec.pdf")
    assert cleaned.material_grade is not None
    assert cleaned.material_grade.excerpt is None
    assert any("no page number" in issue.message for issue in issues)


def test_evidence_ref_helper():
    ref = EvidenceRef(page=3, excerpt="A" * 400)
    assert ref.is_present
    assert len(ref.short(50)) <= 50
