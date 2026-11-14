"""Analysis orchestration.

Order of operations matters and mirrors the brief:

    parse PDFs → AI extracts fields → Pydantic validates → evidence verified
    → Python decides statuses → AI explains (optional) → result object

Nothing here decides compliance; that stays in :mod:`src.compliance`.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from . import extraction
from .compliance import compare_document, count_statuses, summarize_counts
from .document_parser import ParsedDocument, parse_pdf
from .evidence import evidence_map, verify_evidence
from .schemas import (
    AnalysisResult,
    DocumentKind,
    DocumentMeta,
    ExtractedRequirements,
    ManufacturerAnalysis,
    SpecAnalysis,
    Status,
    ValidationIssue,
)

ProgressCallback = Callable[[str, float], None]


class AnalysisError(RuntimeError):
    """User-facing analysis failure with a safe message."""


@dataclass
class AnalysisInput:
    spec_path: str
    manufacturer_paths: list[str]
    manufacturer_names: list[str]


def _meta(document: ParsedDocument, kind: DocumentKind) -> DocumentMeta:
    return DocumentMeta(
        filename=document.filename,
        kind=kind,
        page_count=document.page_count,
        parser=document.parser,
        tables_found=len(document.tables),
        char_count=document.char_count,
        warnings=list(document.warnings),
    )


def _validate_pages(document: ParsedDocument, kind_label: str) -> None:
    if document.page_count == 0:
        raise AnalysisError(f"{kind_label}: the PDF has no pages.")
    if document.is_empty:
        raise AnalysisError(
            f"{kind_label}: no extractable text was found. Scanned PDFs need OCR, "
            "which this version does not support."
        )


def _extract(
    *,
    document: ParsedDocument,
    kind: DocumentKind,
    api_key: str,
    settings,
    progress: ProgressCallback | None,
    label: str,
) -> tuple[ExtractedRequirements, list[ValidationIssue], str, int]:
    text = document.numbered_text()
    if not text.strip():
        raise AnalysisError(f"{label}: no text available for extraction.")

    try:
        outcome = extraction.extract_structured(
            api_key=api_key,
            text=text,
            document_kind=kind,
            filename=document.filename,
            base_url=settings.base_url,
            model=settings.model,
            timeout=settings.timeout_seconds,
            max_completion_tokens=settings.max_completion_tokens,
            reasoning_effort=settings.reasoning_effort,
        )
    except extraction.ExtractionError as exc:
        # Surface a safe, actionable message instead of a raw API exception.
        raise AnalysisError(f"{label}: {exc}") from exc
    requirements = outcome.envelope.to_requirements(kind)
    verified, issues = verify_evidence(requirements, document.pages, document.filename)

    if not _has_any_field(verified):
        issues.append(
            ValidationIssue(
                document=document.filename,
                field=None,
                severity="warning",
                message=(
                    "No comparison fields could be extracted from this document. "
                    "Every criterion will be reported as unverified or not specified."
                ),
            )
        )
    if progress:
        progress(label, 1.0)
    return verified, issues, outcome.model, outcome.attempts


def _has_any_field(req: ExtractedRequirements) -> bool:
    return any(
        [
            req.dimensions is not None,
            req.wall_thickness is not None,
            req.material_grade is not None,
            req.galvanizing is not None,
            req.standard is not None,
        ]
    )


def _manufacturer_label(path: str, fallback_index: int) -> str:
    from pathlib import Path

    stem = Path(path).stem
    cleaned = stem.replace("_", " ").replace("-", " ").strip()
    if not cleaned:
        return f"Manufacturer {fallback_index}"
    return cleaned.title()


def run_analysis(
    data: AnalysisInput,
    *,
    api_key: str,
    settings,
    enable_ai_explanations: bool = True,
    progress: ProgressCallback | None = None,
) -> AnalysisResult:
    """Run the full analysis and return a validated result object."""

    if not api_key:
        raise AnalysisError(
            "No Deploy API key is configured. Add DEPLOY_API_KEY to your .env file."
        )
    if not data.spec_path:
        raise AnalysisError("A specification PDF is required.")
    if not data.manufacturer_paths:
        raise AnalysisError("At least one manufacturer PDF is required.")
    if len(data.manufacturer_paths) > 2:
        raise AnalysisError("This version compares up to two manufacturer documents.")

    started = time.time()
    parser_notes: list[str] = []
    issues: list[ValidationIssue] = []

    def step(message: str, fraction: float) -> None:
        if progress:
            progress(message, fraction)

    # 1. Parse specification
    step("Parsing specification PDF", 0.05)
    try:
        spec_doc = parse_pdf(data.spec_path)
    except Exception as exc:  # noqa: BLE001 - converted into a safe message
        raise AnalysisError(f"The specification could not be parsed: {exc}") from exc
    _validate_pages(spec_doc, "Specification")
    parser_notes.extend(f"Specification: {w}" for w in spec_doc.warnings)
    parser_notes.append(f"Specification parsed with {spec_doc.parser} ({spec_doc.page_count} page(s)).")

    # 2. Parse manufacturer documents
    offer_docs: list[ParsedDocument] = []
    for index, path in enumerate(data.manufacturer_paths, start=1):
        step(f"Parsing manufacturer document {index}", 0.1 + 0.05 * index)
        try:
            document = parse_pdf(path)
        except Exception as exc:  # noqa: BLE001
            raise AnalysisError(
                f"Manufacturer document {index} could not be parsed: {exc}"
            ) from exc
        _validate_pages(document, f"Manufacturer document {index}")
        parser_notes.extend(f"Manufacturer {index}: {w}" for w in document.warnings)
        parser_notes.append(
            f"Manufacturer {index} parsed with {document.parser} "
            f"({document.page_count} page(s))."
        )
        offer_docs.append(document)

    # 3. Extract specification requirements
    step("Extracting specification requirements", 0.25)
    spec_req, spec_issues, model_used, _attempts = _extract(
        document=spec_doc,
        kind=DocumentKind.SPECIFICATION,
        api_key=api_key,
        settings=settings,
        progress=None,
        label="Specification",
    )
    issues.extend(spec_issues)

    spec_analysis = SpecAnalysis(
        document_name=spec_doc.filename,
        document_meta=_meta(spec_doc, DocumentKind.SPECIFICATION),
        requirements=spec_req,
        study_description=spec_req.product_family_statement,
        evidence={key: _ref(spec_req, key) for key in evidence_map(spec_req)},
        validation_issues=spec_issues,
    )

    # 4. Extract each manufacturer and compare deterministically
    manufacturers: list[ManufacturerAnalysis] = []
    ai_inputs = {}
    for index, (document, path) in enumerate(zip(offer_docs, data.manufacturer_paths), start=1):
        step(f"Extracting manufacturer data ({index}/{len(offer_docs)})", 0.35 + 0.2 * index)
        name = (
            data.manufacturer_names[index - 1].strip()
            if index - 1 < len(data.manufacturer_names) and data.manufacturer_names[index - 1].strip()
            else _manufacturer_label(path, index)
        )
        offer_req, offer_issues, _, _ = _extract(
            document=document,
            kind=DocumentKind.MANUFACTURER,
            api_key=api_key,
            settings=settings,
            progress=None,
            label=name,
        )
        issues.extend(offer_issues)

        results = compare_document(spec_req, offer_req)
        counts = count_statuses(results)
        manufacturers.append(
            ManufacturerAnalysis(
                name=name,
                document_name=document.filename,
                document_meta=_meta(document, DocumentKind.MANUFACTURER),
                criteria=results,
                counts=counts,
                warnings=list(document.warnings) + [i.message for i in offer_issues],
            )
        )
        ai_inputs[name] = results

    # 5. Optional AI narrative (never affects statuses)
    summary = ""
    summary_source = "rule"
    if enable_ai_explanations:
        step("Writing explanations", 0.85)
        try:
            explanations, ai_summary = extraction.explain_findings(
                api_key=api_key,
                base_url=settings.base_url,
                manufacturers=ai_inputs,
                spec_name=spec_doc.filename,
                model=settings.model,
                timeout=min(settings.timeout_seconds, 150.0),
            )
        except Exception as exc:  # noqa: BLE001 - narrative is optional
            explanations, ai_summary = {}, None
            issues.append(
                ValidationIssue(
                    document=spec_doc.filename,
                    field=None,
                    severity="warning",
                    message=(
                        "AI explanations were unavailable ("
                        + type(exc).__name__
                        + "); the report uses deterministic rule wording."
                    ),
                )
            )

        for manufacturer in manufacturers:
            bucket = explanations.get(manufacturer.name, {})
            for result in manufacturer.criteria:
                text = bucket.get(result.criterion)
                if text:
                    result.ai_explanation = text
                    result.explanation_source = "ai"
        if ai_summary:
            summary = ai_summary
            summary_source = "ai"

    step("Preparing results", 0.95)
    if not summary:
        summary = _deterministic_summary(manufacturers)

    return AnalysisResult(
        analysis_id=uuid.uuid4().hex[:12],
        created_at=datetime.now(timezone.utc),
        spec=spec_analysis,
        manufacturers=manufacturers,
        summary=summary,
        summary_source=summary_source,
        model=model_used,
        parser_notes=parser_notes,
        validation_issues=issues,
        duration_seconds=round(time.time() - started, 1),
    )


def _ref(req: ExtractedRequirements, key: str):
    from .schemas import EvidenceRef

    field = getattr(req, key, None)
    if field is None:
        return None
    page = getattr(field, "page", None)
    excerpt = getattr(field, "excerpt", None)
    if page is None and not excerpt:
        return None
    return EvidenceRef(page=page, excerpt=excerpt)


def _deterministic_summary(manufacturers: list[ManufacturerAnalysis]) -> str:
    if not manufacturers:
        return "No manufacturer documents were compared."
    parts: list[str] = []
    for manufacturer in manufacturers:
        counts = manufacturer.counts
        if counts.compared_total == 0:
            parts.append(
                f"{manufacturer.name}: none of the five criteria were stated in the specification."
            )
            continue
        verdict = "all compared criteria compliant" if counts.non_compliant == 0 and counts.unverified == 0 else (
            "at least one clear conflict" if counts.non_compliant else "no clear conflicts, but gaps remain"
        )
        parts.append(
            f"{manufacturer.name}: {counts.compliant} compliant, "
            f"{counts.non_compliant} non-compliant, {counts.unverified} unverified "
            f"— {verdict}."
        )
    return " ".join(parts)


def result_from_json(payload: str | dict) -> AnalysisResult:
    if isinstance(payload, dict):
        return AnalysisResult.model_validate(payload)
    return AnalysisResult.model_validate_json(payload)


def status_totals(result: AnalysisResult) -> dict[str, int]:
    counts = result.all_counts()
    return {
        "compliant": counts.compliant,
        "non_compliant": counts.non_compliant,
        "unverified": counts.unverified,
        "not_specified": counts.not_specified,
    }


__all__ = [
    "AnalysisError",
    "AnalysisInput",
    "run_analysis",
    "result_from_json",
    "status_totals",
    "Status",
    "summarize_counts",
]
