"""Pydantic schemas for AI output, document metadata, and comparison results.

The model is allowed to return *extraction only*: values as printed, units as
printed, a page number, and a short verbatim excerpt. It never returns a
compliance status. All statuses are produced by :mod:`src.compliance`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

CriterionKey = Literal[
    "dimensions",
    "wall_thickness",
    "material_grade",
    "galvanizing",
    "standard",
]

CRITERION_ORDER: tuple[str, ...] = (
    "dimensions",
    "wall_thickness",
    "material_grade",
    "galvanizing",
    "standard",
)


class Status(str, Enum):
    """Compliance verdicts produced only by the deterministic engine."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNVERIFIED = "unverified"
    NOT_SPECIFIED = "not_specified"


class DocumentKind(str, Enum):
    SPECIFICATION = "specification"
    MANUFACTURER = "manufacturer"


class ThicknessKind(str, Enum):
    NOMINAL = "nominal"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"


class GalvanizingProcess(str, Enum):
    HOT_DIP = "hot_dip"
    PRE_GALVANIZED = "pre_galvanized"
    ELECTROPLATED = "electroplated"
    BARE = "bare"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


class EvidenceRef(BaseModel):
    """A page reference plus a verbatim excerpt from that page."""

    model_config = ConfigDict(extra="forbid")

    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)

    @property
    def is_present(self) -> bool:
        return self.page is not None and bool(self.excerpt)

    def short(self, limit: int = 220) -> str:
        text = (self.excerpt or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"


class ValidationIssue(BaseModel):
    document: str
    field: str | None = None
    severity: Literal["warning", "error"] = "warning"
    message: str


class ParsedPage(BaseModel):
    number: int = Field(ge=1)
    text: str


class DocumentMeta(BaseModel):
    """Information about one parsed input document."""

    filename: str
    kind: DocumentKind
    page_count: int = Field(ge=0)
    parser: str
    tables_found: int = 0
    char_count: int = 0
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Raw extraction fields (model output, values as printed)
# ---------------------------------------------------------------------------


class Quantity(BaseModel):
    """A single measured value exactly as printed."""

    model_config = ConfigDict(extra="forbid")

    value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_number(cls, raw: object) -> object:
        if isinstance(raw, str):
            cleaned = raw.strip().replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return raw


class DimensionsField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    width: Quantity | None = None
    height: Quantity | None = None
    raw_text: str | None = Field(default=None, max_length=300)
    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)


class ThicknessField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: float | None = None
    unit: str | None = Field(default=None, max_length=24)
    kind: ThicknessKind = ThicknessKind.NOMINAL
    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_number(cls, raw: object) -> object:
        if isinstance(raw, str):
            cleaned = raw.strip().replace(",", ".")
            try:
                return float(cleaned)
            except ValueError:
                return None
        return raw


class MaterialGradeField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grade: str | None = Field(default=None, max_length=80)
    equivalence_allowed: bool = False
    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)


class GalvanizingField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process: GalvanizingProcess | None = None
    standard: str | None = Field(default=None, max_length=80)
    coating_mass_value: float | None = None
    coating_mass_unit: str | None = Field(default=None, max_length=24)
    coating_thickness_value: float | None = None
    coating_thickness_unit: str | None = Field(default=None, max_length=24)
    raw_text: str | None = Field(default=None, max_length=300)
    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)


class StandardField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designation: str | None = Field(default=None, max_length=120)
    page: int | None = Field(default=None, ge=1, le=2000)
    excerpt: str | None = Field(default=None, max_length=600)


class ExtractedRequirements(BaseModel):
    """Structured extraction for one document (specification or catalogue)."""

    model_config = ConfigDict(extra="forbid")

    document_kind: DocumentKind = DocumentKind.SPECIFICATION
    product_family_statement: str | None = Field(default=None, max_length=300)
    dimensions: DimensionsField | None = None
    wall_thickness: ThicknessField | None = None
    material_grade: MaterialGradeField | None = None
    galvanizing: GalvanizingField | None = None
    standard: StandardField | None = None
    notes: list[str] = Field(default_factory=list)


class ExtractionEnvelope(BaseModel):
    """Top-level object expected from the model."""

    model_config = ConfigDict(extra="forbid")

    document_kind: DocumentKind = DocumentKind.SPECIFICATION
    product_family_statement: str | None = Field(default=None, max_length=300)
    dimensions: DimensionsField | None = None
    wall_thickness: ThicknessField | None = None
    material_grade: MaterialGradeField | None = None
    galvanizing: GalvanizingField | None = None
    standard: StandardField | None = None
    notes: list[str] = Field(default_factory=list)

    def to_requirements(self, kind: DocumentKind) -> ExtractedRequirements:
        return ExtractedRequirements(
            document_kind=kind,
            product_family_statement=self.product_family_statement,
            dimensions=self.dimensions,
            wall_thickness=self.wall_thickness,
            material_grade=self.material_grade,
            galvanizing=self.galvanizing,
            standard=self.standard,
            notes=list(self.notes),
        )


# ---------------------------------------------------------------------------
# Comparison results
# ---------------------------------------------------------------------------


class CheckDetail(BaseModel):
    """One atomic rule evaluation, kept for auditability."""

    label: str
    outcome: str  # "pass" | "fail" | "unknown"
    spec_text: str | None = None
    offer_text: str | None = None
    note: str | None = None


class CriterionResult(BaseModel):
    criterion: str
    status: Status
    headline: str
    spec_display: str | None = None
    offer_display: str | None = None
    spec_evidence: EvidenceRef | None = None
    offer_evidence: EvidenceRef | None = None
    checks: list[CheckDetail] = Field(default_factory=list)
    rule_explanation: str = ""
    ai_explanation: str | None = None
    explanation_source: Literal["ai", "rule"] = "rule"

    @property
    def explanation(self) -> str:
        return self.ai_explanation or self.rule_explanation


class StatusCounts(BaseModel):
    compliant: int = 0
    non_compliant: int = 0
    unverified: int = 0
    not_specified: int = 0

    @property
    def compared_total(self) -> int:
        return self.compliant + self.non_compliant + self.unverified

    @property
    def evaluated_total(self) -> int:
        return self.compared_total + self.not_specified

    def add(self, status: Status) -> None:
        setattr(self, status.value, getattr(self, status.value) + 1)


class ManufacturerAnalysis(BaseModel):
    name: str
    document_name: str
    document_meta: DocumentMeta
    criteria: list[CriterionResult]
    counts: StatusCounts
    warnings: list[str] = Field(default_factory=list)

    def criterion(self, key: str) -> CriterionResult | None:
        for item in self.criteria:
            if item.criterion == key:
                return item
        return None


class SpecAnalysis(BaseModel):
    document_name: str
    document_meta: DocumentMeta
    requirements: ExtractedRequirements
    study_description: str | None = None
    evidence: dict[str, EvidenceRef] = Field(default_factory=dict)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Everything the results page and the report need."""

    analysis_id: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    spec: SpecAnalysis
    manufacturers: list[ManufacturerAnalysis]
    summary: str = ""
    summary_source: Literal["ai", "rule"] = "rule"
    model: str = ""
    parser_notes: list[str] = Field(default_factory=list)
    validation_issues: list[ValidationIssue] = Field(default_factory=list)
    duration_seconds: float | None = None
    demo: bool = False

    def manufacturer(self, name: str) -> ManufacturerAnalysis | None:
        for item in self.manufacturers:
            if item.name == name:
                return item
        return None

    def all_counts(self) -> StatusCounts:
        total = StatusCounts()
        for manufacturer in self.manufacturers:
            total.compliant += manufacturer.counts.compliant
            total.non_compliant += manufacturer.counts.non_compliant
            total.unverified += manufacturer.counts.unverified
            total.not_specified += manufacturer.counts.not_specified
        return total
