"""DeepSeek extraction and explanation through the Deploy API.

Responsibilities are deliberately narrow:

* Extraction: turn page-tagged document text into one validated JSON object.
* Explanation: write short prose about findings whose status is *already*
  decided by :mod:`src.compliance`.

The model never returns a compliance status, and it is never trusted with page
numbers or excerpts without verification against the parsed pages.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from pydantic import ValidationError

from .schemas import (
    CriterionResult,
    DocumentKind,
    ExtractionEnvelope,
    Status,
)

DEFAULT_MODEL = "deepseek-ai/deepseek-v4.1-flash-1017"


class ExtractionError(RuntimeError):
    """A recoverable, user-facing extraction failure."""


EXTRACTION_SYSTEM_PROMPT = """You extract technical data from construction steel documents.

Rules you must follow:
1. Return JSON only. No markdown, no commentary, no code fences.
2. Copy values EXACTLY as printed in the document. Do not convert units, do not round, do not summarize.
3. Every value you report must be accompanied by the PDF page number where it appears and a short VERBATIM excerpt copied from that page (max 300 characters, no ellipses).
4. If a field is not explicitly stated in the document, return null for it. Never infer, never guess, never fill a value from general knowledge.
5. Never invent page numbers, standards, grades or product data.
6. If a document lists several products or sizes, report only the single product that the document clearly presents as its main subject. If several products are equally prominent and no single one is the subject, return null for dimensions and wall thickness and explain this in "notes".
7. Units must be copied as printed (for example "mm", "g/m2", "µm", "Z275"). If no unit is printed, return null for the unit.
8. "equivalence_allowed" is true only when the document explicitly permits an equivalent grade (for example "or equivalent").
9. "wall_thickness.kind" must be "nominal", "minimum" or "maximum", taken from the wording. Default to "nominal" only when the text states a plain thickness.
10. "galvanizing.process" must be one of: "hot_dip", "pre_galvanized", "electroplated", "bare", "unknown".
11. "applicable standard" means the product manufacturing standard (for example EN 10219), not a coating standard.
12. Place notes in the "notes" array. Notes are plain sentences, max 200 characters each, max 5 notes.
"""

EXTRACTION_USER_TEMPLATE = """Document kind: {document_kind}
File name: {filename}

Extract the five comparison fields for galvanized square steel hollow sections.

Return JSON with exactly this shape:
{{
  "document_kind": "{document_kind}",
  "product_family_statement": string|null,
  "dimensions": {{
    "width": {{"value": number|null, "unit": string|null, "page": number|null, "excerpt": string|null}},
    "height": {{"value": number|null, "unit": string|null, "page": number|null, "excerpt": string|null}},
    "raw_text": string|null, "page": number|null, "excerpt": string|null
  }}|null,
  "wall_thickness": {{"value": number|null, "unit": string|null, "kind": "nominal"|"minimum"|"maximum", "page": number|null, "excerpt": string|null}}|null,
  "material_grade": {{"grade": string|null, "equivalence_allowed": boolean, "page": number|null, "excerpt": string|null}}|null,
  "galvanizing": {{
    "process": "hot_dip"|"pre_galvanized"|"electroplated"|"bare"|"unknown"|null,
    "standard": string|null,
    "coating_mass_value": number|null, "coating_mass_unit": string|null,
    "coating_thickness_value": number|null, "coating_thickness_unit": string|null,
    "raw_text": string|null, "page": number|null, "excerpt": string|null
  }}|null,
  "standard": {{"designation": string|null, "page": number|null, "excerpt": string|null}}|null,
  "notes": [string]
}}

If a whole criterion is absent, return null for that criterion object.

=== DOCUMENT TEXT (page boundaries marked) ===
{text}
=== END OF DOCUMENT TEXT ===
"""

EXPLANATION_SYSTEM_PROMPT = """You explain comparison findings for a technical-office audience.

You are given findings whose compliance status has ALREADY been decided by deterministic rules.
Rules you must follow:
1. Never change, question or reinterpret a status. Explain the reasoning behind the given status.
2. Use only the supplied evidence. Do not add facts, standards, numbers or page references that are not in the input.
3. Do not invent page numbers. If a page number is not supplied, do not mention one.
4. Be concise and specific: 1-2 sentences per criterion, plain professional English.
5. Missing information must be described as unverified, never as acceptable.
6. Return JSON only, no markdown, no code fences.
"""

EXPLANATION_USER_TEMPLATE = """Specification: {spec_name}

Findings per manufacturer:
{findings}

Return JSON with exactly this shape:
{{
  "manufacturers": {{
    "<manufacturer name exactly as given>": {{
      "dimensions": "<explanation>",
      "wall_thickness": "<explanation>",
      "material_grade": "<explanation>",
      "galvanizing": "<explanation>",
      "standard": "<explanation>"
    }}
  }},
  "summary": "<two sentence overall summary>"
}}

Provide an explanation for every criterion key listed in the findings for that manufacturer.
Use only these criterion keys: dimensions, wall_thickness, material_grade, galvanizing, standard.
"""


# ---------------------------------------------------------------------------
# Low-level client helpers
# ---------------------------------------------------------------------------


@dataclass
class ModelResponse:
    text: str
    model: str


def _build_client(api_key: str, base_url: str, timeout: float):
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=1)


def _call_model(
    *,
    api_key: str,
    base_url: str,
    model: str,
    timeout: float,
    system: str,
    user: str,
    max_completion_tokens: int,
    reasoning_effort: str,
    client=None,
) -> ModelResponse:
    """Single Chat Completions call with explicit error translation."""

    import openai

    api = client or _build_client(api_key, base_url, timeout)
    try:
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "max_completion_tokens": max_completion_tokens,
        }
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        try:
            response = api.chat.completions.create(**kwargs)
        except openai.BadRequestError:
            # Some deployments reject reasoning_effort or the token parameter name.
            if "reasoning_effort" in kwargs:
                kwargs.pop("reasoning_effort")
                response = api.chat.completions.create(**kwargs)
            else:
                raise
    except openai.AuthenticationError as exc:
        raise ExtractionError(
            "The Deploy API rejected the API key. Check DEPLOY_API_KEY in your .env file."
        ) from exc
    except openai.RateLimitError as exc:
        raise ExtractionError(
            "The Deploy API rate limit was reached. Wait a moment and try again."
        ) from exc
    except openai.APITimeoutError as exc:
        raise ExtractionError(
            "The Deploy API did not respond in time. Try again, or use a smaller PDF."
        ) from exc
    except openai.APIConnectionError as exc:
        raise ExtractionError(
            "Could not reach the Deploy API. Check your network connection."
        ) from exc
    except openai.APIStatusError as exc:
        raise ExtractionError(
            f"The Deploy API returned an error (HTTP {exc.status_code})."
        ) from exc

    choice = response.choices[0] if response.choices else None
    content = (choice.message.content or "") if choice else ""
    if not content.strip():
        raise ExtractionError("The model returned an empty response.")
    return ModelResponse(text=content, model=getattr(response, "model", model))


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def extract_json_block(raw: str) -> str:
    """Pull the first JSON object out of a model response."""

    text = raw.strip()
    text = _FENCE_RE.sub("", text).strip()
    if text.startswith("{"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise ExtractionError("The model response did not contain a JSON object.")
    return text[start : end + 1]


def parse_envelope(raw: str) -> ExtractionEnvelope:
    payload = extract_json_block(raw)
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExtractionError("The model returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise ExtractionError("The model returned JSON that is not an object.")
    try:
        return ExtractionEnvelope.model_validate(data)
    except ValidationError as exc:
        raise ExtractionError(
            "The model output did not match the expected schema "
            f"({exc.error_count()} validation error(s))."
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass
class ExtractionOutcome:
    envelope: ExtractionEnvelope
    model: str
    attempts: int
    repaired: bool = False


def extract_structured(
    *,
    api_key: str,
    text: str,
    document_kind: DocumentKind,
    filename: str,
    base_url: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 180.0,
    max_completion_tokens: int = 4000,
    reasoning_effort: str = "high",
    max_attempts: int = 2,
) -> ExtractionOutcome:
    """Extract structured fields, retrying once with a repair instruction."""

    user = EXTRACTION_USER_TEMPLATE.format(
        document_kind=document_kind.value, filename=filename, text=text
    )
    last_error: ExtractionError | None = None

    for attempt in range(1, max_attempts + 1):
        prompt = user
        if last_error is not None:
            prompt = (
                user
                + "\n\nYour previous answer was rejected: "
                + str(last_error)
                + "\nReturn only valid JSON matching the required shape."
            )
        response = _call_model(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            system=EXTRACTION_SYSTEM_PROMPT,
            user=prompt,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort=reasoning_effort,
        )
        try:
            envelope = parse_envelope(response.text)
        except ExtractionError as exc:
            last_error = exc
            continue
        return ExtractionOutcome(
            envelope=envelope,
            model=response.model,
            attempts=attempt,
            repaired=attempt > 1,
        )

    raise last_error or ExtractionError("Extraction failed.")


def explain_findings(
    *,
    api_key: str,
    base_url: str,
    manufacturers: dict[str, list[CriterionResult]],
    spec_name: str,
    model: str = DEFAULT_MODEL,
    timeout: float = 120.0,
    max_completion_tokens: int = 2000,
) -> tuple[dict[str, dict[str, str]], str | None]:
    """Generate per-criterion explanations keyed by manufacturer name.

    Returns ``({manufacturer: {criterion: text}}, summary)``. Any failure
    returns empty results so the caller falls back to rule-based wording;
    an explanation failure must never break the analysis.
    """

    blocks: list[str] = []
    for name, criteria in manufacturers.items():
        blocks.append(f"\n--- Manufacturer: {name} ---")
        for result in criteria:
            blocks.append(
                json.dumps(
                    {
                        "criterion": result.criterion,
                        "status": result.status.value,
                        "specification": result.spec_display,
                        "catalogue": result.offer_display,
                        "checks": [
                            {
                                "label": check.label,
                                "outcome": check.outcome,
                                "spec": check.spec_text,
                                "offer": check.offer_text,
                                "note": check.note,
                            }
                            for check in result.checks
                        ],
                        "deterministic_reason": result.rule_explanation,
                    },
                    ensure_ascii=False,
                )
            )

    user = EXPLANATION_USER_TEMPLATE.format(
        spec_name=spec_name,
        findings="\n".join(blocks),
    )

    try:
        response = _call_model(
            api_key=api_key,
            base_url=base_url,
            model=model,
            timeout=timeout,
            system=EXPLANATION_SYSTEM_PROMPT,
            user=user,
            max_completion_tokens=max_completion_tokens,
            reasoning_effort="medium",
        )
        payload = json.loads(extract_json_block(response.text))
    except (ExtractionError, json.JSONDecodeError, ValidationError):
        return {}, None

    if not isinstance(payload, dict):
        return {}, None

    valid_keys = {"dimensions", "wall_thickness", "material_grade", "galvanizing", "standard"}
    raw_manufacturers = payload.get("manufacturers")
    result: dict[str, dict[str, str]] = {name: {} for name in manufacturers}

    if isinstance(raw_manufacturers, dict):
        lowered = {str(k).strip().lower(): v for k, v in raw_manufacturers.items()}
        for name in manufacturers:
            bucket = lowered.get(name.strip().lower())
            if not isinstance(bucket, dict):
                continue
            for key, value in bucket.items():
                if key not in valid_keys or not isinstance(value, str):
                    continue
                text = value.strip()
                if 0 < len(text) <= 600:
                    result[name][key] = text

    summary = payload.get("summary")
    summary_text = summary.strip() if isinstance(summary, str) and summary.strip() else None
    if summary_text and len(summary_text) > 900:
        summary_text = summary_text[:897].rstrip() + "…"
    return result, summary_text
