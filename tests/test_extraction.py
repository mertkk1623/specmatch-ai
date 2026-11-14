"""Tests for AI extraction handling (no real API calls).

Covers the brief's requirements: invalid JSON, incomplete model output, API
failures and evidence preservation.
"""

from __future__ import annotations

import json

import pytest

from src import extraction as ex
from src.schemas import DocumentKind, Status


VALID = {
    "document_kind": "manufacturer",
    "dimensions": {
        "width": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 x 40"},
        "height": {"value": 40, "unit": "mm", "page": 1, "excerpt": "40 x 40"},
        "raw_text": "40 x 40 mm",
        "page": 1,
        "excerpt": "40 x 40",
    },
    "wall_thickness": {
        "value": 3.0,
        "unit": "mm",
        "kind": "nominal",
        "page": 1,
        "excerpt": "3.0 mm nominal",
    },
    "material_grade": {
        "grade": "S235JRH",
        "equivalence_allowed": False,
        "page": 1,
        "excerpt": "S235JRH",
    },
    "galvanizing": None,
    "standard": {"designation": "EN 10219", "page": 1, "excerpt": "EN 10219"},
    "notes": [],
}


class FakeClient:
    """Minimal stand-in for the OpenAI client."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.chat = self
        self.completions = self

    def create(self, **kwargs):
        self.calls += 1
        if not self.responses:
            raise AssertionError("no more fake responses")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item

        class Message:
            content = item

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]
            model = "fake-model"

        return Response()


def fake_outcome(text: str):
    class Message:
        content = text

    class Choice:
        message = Message()

    class Response:
        choices = [Choice()]
        model = "fake-model"

    return Response()


def test_extract_json_block_handles_code_fences():
    raw = '```json\n{"a": 1}\n```'
    assert json.loads(ex.extract_json_block(raw)) == {"a": 1}


def test_extract_json_block_finds_object_in_prose():
    raw = 'Here you go:\n{"a": 1}\nHope this helps.'
    assert json.loads(ex.extract_json_block(raw)) == {"a": 1}


def test_extract_json_block_raises_without_json():
    with pytest.raises(ex.ExtractionError):
        ex.extract_json_block("no json here")


def test_parse_envelope_valid():
    envelope = ex.parse_envelope(json.dumps(VALID))
    assert envelope.dimensions.width.value == 40
    assert envelope.wall_thickness.kind.value == "nominal"


def test_parse_envelope_rejects_unknown_keys():
    payload = dict(VALID)
    payload["compliance_status"] = "compliant"
    with pytest.raises(ex.ExtractionError):
        ex.parse_envelope(json.dumps(payload))


def test_parse_envelope_accepts_partial_output():
    envelope = ex.parse_envelope(json.dumps({"dimensions": None, "notes": ["nothing found"]}))
    assert envelope.dimensions is None
    assert envelope.notes == ["nothing found"]


def test_parse_envelope_rejects_incomplete_typed_value():
    bad = {"dimensions": {"width": {"value": 40, "unit": "mm", "page": "one"}}}
    with pytest.raises(ex.ExtractionError):
        ex.parse_envelope(json.dumps(bad))


def test_extraction_retry_path(monkeypatch):
    client = FakeClient(["not json", json.dumps(VALID)])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    outcome = ex.extract_structured(
        api_key="x",
        text="page text",
        document_kind=DocumentKind.MANUFACTURER,
        filename="a.pdf",
        base_url="http://example",
        max_attempts=2,
    )
    assert outcome.repaired is True
    assert outcome.attempts == 2
    assert client.calls == 2


def test_extraction_failure_after_retries(monkeypatch):
    client = FakeClient(["bad", "still bad"])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    with pytest.raises(ex.ExtractionError):
        ex.extract_structured(
            api_key="x",
            text="page text",
            document_kind=DocumentKind.SPECIFICATION,
            filename="a.pdf",
            base_url="http://example",
            max_attempts=2,
        )


def test_api_error_is_translated(monkeypatch):
    import openai

    client = FakeClient([openai.APITimeoutError(request=None)])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    with pytest.raises(ex.ExtractionError) as info:
        ex.extract_structured(
            api_key="x",
            text="text",
            document_kind=DocumentKind.SPECIFICATION,
            filename="a.pdf",
            base_url="http://example",
            max_attempts=1,
        )
    assert "did not respond in time" in str(info.value)


def test_authentication_error_message(monkeypatch):
    import openai
    import httpx

    request = httpx.Request("POST", "https://example.test")
    response = httpx.Response(401, request=request)
    error = openai.AuthenticationError("bad key", response=response, body=None)
    client = FakeClient([error])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    with pytest.raises(ex.ExtractionError) as info:
        ex.extract_structured(
            api_key="x",
            text="text",
            document_kind=DocumentKind.SPECIFICATION,
            filename="a.pdf",
            base_url="http://example",
            max_attempts=1,
        )
    assert "DEPLOY_API_KEY" in str(info.value)


def test_empty_response_is_an_error(monkeypatch):
    client = FakeClient(["   "])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    with pytest.raises(ex.ExtractionError) as info:
        ex.extract_structured(
            api_key="x",
            text="text",
            document_kind=DocumentKind.SPECIFICATION,
            filename="a.pdf",
            base_url="http://example",
            max_attempts=1,
        )
    assert "empty" in str(info.value)


def test_explain_findings_parses_manufacturer_buckets(monkeypatch):
    from src.schemas import CriterionResult

    payload = {
        "manufacturers": {
            "Anadolu Profil": {"dimensions": "Section matches.", "bogus_key": "x"},
            "Unknown Corp": {"dimensions": "Should be ignored."},
        },
        "summary": "One of two suppliers matches the specification.",
    }
    client = FakeClient([json.dumps(payload)])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    criteria = [
        CriterionResult(
            criterion="dimensions",
            status=Status.COMPLIANT,
            headline="Matches",
            rule_explanation="Rule text",
        )
    ]
    result, summary = ex.explain_findings(
        api_key="x",
        base_url="http://example",
        manufacturers={"Anadolu Profil": criteria},
        spec_name="spec.pdf",
    )
    assert result == {"Anadolu Profil": {"dimensions": "Section matches."}}
    assert summary == "One of two suppliers matches the specification."


def test_explain_findings_returns_empty_on_failure(monkeypatch):
    import openai

    client = FakeClient([openai.APIConnectionError(request=None)])
    monkeypatch.setattr(ex, "_build_client", lambda *a, **k: client)
    result, summary = ex.explain_findings(
        api_key="x",
        base_url="http://example",
        manufacturers={"A": []},
        spec_name="spec.pdf",
    )
    assert result == {}
    assert summary is None
