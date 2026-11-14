"""Evidence verification.

The model is asked for page numbers and short verbatim excerpts. Because a
language model can hallucinate both, every reference is checked against the
text parsed from the real PDF page. Unverifiable references are dropped and
reported as validation issues rather than displayed.
"""

from __future__ import annotations

from .schemas import (
    ExtractedRequirements,
    ParsedPage,
    ValidationIssue,
)
from .units import contains_excerpt, normalize_space


def page_lookup(pages: list[ParsedPage]) -> dict[int, str]:
    return {page.number: page.text for page in pages}


def verify_evidence(
    requirements: ExtractedRequirements,
    pages: list[ParsedPage],
    document_name: str,
) -> tuple[ExtractedRequirements, list[ValidationIssue]]:
    """Return a copy with unverifiable page/excerpt references removed."""

    lookup = page_lookup(pages)
    issues: list[ValidationIssue] = []
    verified_pages: dict[str, int] = {}

    def check(field_name: str, page: int | None, excerpt: str | None) -> tuple[int | None, str | None]:
        if page is None and not excerpt:
            return None, None
        if page is None:
            issues.append(
                ValidationIssue(
                    document=document_name,
                    field=field_name,
                    severity="warning",
                    message="Evidence excerpt had no page number and was not shown.",
                )
            )
            return None, None
        if page not in lookup:
            issues.append(
                ValidationIssue(
                    document=document_name,
                    field=field_name,
                    severity="warning",
                    message=f"Cited page {page} does not exist in the document; reference removed.",
                )
            )
            return None, None
        if not excerpt:
            return page, None
        if contains_excerpt(lookup[page], excerpt):
            verified_pages[field_name] = page
            return page, normalize_space(excerpt)
        issues.append(
            ValidationIssue(
                document=document_name,
                field=field_name,
                severity="warning",
                message=(
                    f"Excerpt could not be found on page {page}; the unverified "
                    "reference was removed."
                ),
            )
        )
        return page, None

    updates: dict[str, object] = {}

    def handle_simple(field_name: str, obj):
        if obj is None:
            return None
        page, excerpt = check(field_name, getattr(obj, "page", None), getattr(obj, "excerpt", None))
        return obj.model_copy(update={"page": page, "excerpt": excerpt})

    updates["dimensions"] = handle_simple("dimensions", requirements.dimensions)
    updates["wall_thickness"] = handle_simple("wall_thickness", requirements.wall_thickness)
    updates["material_grade"] = handle_simple("material_grade", requirements.material_grade)
    updates["galvanizing"] = handle_simple("galvanizing", requirements.galvanizing)
    updates["standard"] = handle_simple("standard", requirements.standard)

    cleaned = requirements.model_copy(update=updates)
    return cleaned, issues


def evidence_map(requirements: ExtractedRequirements) -> dict[str, int]:
    """Criterion → verified page number, for the compact evidence strip."""

    mapping: dict[str, int] = {}
    for key in ("dimensions", "wall_thickness", "material_grade", "galvanizing", "standard"):
        field = getattr(requirements, key, None)
        page = getattr(field, "page", None) if field is not None else None
        if page is not None:
            mapping[key] = page
    return mapping
