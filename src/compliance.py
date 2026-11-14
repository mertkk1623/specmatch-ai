"""Deterministic compliance engine.

This module is the only place that decides a status. It is pure Python, has no
network access, and is fully unit tested. The AI never returns a status.

Rules (V1, documented in PLAN.md):

* A criterion absent from the specification → ``NOT_SPECIFIED`` (neutral, not a
  compliance verdict).
* Missing / ambiguous / inconvertible manufacturer data → ``UNVERIFIED``.
* A clear conflict → ``NON_COMPLIANT``.
* Only complete matching evidence → ``COMPLIANT``.
"""

from __future__ import annotations

from .schemas import (
    CheckDetail,
    CriterionResult,
    DimensionsField,
    EvidenceRef,
    ExtractedRequirements,
    GalvanizingField,
    MaterialGradeField,
    StandardField,
    Status,
    StatusCounts,
    ThicknessField,
    ThicknessKind,
)
from .units import (
    allows_equivalence,
    normalize_grade,
    normalize_space,
    normalize_standard,
    standards_compatible,
    to_g_per_m2,
    to_mm,
    to_um,
)

# Rounding guard: catalogue values are printed to 0.1 mm in practice.
LENGTH_TOLERANCE_MM = 0.1
COATING_TOLERANCE = 0.5


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _evidence(page: int | None, excerpt: str | None) -> EvidenceRef | None:
    if page is None and not excerpt:
        return None
    return EvidenceRef(page=page, excerpt=excerpt)


def _fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{round(value):g}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _length_display(value: float | None, unit: str | None) -> str:
    if value is None:
        return "—"
    return f"{_fmt_number(value)} {unit}".strip() if unit else _fmt_number(value)


# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------


def _dimensions_populated(field: DimensionsField | None) -> bool:
    if field is None:
        return False
    return bool(
        (field.width and field.width.value is not None)
        or (field.height and field.height.value is not None)
        or (field.raw_text and field.raw_text.strip())
    )


def compare_dimensions(
    spec: DimensionsField | None, offer: DimensionsField | None
) -> CriterionResult:
    evidence_spec = _evidence(
        spec.page if spec else None,
        (spec.excerpt if spec else None) or (spec.raw_text if spec else None),
    )
    evidence_offer = _evidence(
        offer.page if offer else None,
        (offer.excerpt if offer else None) or (offer.raw_text if offer else None),
    )

    if not _dimensions_populated(spec):
        return CriterionResult(
            criterion="dimensions",
            status=Status.NOT_SPECIFIED,
            headline="No profile dimensions stated in the specification",
            spec_display=None,
            spec_evidence=evidence_spec,
            rule_explanation=(
                "The specification does not state a profile size, so this criterion "
                "was not compared."
            ),
        )

    if not _dimensions_populated(offer):
        return CriterionResult(
            criterion="dimensions",
            status=Status.UNVERIFIED,
            headline="No profile dimensions found in the catalogue",
            spec_display=_dimensions_spec_display(spec),
            offer_display=None,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The catalogue does not state a profile size that could be matched "
                "to the specified section. Missing information is never treated as compliant."
            ),
        )

    spec_w = to_mm(spec.width.value, spec.width.unit) if spec.width else None
    spec_h = to_mm(spec.height.value, spec.height.unit) if spec.height else None
    offer_w = to_mm(offer.width.value, offer.width.unit) if offer.width else None
    offer_h = to_mm(offer.height.value, offer.height.unit) if offer.height else None

    checks: list[CheckDetail] = []
    missing: list[str] = []

    for label, spec_val, offer_val in (
        ("Width", spec_w, offer_w),
        ("Height", spec_h, offer_h),
    ):
        if spec_val is None:
            missing.append(f"{label.lower()} in the specification")
        elif offer_val is None:
            missing.append(f"{label.lower()} in the catalogue")
        elif abs(spec_val - offer_val) <= LENGTH_TOLERANCE_MM:
            checks.append(
                CheckDetail(
                    label=label,
                    outcome="pass",
                    spec_text=f"{_fmt_number(spec_val)} mm",
                    offer_text=f"{_fmt_number(offer_val)} mm",
                )
            )
        else:
            checks.append(
                CheckDetail(
                    label=label,
                    outcome="fail",
                    spec_text=f"{_fmt_number(spec_val)} mm",
                    offer_text=f"{_fmt_number(offer_val)} mm",
                    note=f"Difference of {_fmt_number(abs(spec_val - offer_val))} mm.",
                )
            )

    spec_display = _dimensions_spec_display(spec)
    offer_display = _dimensions_offer_display(offer, offer_w, offer_h)

    if any(check.outcome == "fail" for check in checks):
        failed = ", ".join(c.label.lower() for c in checks if c.outcome == "fail")
        return CriterionResult(
            criterion="dimensions",
            status=Status.NON_COMPLIANT,
            headline=f"Offered section differs in {failed}",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            checks=checks,
            rule_explanation=(
                "The offered section size does not match the specified profile "
                "within the 0.1 mm rounding tolerance used in V1."
            ),
        )

    if missing:
        return CriterionResult(
            criterion="dimensions",
            status=Status.UNVERIFIED,
            headline="Profile size could not be fully verified",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            checks=checks,
            rule_explanation=(
                "Required evidence is incomplete: missing "
                + " and ".join(missing)
                + ". The criterion remains unverified."
            ),
        )

    return CriterionResult(
        criterion="dimensions",
        status=Status.COMPLIANT,
        headline="Offered section matches the specified profile",
        spec_display=spec_display,
        offer_display=offer_display,
        spec_evidence=evidence_spec,
        offer_evidence=evidence_offer,
        checks=checks,
        rule_explanation=(
            "Width and height match the specification within the 0.1 mm "
            "rounding tolerance used in V1."
        ),
    )


def _dimensions_spec_display(field: DimensionsField | None) -> str | None:
    if not field:
        return None
    if field.width and field.height:
        width = to_mm(field.width.value, field.width.unit)
        height = to_mm(field.height.value, field.height.unit)
        unit = field.width.unit or field.height.unit or ""
        if width is not None and height is not None:
            return f"{_fmt_number(width)} × {_fmt_number(height)} {unit}".strip()
    if field.raw_text:
        return normalize_space(field.raw_text)
    return None


def _dimensions_offer_display(
    field: DimensionsField, width_mm: float | None, height_mm: float | None
) -> str | None:
    if width_mm is not None and height_mm is not None:
        return f"{_fmt_number(width_mm)} × {_fmt_number(height_mm)} mm"
    if field.raw_text:
        return normalize_space(field.raw_text)
    return None


def _thickness_populated(field: ThicknessField | None) -> bool:
    return bool(field and field.value is not None)


def _thickness_to_mm(field: ThicknessField | None) -> float | None:
    if not field:
        return None
    return to_mm(field.value, field.unit)


def _thickness_display(field: ThicknessField | None) -> str | None:
    if not field or field.value is None:
        return None
    value = _length_display(field.value, field.unit)
    return f"{value} ({field.kind.value})"


def compare_wall_thickness(
    spec: ThicknessField | None, offer: ThicknessField | None
) -> CriterionResult:
    evidence_spec = _evidence(spec.page if spec else None, spec.excerpt if spec else None)
    evidence_offer = _evidence(
        offer.page if offer else None, offer.excerpt if offer else None
    )

    if not _thickness_populated(spec):
        return CriterionResult(
            criterion="wall_thickness",
            status=Status.NOT_SPECIFIED,
            headline="No wall thickness stated in the specification",
            spec_evidence=evidence_spec,
            rule_explanation=(
                "The specification does not state a wall thickness, so this "
                "criterion was not compared."
            ),
        )

    spec_mm = _thickness_to_mm(spec)
    offer_mm = _thickness_to_mm(offer)
    spec_display = _thickness_display(spec)
    offer_display = _thickness_display(offer)

    if spec_mm is None:
        return CriterionResult(
            criterion="wall_thickness",
            status=Status.UNVERIFIED,
            headline="Specified wall thickness uses an unsupported unit",
            spec_display=spec_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The specified thickness could not be converted with a tested rule, "
                "so no comparison was made."
            ),
        )

    if offer_mm is None:
        return CriterionResult(
            criterion="wall_thickness",
            status=Status.UNVERIFIED,
            headline="No comparable wall thickness found in the catalogue",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The catalogue does not state a wall thickness in a unit this version "
                "can convert. Missing information is never treated as compliant."
            ),
        )

    spec_kind: ThicknessKind = spec.kind
    offer_kind: ThicknessKind = offer.kind
    check = CheckDetail(
        label="Wall thickness",
        outcome="unknown",
        spec_text=f"{_fmt_number(spec_mm)} mm ({spec_kind.value})",
        offer_text=f"{_fmt_number(offer_mm)} mm ({offer_kind.value})",
    )

    status: Status
    note: str

    if spec_kind is ThicknessKind.NOMINAL and offer_kind is ThicknessKind.NOMINAL:
        if abs(spec_mm - offer_mm) <= LENGTH_TOLERANCE_MM:
            check.outcome = "pass"
            status = Status.COMPLIANT
            note = "Nominal wall thickness matches the specification."
        else:
            check.outcome = "fail"
            status = Status.NON_COMPLIANT
            note = (
                f"Nominal wall thickness differs by "
                f"{_fmt_number(abs(spec_mm - offer_mm))} mm."
            )
    elif spec_kind is ThicknessKind.NOMINAL:
        # Catalogue states a minimum/maximum only; it cannot establish a nominal value.
        if offer_kind is ThicknessKind.MINIMUM and offer_mm < spec_mm - LENGTH_TOLERANCE_MM:
            check.outcome = "fail"
            status = Status.NON_COMPLIANT
            note = (
                "The catalogue guarantees a minimum wall thickness below the "
                "specified nominal value."
            )
        elif offer_kind is ThicknessKind.MAXIMUM and offer_mm < spec_mm - LENGTH_TOLERANCE_MM:
            check.outcome = "fail"
            status = Status.NON_COMPLIANT
            note = (
                "The catalogue maximum wall thickness is below the specified "
                "nominal value."
            )
        else:
            status = Status.UNVERIFIED
            note = (
                "The catalogue only states a limiting wall thickness, which is "
                "insufficient to confirm the specified nominal value."
            )
    elif spec_kind is ThicknessKind.MINIMUM:
        if offer_kind is ThicknessKind.MAXIMUM:
            if offer_mm < spec_mm - LENGTH_TOLERANCE_MM:
                check.outcome = "fail"
                status = Status.NON_COMPLIANT
                note = "The catalogue maximum is below the required minimum."
            else:
                status = Status.UNVERIFIED
                note = "A catalogue maximum cannot demonstrate a required minimum."
        elif offer_mm >= spec_mm - LENGTH_TOLERANCE_MM:
            check.outcome = "pass"
            status = Status.COMPLIANT
            note = "The offered wall thickness meets or exceeds the required minimum."
        else:
            check.outcome = "fail"
            status = Status.NON_COMPLIANT
            note = "The offered wall thickness is below the required minimum."
    else:  # spec requires a maximum
        if offer_kind is ThicknessKind.MINIMUM:
            if offer_mm > spec_mm + LENGTH_TOLERANCE_MM:
                check.outcome = "fail"
                status = Status.NON_COMPLIANT
                note = "The catalogue minimum already exceeds the allowed maximum."
            else:
                status = Status.UNVERIFIED
                note = "A catalogue minimum cannot demonstrate a required maximum."
        elif offer_mm <= spec_mm + LENGTH_TOLERANCE_MM:
            check.outcome = "pass"
            status = Status.COMPLIANT
            note = "The offered wall thickness is within the specified maximum."
        else:
            check.outcome = "fail"
            status = Status.NON_COMPLIANT
            note = "The offered wall thickness exceeds the specified maximum."

    return CriterionResult(
        criterion="wall_thickness",
        status=status,
        headline=_headline_for("wall thickness", status),
        spec_display=spec_display,
        offer_display=offer_display,
        spec_evidence=evidence_spec,
        offer_evidence=evidence_offer,
        checks=[check],
        rule_explanation=note,
    )


def _headline_for(subject: str, status: Status) -> str:
    mapping = {
        Status.COMPLIANT: f"Offered {subject} meets the requirement",
        Status.NON_COMPLIANT: f"Offered {subject} conflicts with the requirement",
        Status.UNVERIFIED: f"{subject.capitalize()} could not be verified",
        Status.NOT_SPECIFIED: f"No {subject} requirement stated",
    }
    return mapping[status]


# ---------------------------------------------------------------------------
# Material grade
# ---------------------------------------------------------------------------


def _grade_populated(field: MaterialGradeField | None) -> bool:
    return bool(field and normalize_grade(field.grade))


def compare_material_grade(
    spec: MaterialGradeField | None, offer: MaterialGradeField | None
) -> CriterionResult:
    evidence_spec = _evidence(spec.page if spec else None, spec.excerpt if spec else None)
    evidence_offer = _evidence(
        offer.page if offer else None, offer.excerpt if offer else None
    )

    if not _grade_populated(spec):
        return CriterionResult(
            criterion="material_grade",
            status=Status.NOT_SPECIFIED,
            headline="No material grade requirement stated",
            spec_display=None,
            spec_evidence=evidence_spec,
            rule_explanation=(
                "The specification does not state a material grade, so this "
                "criterion was not compared."
            ),
        )

    spec_grade = normalize_grade(spec.grade)
    spec_display = spec.grade.strip() if spec.grade else None

    if not _grade_populated(offer):
        return CriterionResult(
            criterion="material_grade",
            status=Status.UNVERIFIED,
            headline="No material grade found in the catalogue",
            spec_display=spec_display,
            offer_display=offer.grade.strip() if offer and offer.grade else None,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The catalogue does not state a recognizable material grade. "
                "Missing information is never treated as compliant."
            ),
        )

    offer_grade = normalize_grade(offer.grade)
    offer_display = offer.grade.strip() if offer.grade else None

    if spec_grade == offer_grade:
        return CriterionResult(
            criterion="material_grade",
            status=Status.COMPLIANT,
            headline="Material grade matches the specification",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            checks=[
                CheckDetail(
                    label="Grade designation",
                    outcome="pass",
                    spec_text=spec_grade,
                    offer_text=offer_grade,
                )
            ],
            rule_explanation=(
                f"Both documents state grade {spec_grade} (spacing and punctuation "
                "ignored when comparing designations)."
            ),
        )

    if spec.equivalence_allowed:
        return CriterionResult(
            criterion="material_grade",
            status=Status.UNVERIFIED,
            headline="Specification allows an equivalent grade",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            checks=[
                CheckDetail(
                    label="Grade designation",
                    outcome="unknown",
                    spec_text=spec_grade,
                    offer_text=offer_grade,
                    note="Equivalence is allowed by the specification; V1 cannot verify it.",
                )
            ],
            rule_explanation=(
                "The specification permits an equivalent grade. Deciding equivalence "
                "requires metallurgical judgement, so the criterion stays unverified."
            ),
        )

    return CriterionResult(
        criterion="material_grade",
        status=Status.NON_COMPLIANT,
        headline="Offered material grade differs from the specification",
        spec_display=spec_display,
        offer_display=offer_display,
        spec_evidence=evidence_spec,
        offer_evidence=evidence_offer,
        checks=[
            CheckDetail(
                label="Grade designation",
                outcome="fail",
                spec_text=spec_grade,
                offer_text=offer_grade,
            )
        ],
        rule_explanation=(
            f"The specification requires grade {spec_grade} and the catalogue offers "
            f"{offer_grade}, which is a different designation."
        ),
    )


# ---------------------------------------------------------------------------
# Standard
# ---------------------------------------------------------------------------


def _standard_populated(field: StandardField | None) -> bool:
    return bool(field and normalize_standard(field.designation))


def compare_standard(
    spec: StandardField | None, offer: StandardField | None
) -> CriterionResult:
    evidence_spec = _evidence(spec.page if spec else None, spec.excerpt if spec else None)
    evidence_offer = _evidence(
        offer.page if offer else None, offer.excerpt if offer else None
    )

    if not _standard_populated(spec):
        return CriterionResult(
            criterion="standard",
            status=Status.NOT_SPECIFIED,
            headline="No applicable standard stated",
            spec_evidence=evidence_spec,
            rule_explanation=(
                "The specification does not state an applicable standard, so this "
                "criterion was not compared."
            ),
        )

    spec_display = normalize_standard(spec.designation) or spec.designation

    if not _standard_populated(offer):
        return CriterionResult(
            criterion="standard",
            status=Status.UNVERIFIED,
            headline="No applicable standard found in the catalogue",
            spec_display=spec_display,
            offer_display=offer.designation if offer else None,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The catalogue does not state a standard designation that could be "
                "matched. Missing information is never treated as compliant."
            ),
        )

    offer_display = normalize_standard(offer.designation) or offer.designation
    compatible, note = standards_compatible(spec.designation, offer.designation)

    if compatible:
        same_display = spec_display == offer_display
        return CriterionResult(
            criterion="standard",
            status=Status.COMPLIANT,
            headline="Catalogue references the required standard",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            checks=[
                CheckDetail(
                    label="Standard designation",
                    outcome="pass",
                    spec_text=spec_display,
                    offer_text=offer_display,
                    note=None if same_display else "Part-level reference is consistent.",
                )
            ],
            rule_explanation=(
                "The catalogue references the same standard family and number as "
                "the specification."
            ),
        )

    return CriterionResult(
        criterion="standard",
        status=Status.NON_COMPLIANT,
        headline="Catalogue references a different standard",
        spec_display=spec_display,
        offer_display=offer_display,
        spec_evidence=evidence_spec,
        offer_evidence=evidence_offer,
        checks=[
            CheckDetail(
                label="Standard designation",
                outcome="fail",
                spec_text=spec_display,
                offer_text=offer_display,
            )
        ],
        rule_explanation=note,
    )


# ---------------------------------------------------------------------------
# Galvanizing
# ---------------------------------------------------------------------------

_STANDARD_PROCESS_HINTS: tuple[tuple[str, str], ...] = (
    ("1461", "hot_dip"),
    ("10646", "hot_dip"),
    ("10346", "pre_galvanized"),
    ("14713", "electroplated"),
)

_PROCESS_LABELS = {
    "hot_dip": "hot-dip galvanized",
    "pre_galvanized": "pre-galvanized (zinc-coated strip)",
    "electroplated": "electroplated zinc",
    "bare": "bare / untreated",
    "unknown": "process not stated",
}

_PROCESS_CONFLICTS = {
    frozenset({"hot_dip", "pre_galvanized"}),
    frozenset({"hot_dip", "electroplated"}),
    frozenset({"hot_dip", "bare"}),
    frozenset({"pre_galvanized", "electroplated"}),
    frozenset({"pre_galvanized", "bare"}),
    frozenset({"electroplated", "bare"}),
}


def infer_process(process: str | None, standard: str | None) -> str | None:
    """Resolve a coating process, falling back to a standard-based rule."""

    if process and process != "unknown":
        return process
    normalized = normalize_standard(standard)
    if not normalized:
        return None
    for token, inferred in _STANDARD_PROCESS_HINTS:
        if token in normalized:
            return inferred
    return None


def _galvanizing_populated(field: GalvanizingField | None) -> bool:
    if not field:
        return False
    return bool(
        field.process
        or field.standard
        or field.coating_mass_value is not None
        or field.coating_thickness_value is not None
        or (field.raw_text and field.raw_text.strip())
    )


def compare_galvanizing(
    spec: GalvanizingField | None, offer: GalvanizingField | None
) -> CriterionResult:
    evidence_spec = _evidence(
        spec.page if spec else None,
        (spec.excerpt if spec else None) or (spec.raw_text if spec else None),
    )
    evidence_offer = _evidence(
        offer.page if offer else None,
        (offer.excerpt if offer else None) or (offer.raw_text if offer else None),
    )

    if not _galvanizing_populated(spec):
        return CriterionResult(
            criterion="galvanizing",
            status=Status.NOT_SPECIFIED,
            headline="No galvanizing or coating requirement stated",
            spec_evidence=evidence_spec,
            rule_explanation=(
                "The specification does not state a galvanizing or coating "
                "requirement, so this criterion was not compared."
            ),
        )

    spec_display = _galvanizing_display(spec)
    offer_display = _galvanizing_display(offer)

    if not _galvanizing_populated(offer):
        return CriterionResult(
            criterion="galvanizing",
            status=Status.UNVERIFIED,
            headline="No galvanizing information found in the catalogue",
            spec_display=spec_display,
            offer_display=None,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The catalogue does not state a coating process, standard or coating "
                "mass. Missing information is never treated as compliant."
            ),
        )

    checks: list[CheckDetail] = []

    # 1. Process
    spec_process = infer_process(spec.process.value if spec.process else None, spec.standard)
    offer_process = infer_process(
        offer.process.value if offer.process else None, offer.standard
    )
    if spec_process:
        if not offer_process:
            checks.append(
                CheckDetail(
                    label="Coating process",
                    outcome="unknown",
                    spec_text=_PROCESS_LABELS.get(spec_process, spec_process),
                    offer_text="not stated",
                    note="Required process evidence is missing from the catalogue.",
                )
            )
        elif spec_process == offer_process:
            checks.append(
                CheckDetail(
                    label="Coating process",
                    outcome="pass",
                    spec_text=_PROCESS_LABELS.get(spec_process, spec_process),
                    offer_text=_PROCESS_LABELS.get(offer_process, offer_process),
                )
            )
        elif frozenset({spec_process, offer_process}) in _PROCESS_CONFLICTS:
            checks.append(
                CheckDetail(
                    label="Coating process",
                    outcome="fail",
                    spec_text=_PROCESS_LABELS.get(spec_process, spec_process),
                    offer_text=_PROCESS_LABELS.get(offer_process, offer_process),
                    note="The offered coating process is a different process.",
                )
            )
        else:
            checks.append(
                CheckDetail(
                    label="Coating process",
                    outcome="unknown",
                    spec_text=_PROCESS_LABELS.get(spec_process, spec_process),
                    offer_text=_PROCESS_LABELS.get(offer_process, offer_process),
                )
            )

    # 2. Galvanizing standard
    spec_std = normalize_standard(spec.standard)
    offer_std = normalize_standard(offer.standard)
    if spec_std:
        if not offer_std:
            checks.append(
                CheckDetail(
                    label="Coating standard",
                    outcome="unknown",
                    spec_text=spec_std,
                    offer_text="not stated",
                    note="The catalogue does not reference a coating standard.",
                )
            )
        else:
            compatible, note = standards_compatible(spec.standard, offer.standard)
            checks.append(
                CheckDetail(
                    label="Coating standard",
                    outcome="pass" if compatible else "fail",
                    spec_text=spec_std,
                    offer_text=offer_std,
                    note=None if compatible else note,
                )
            )

    # 3. Coating mass
    spec_mass = to_g_per_m2(spec.coating_mass_value, spec.coating_mass_unit)
    offer_mass = to_g_per_m2(offer.coating_mass_value, offer.coating_mass_unit)
    if spec.coating_mass_value is not None:
        if spec_mass is None:
            checks.append(
                CheckDetail(
                    label="Coating mass",
                    outcome="unknown",
                    spec_text=f"{spec.coating_mass_value} {spec.coating_mass_unit or ''}".strip(),
                    offer_text=None,
                    note="Specified coating mass unit is not supported by V1 conversions.",
                )
            )
        elif offer_mass is None:
            checks.append(
                CheckDetail(
                    label="Coating mass",
                    outcome="unknown",
                    spec_text=f"≥ {_fmt_number(spec_mass)} g/m²",
                    offer_text="not stated",
                    note="The catalogue does not state a comparable coating mass.",
                )
            )
        elif offer_mass + COATING_TOLERANCE >= spec_mass:
            checks.append(
                CheckDetail(
                    label="Coating mass",
                    outcome="pass",
                    spec_text=f"≥ {_fmt_number(spec_mass)} g/m²",
                    offer_text=f"{_fmt_number(offer_mass)} g/m²",
                )
            )
        else:
            checks.append(
                CheckDetail(
                    label="Coating mass",
                    outcome="fail",
                    spec_text=f"≥ {_fmt_number(spec_mass)} g/m²",
                    offer_text=f"{_fmt_number(offer_mass)} g/m²",
                    note="Offered coating mass is below the specified minimum.",
                )
            )

    # 4. Coating thickness
    spec_um = to_um(spec.coating_thickness_value, spec.coating_thickness_unit)
    offer_um = to_um(offer.coating_thickness_value, offer.coating_thickness_unit)
    if spec.coating_thickness_value is not None:
        if spec_um is None:
            checks.append(
                CheckDetail(
                    label="Coating thickness",
                    outcome="unknown",
                    spec_text=f"{spec.coating_thickness_value} {spec.coating_thickness_unit or ''}".strip(),
                    note="Specified coating thickness unit is not supported by V1 conversions.",
                )
            )
        elif offer_um is None:
            checks.append(
                CheckDetail(
                    label="Coating thickness",
                    outcome="unknown",
                    spec_text=f"≥ {_fmt_number(spec_um)} µm",
                    offer_text="not stated",
                    note="The catalogue does not state a comparable coating thickness.",
                )
            )
        elif offer_um + COATING_TOLERANCE >= spec_um:
            checks.append(
                CheckDetail(
                    label="Coating thickness",
                    outcome="pass",
                    spec_text=f"≥ {_fmt_number(spec_um)} µm",
                    offer_text=f"{_fmt_number(offer_um)} µm",
                )
            )
        else:
            checks.append(
                CheckDetail(
                    label="Coating thickness",
                    outcome="fail",
                    spec_text=f"≥ {_fmt_number(spec_um)} µm",
                    offer_text=f"{_fmt_number(offer_um)} µm",
                    note="Offered coating thickness is below the specified minimum.",
                )
            )

    if not checks:
        return CriterionResult(
            criterion="galvanizing",
            status=Status.UNVERIFIED,
            headline="Galvanizing requirement could not be interpreted",
            spec_display=spec_display,
            offer_display=offer_display,
            spec_evidence=evidence_spec,
            offer_evidence=evidence_offer,
            rule_explanation=(
                "The specification mentions a coating requirement, but no process, "
                "standard or coating quantity could be extracted to compare."
            ),
        )

    failures = [c for c in checks if c.outcome == "fail"]
    unknowns = [c for c in checks if c.outcome == "unknown"]

    if failures:
        status = Status.NON_COMPLIANT
        headline = "Offered coating conflicts with the requirement"
        explanation = (
            "Conflicting coating evidence: "
            + "; ".join(
                f"{c.label.lower()} ({c.spec_text} vs {c.offer_text})" for c in failures
            )
            + "."
        )
    elif unknowns:
        status = Status.UNVERIFIED
        headline = "Coating requirement only partially verified"
        explanation = (
            "Some coating evidence could not be verified: "
            + "; ".join(c.label.lower() for c in unknowns)
            + ". Missing information is never treated as compliant."
        )
    else:
        status = Status.COMPLIANT
        headline = "Offered coating meets the stated requirement"
        explanation = "All specified coating attributes match the catalogue evidence."

    return CriterionResult(
        criterion="galvanizing",
        status=status,
        headline=headline,
        spec_display=spec_display,
        offer_display=offer_display,
        spec_evidence=evidence_spec,
        offer_evidence=evidence_offer,
        checks=checks,
        rule_explanation=explanation,
    )


def _galvanizing_display(field: GalvanizingField | None) -> str | None:
    if not field:
        return None
    parts: list[str] = []
    if field.raw_text and len(normalize_space(field.raw_text)) <= 90:
        return normalize_space(field.raw_text)
    process = infer_process(field.process.value if field.process else None, field.standard)
    if process:
        parts.append(_PROCESS_LABELS.get(process, process))
    standard = normalize_standard(field.standard)
    if standard:
        parts.append(standard)
    if field.coating_mass_value is not None:
        parts.append(
            f"{_fmt_number(field.coating_mass_value)} {field.coating_mass_unit or ''}".strip()
        )
    if field.coating_thickness_value is not None:
        parts.append(
            f"{_fmt_number(field.coating_thickness_value)} {field.coating_thickness_unit or ''}".strip()
        )
    if parts:
        return " · ".join(parts)
    if field.raw_text:
        # Long unstructured prose: keep the display compact.
        text = normalize_space(field.raw_text)
        return text[:117].rstrip() + "…" if len(text) > 120 else text
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compare_document(
    spec: ExtractedRequirements, offer: ExtractedRequirements
) -> list[CriterionResult]:
    """Evaluate the five V1 criteria for one manufacturer document."""

    return [
        compare_dimensions(spec.dimensions, offer.dimensions),
        compare_wall_thickness(spec.wall_thickness, offer.wall_thickness),
        compare_material_grade(spec.material_grade, offer.material_grade),
        compare_galvanizing(spec.galvanizing, offer.galvanizing),
        compare_standard(spec.standard, offer.standard),
    ]


def count_statuses(results: list[CriterionResult]) -> StatusCounts:
    counts = StatusCounts()
    for result in results:
        counts.add(result.status)
    return counts


def summarize_counts(results: list[CriterionResult]) -> str:
    """Deterministic one-line summary (also the AI fallback)."""

    counts = count_statuses(results)
    total = counts.compared_total
    if total == 0:
        return "The specification did not state any of the five comparison criteria."
    return (
        f"{counts.compliant} of {total} compared criteria compliant, "
        f"{counts.non_compliant} non-compliant, {counts.unverified} unverified"
        + (f", {counts.not_specified} not stated in the specification" if counts.not_specified else "")
        + "."
    )
