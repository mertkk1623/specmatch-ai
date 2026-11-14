"""Pipeline tests with the AI layer stubbed out.

These prove three things the brief requires:

* The comparison engine runs without any API access.
* A failing or malformed model response degrades gracefully instead of crashing.
* A model that returns a compliance status cannot influence the result.
"""

from __future__ import annotations

import json

import pytest

from src import extraction
from src.document_parser import ParsedDocument
from src.pipeline import AnalysisError, AnalysisInput, run_analysis
from src.schemas import (
    DocumentKind,
    ExtractionEnvelope,
    ParsedPage,
    Status,
)


class FakeSettings:
    api_key = "test-key"
    base_url = "http://example.invalid"
    model = "fake-model"
    timeout_seconds = 5.0
    max_completion_tokens = 1000
    reasoning_effort = "low"


SPEC_ENVELOPE = ExtractionEnvelope.model_validate(
    {
        "dimensions": {
            "width": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 x 40 x 3.0 mm"},
            "height": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 x 40 x 3.0 mm"},
            "raw_text": "40 x 40 x 3.0 mm",
            "page": 1,
            "excerpt": "40 x 40 x 3.0 mm",
        },
        "wall_thickness": {
            "value": 3.0,
            "unit": "mm",
            "kind": "nominal",
            "page": 1,
            "excerpt": "40 x 40 x 3.0 mm",
        },
        "material_grade": {
            "grade": "S235JRH",
            "page": 1,
            "excerpt": "Steel grade S235JRH",
        },
        "galvanizing": None,
        "standard": {"designation": "EN 10219", "page": 1, "excerpt": "EN 10219"},
    }
)

GOOD_OFFER = ExtractionEnvelope.model_validate(
    {
        "dimensions": {
            "width": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 mm x 40 mm"},
            "height": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 mm x 40 mm"},
            "raw_text": "40 mm x 40 mm",
            "page": 1,
            "excerpt": "40 mm x 40 mm",
        },
        "wall_thickness": {
            "value": 3.0,
            "unit": "mm",
            "kind": "nominal",
            "page": 1,
            "excerpt": "3.0 mm nominal",
        },
        "material_grade": {"grade": "S235JRH", "page": 1, "excerpt": "S235JRH"},
        "galvanizing": None,
        "standard": {"designation": "EN 10219-1", "page": 1, "excerpt": "EN 10219-1"},
    }
)

BAD_OFFER = ExtractionEnvelope.model_validate(
    {
        "dimensions": {
            "width": {"value": 50, "unit": "mm", "page": 1, "excerpt": "50 mm x 50 mm"},
            "height": {"value": 50, "unit": "mm", "page": 1, "excerpt": "50 mm x 50 mm"},
            "page": 1,
            "excerpt": "50 mm x 50 mm",
        },
        "wall_thickness": {
            "value": 2.5,
            "unit": "mm",
            "kind": "nominal",
            "page": 1,
            "excerpt": "2.5 mm nominal",
        },
        "material_grade": {"grade": "S275J0H", "page": 1, "excerpt": "S275J0H"},
        "galvanizing": None,
        "standard": None,
    }
)

DOC_TEXT = {
    "specification.pdf": (
        "Project specification for galvanized square hollow sections.\n"
        "Section profile: 40 x 40 x 3.0 mm\n"
        "Steel grade S235JRH to EN 10219"
    ),
    "a.pdf": (
        "Anadolu Profil product datasheet for square hollow sections.\n"
        "Outside dimensions 40 mm x 40 mm\n"
        "Wall thickness 3.0 mm nominal\n"
        "Steel grade S235JRH, manufacturing standard EN 10219-1"
    ),
    "b.pdf": (
        "Ege Metal box profile catalogue extract for structural range.\n"
        "Outside dimensions 50 mm x 50 mm\n"
        "Wall thickness 2.5 mm nominal\n"
        "Steel grade S275J0H, pre-galvanized strip"
    ),
}


def fake_parse(path, **_kwargs):
    name = str(path).replace("\\", "/").rsplit("/", 1)[-1]
    text = DOC_TEXT.get(name, "unrelated document text")
    return ParsedDocument(
        filename=name,
        pages=[ParsedPage(number=1, text=text)],
        parser="stub",
    )


def fake_extract(*, document_kind, filename, **_kwargs):
    mapping = {
        "specification.pdf": SPEC_ENVELOPE,
        "a.pdf": GOOD_OFFER,
        "b.pdf": BAD_OFFER,
    }
    return extraction.ExtractionOutcome(
        envelope=mapping[filename],
        model="stub-model",
        attempts=1,
    )


@pytest.fixture()
def patched(monkeypatch):
    monkeypatch.setattr("src.pipeline.parse_pdf", fake_parse)
    monkeypatch.setattr(extraction, "extract_structured", fake_extract)
    monkeypatch.setattr(
        extraction,
        "explain_findings",
        lambda **kwargs: ({}, None),
    )


def build_inputs(tmp_path) -> AnalysisInput:
    paths = []
    for name in ("specification.pdf", "a.pdf", "b.pdf"):
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.4 stub")
        paths.append(str(path))
    return AnalysisInput(
        spec_path=paths[0],
        manufacturer_paths=paths[1:],
        manufacturer_names=["Supplier A", "Supplier B"],
    )


def test_pipeline_runs_without_network(patched, tmp_path):
    result = run_analysis(
        build_inputs(tmp_path),
        api_key="test-key",
        settings=FakeSettings(),
        enable_ai_explanations=False,
    )

    assert result.spec.document_name == "specification.pdf"
    assert [m.name for m in result.manufacturers] == ["Supplier A", "Supplier B"]

    good = result.manufacturer("Supplier A")
    bad = result.manufacturer("Supplier B")
    assert good is not None and bad is not None

    assert good.criterion("dimensions").status is Status.COMPLIANT
    assert good.criterion("wall_thickness").status is Status.COMPLIANT
    assert good.criterion("material_grade").status is Status.COMPLIANT
    assert good.criterion("standard").status is Status.COMPLIANT
    # Specification says nothing about galvanizing in this fixture.
    assert good.criterion("galvanizing").status is Status.NOT_SPECIFIED

    assert bad.criterion("dimensions").status is Status.NON_COMPLIANT
    assert bad.criterion("wall_thickness").status is Status.NON_COMPLIANT
    assert bad.criterion("material_grade").status is Status.NON_COMPLIANT
    assert bad.criterion("standard").status is Status.UNVERIFIED

    assert result.summary_source == "rule"
    assert result.summary


def test_model_cannot_return_a_status(patched, monkeypatch, tmp_path):
    """Even if a model smuggles a status into its JSON, Pydantic rejects it."""

    payload = dict(json.loads(SPEC_ENVELOPE.model_dump_json()))
    payload["status"] = "compliant"
    payload["criteria"] = {"dimensions": "compliant"}

    with pytest.raises(extraction.ExtractionError):
        extraction.parse_envelope(json.dumps(payload))


def test_api_failure_is_a_user_facing_error(patched, monkeypatch, tmp_path):
    def boom(**_kwargs):
        raise extraction.ExtractionError(
            "The Deploy API did not respond in time. Try again, or use a smaller PDF."
        )

    monkeypatch.setattr(extraction, "extract_structured", boom)

    with pytest.raises(AnalysisError) as info:
        run_analysis(
            build_inputs(tmp_path),
            api_key="test-key",
            settings=FakeSettings(),
            enable_ai_explanations=False,
        )
    assert "did not respond in time" in str(info.value)


def test_missing_api_key_is_rejected(tmp_path):
    with pytest.raises(AnalysisError) as info:
        run_analysis(build_inputs(tmp_path), api_key="", settings=FakeSettings())
    assert "DEPLOY_API_KEY" in str(info.value)


def test_more_than_two_manufacturers_is_rejected(patched, tmp_path):
    inputs = build_inputs(tmp_path)
    inputs.manufacturer_paths.append(inputs.manufacturer_paths[0])
    with pytest.raises(AnalysisError) as info:
        run_analysis(inputs, api_key="test-key", settings=FakeSettings())
    assert "up to two" in str(info.value)


def test_explanation_failure_keeps_statuses_and_falls_back(patched, monkeypatch, tmp_path):
    def boom(**_kwargs):
        raise RuntimeError("narrative service down")

    monkeypatch.setattr(extraction, "explain_findings", boom)

    result = run_analysis(
        build_inputs(tmp_path),
        api_key="test-key",
        settings=FakeSettings(),
        enable_ai_explanations=True,
    )

    assert result.summary_source == "rule"
    assert result.manufacturer("Supplier A").criterion("dimensions").status is Status.COMPLIANT
    assert result.manufacturer("Supplier B").criterion("dimensions").status is Status.NON_COMPLIANT
    assert all(
        criterion.explanation_source == "rule"
        for manufacturer in result.manufacturers
        for criterion in manufacturer.criteria
    )
    assert any(
        "AI explanations were unavailable" in issue.message
        for issue in result.validation_issues
    )


def test_ai_explanations_are_attached_but_do_not_change_statuses(patched, monkeypatch, tmp_path):
    def explanations(**_kwargs):
        return (
            {
                "Supplier A": {
                    "dimensions": "Section size matches the specified profile.",
                    "wall_thickness": "Wall thickness matches.",
                },
                "Supplier B": {
                    "dimensions": "Offered section is 50 x 50 mm, not 40 x 40 mm.",
                },
            },
            "Supplier A matches on the measured fields; Supplier B does not.",
        )

    monkeypatch.setattr(extraction, "explain_findings", explanations)

    result = run_analysis(
        build_inputs(tmp_path),
        api_key="test-key",
        settings=FakeSettings(),
        enable_ai_explanations=True,
    )

    a = result.manufacturer("Supplier A")
    b = result.manufacturer("Supplier B")
    assert a.criterion("dimensions").ai_explanation == "Section size matches the specified profile."
    assert a.criterion("dimensions").status is Status.COMPLIANT
    assert b.criterion("dimensions").status is Status.NON_COMPLIANT
    assert b.criterion("dimensions").explanation_source == "ai"
    # A criterion with no AI text keeps the deterministic text and label.
    assert b.criterion("wall_thickness").explanation_source == "rule"
    assert result.summary_source == "ai"


def test_fabricated_evidence_is_stripped_by_the_pipeline(patched, monkeypatch, tmp_path):
    fabricated = ExtractionEnvelope.model_validate(
        {
            "dimensions": {
                "width": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 x 40 mm"},
                "height": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 x 40 mm"},
                "page": 7,
                "excerpt": "40 x 40 mm",
            }
        }
    )

    def extract_with_bad_page(*, filename, **_kwargs):
        envelope = fabricated if filename == "a.pdf" else ExtractionEnvelope()
        return extraction.ExtractionOutcome(envelope=envelope, model="stub", attempts=1)

    monkeypatch.setattr(extraction, "extract_structured", extract_with_bad_page)

    result = run_analysis(
        build_inputs(tmp_path),
        api_key="test-key",
        settings=FakeSettings(),
        enable_ai_explanations=False,
    )

    dimensions = result.manufacturer("Supplier A").criterion("dimensions")
    assert dimensions.spec_evidence is None or dimensions.spec_evidence.page != 7
    assert any("does not exist in the document" in issue.message for issue in result.validation_issues)
