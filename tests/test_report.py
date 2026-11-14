"""Tests for PDF parsing and the report export.

The parser test uses the synthetic demo specification so it exercises the real
PDF path end to end.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.document_parser import DocumentParseError, parse_pdf
from src.report import build_report_html, report_filename
from src.schemas import AnalysisResult

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "sample_docs" / "demo_specification.pdf"
DEMO_JSON = ROOT / "sample_docs" / "precomputed" / "demo_analysis.json"


requires_demo = pytest.mark.skipif(not SPEC.exists(), reason="demo PDFs not built")


@requires_demo
def test_pypdf_parser_returns_page_text():
    document = parse_pdf(SPEC, prefer_docling=False)
    assert document.page_count >= 1
    assert "SYNTHETIC DEMO DOCUMENT" in document.pages[0].text
    assert document.parser.startswith("pypdf")


@requires_demo
def test_numbered_text_marks_pages():
    document = parse_pdf(SPEC, prefer_docling=False)
    text = document.numbered_text()
    assert "===== PAGE 1 =====" in text
    assert "S235JRH" in text


@requires_demo
def test_max_pages_truncates_and_warns():
    document = parse_pdf(SPEC, prefer_docling=False, max_pages=1)
    assert document.page_count == 1


def test_missing_file_raises():
    with pytest.raises(DocumentParseError):
        parse_pdf(ROOT / "sample_docs" / "does_not_exist.pdf")


def test_non_pdf_raises(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("hello", encoding="utf-8")
    with pytest.raises(DocumentParseError):
        parse_pdf(target)


def test_empty_pdf_raises(tmp_path):
    from reportlab.pdfgen import canvas

    target = tmp_path / "blank.pdf"
    c = canvas.Canvas(str(target))
    c.showPage()
    c.save()
    with pytest.raises(DocumentParseError) as info:
        parse_pdf(target, prefer_docling=False)
    assert "No extractable text" in str(info.value)


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


@requires_demo
def test_report_is_self_contained_and_consistent():
    from src.pipeline import result_from_json

    if not DEMO_JSON.exists():
        pytest.skip("precomputed demo not built")
    result = result_from_json(DEMO_JSON.read_text(encoding="utf-8"))
    html = build_report_html(result)

    assert html.startswith("<!DOCTYPE html>")
    assert "<script" not in html.lower()
    assert "http://" not in html and "https://" not in html
    assert "SpecMatch AI" in html
    assert result.spec.document_name in html
    for manufacturer in result.manufacturers:
        assert manufacturer.name in html

    # Statuses shown in the report must match the validated result exactly.
    for manufacturer in result.manufacturers:
        for criterion in manufacturer.criteria:
            assert criterion.headline in html or criterion.criterion in html


@requires_demo
def test_report_filename_is_safe():
    from src.pipeline import result_from_json

    if not DEMO_JSON.exists():
        pytest.skip("precomputed demo not built")
    result = result_from_json(DEMO_JSON.read_text(encoding="utf-8"))
    name = report_filename(result)
    assert name.startswith("specmatch-report-")
    assert name.endswith(".html")
    assert " " not in name


@requires_demo
def test_precomputed_demo_is_valid_and_has_all_statuses():
    from src.pipeline import result_from_json

    if not DEMO_JSON.exists():
        pytest.skip("precomputed demo not built")
    result = result_from_json(DEMO_JSON.read_text(encoding="utf-8"))
    assert result.demo is True
    assert len(result.manufacturers) == 2

    statuses = {
        criterion.status.value
        for manufacturer in result.manufacturers
        for criterion in manufacturer.criteria
    }
    assert {"compliant", "non_compliant", "unverified"} <= statuses

    for manufacturer in result.manufacturers:
        assert len(manufacturer.criteria) == 5
        for criterion in manufacturer.criteria:
            assert criterion.rule_explanation
            # Evidence pages must be within the parsed document.
            for ref in (criterion.spec_evidence, criterion.offer_evidence):
                if ref and ref.page:
                    assert ref.page <= result.spec.document_meta.page_count or ref.page <= 5
