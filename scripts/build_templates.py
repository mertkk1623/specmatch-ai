"""Build the blank input templates and the field guide.

SpecMatch AI does **not** read CSV or Excel. It reads PDFs and extracts five
technical fields with a language model, so a "column template" would be
misleading. The templates here are therefore blank PDF datasheets that carry
exactly the five labelled fields the extractor looks for, in the place it looks
for them.

The field guide is a CSV that documents, for each field: the label the extractor
matches, the value type, the accepted units, and the deterministic validation
rule that decides the status. It is documentation, not an input file.

Run:  python scripts/build_templates.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sample_docs" / "templates"

INK = colors.HexColor("#1B2430")
MUTED = colors.HexColor("#5A6672")
RULE = colors.HexColor("#D6DCE2")
ACCENT = colors.HexColor("#1F4E79")
FIELD_BG = colors.HexColor("#F7F9FB")
HINT_INK = colors.HexColor("#8A94A0")

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
for regular, bold in (
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
):
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("TplSans", str(regular)))
        pdfmetrics.registerFont(TTFont("TplSans-Bold", str(bold)))
        FONT, FONT_BOLD = "TplSans", "TplSans-Bold"
        break


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle(
            "brand", parent=base["Normal"], fontName=FONT_BOLD, fontSize=9,
            textColor=MUTED, leading=12, spaceAfter=2,
        ),
        "title": ParagraphStyle(
            "title", parent=base["Normal"], fontName=FONT_BOLD, fontSize=17,
            textColor=INK, leading=21, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"], fontName=FONT, fontSize=9.5,
            textColor=MUTED, leading=14, spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Normal"], fontName=FONT_BOLD, fontSize=10.5,
            textColor=ACCENT, leading=14, spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName=FONT, fontSize=9,
            textColor=INK, leading=13.5, spaceAfter=5,
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"], fontName=FONT, fontSize=8,
            textColor=MUTED, leading=11.5,
        ),
        "label": ParagraphStyle(
            "label", parent=base["Normal"], fontName=FONT_BOLD, fontSize=9,
            textColor=INK, leading=12,
        ),
        "hint": ParagraphStyle(
            "hint", parent=base["Normal"], fontName=FONT, fontSize=8,
            textColor=HINT_INK, leading=11,
        ),
    }


class TemplateDoc(BaseDocTemplate):
    def __init__(self, path: Path, label: str, doc_id: str):
        super().__init__(
            str(path), pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=18 * mm,
            title=label, author="SpecMatch AI", subject="Blank input template",
        )
        self.label = label
        self.doc_id = doc_id
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=self._decorate)])

    def _decorate(self, canvas, doc) -> None:
        canvas.saveState()
        width, _ = A4
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(20 * mm, 14 * mm, width - 20 * mm, 14 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 7.4)
        canvas.drawString(20 * mm, 10 * mm, f"{self.label}  |  {self.doc_id}")
        canvas.drawRightString(width - 20 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()


def field_block(label: str, hint: str, st: dict, value: str = "") -> Table:
    """One fillable field: bold label, hint, and a writable value cell."""

    value_para = (
        Paragraph(value, st["body"])
        if value
        else Paragraph("&nbsp;", st["body"])
    )
    data = [[Paragraph(label, st["label"]), value_para],
            ["", Paragraph(hint, st["hint"])]]
    table = Table(data, colWidths=[52 * mm, 118 * mm], hAlign="LEFT", rowHeights=[11 * mm, 6 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (1, 0), (1, 0), FIELD_BG),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("BOX", (1, 0), (1, 0), 0.6, RULE),
                ("LINEBELOW", (0, 0), (0, 0), 0.4, RULE),
                ("SPAN", (1, 0), (1, 1)),
            ]
        )
    )
    return table


def build_specification_template(path: Path) -> None:
    st = styles()
    doc = TemplateDoc(path, "Blank template - project specification", "TPL-SPEC")
    story = [
        Paragraph("PROJECT SPECIFICATION - BLANK TEMPLATE", st["brand"]),
        Paragraph("Technical specification input", st["title"]),
        Paragraph(
            "Fill in the five fields below and export to PDF. SpecMatch AI reads the "
            "labels on the left to find each value. Keep the labels unchanged; write "
            "your requirement in the right-hand box. Delete any field the project does "
            "not specify - it will be reported as not specified rather than assumed.",
            st["subtitle"],
        ),
        Paragraph("Required fields", st["h2"]),
        field_block(
            "Section profile",
            'Outside dimensions, e.g. "60 x 60 mm" or "100 x 100 mm".',
            st,
        ),
        Spacer(1, 3),
        field_block(
            "Wall thickness",
            'State the kind: "3.0 mm nominal", "3.0 mm minimum" or "4.0 mm maximum".',
            st,
        ),
        Spacer(1, 3),
        field_block(
            "Steel grade",
            'EN designation, e.g. "S235JRH". Add "or equivalent" only if equivalence is allowed.',
            st,
        ),
        Spacer(1, 3),
        field_block(
            "Galvanizing",
            'Process, standard and coating, e.g. "Hot-dip galvanized to EN ISO 1461, minimum 505 g/m2".',
            st,
        ),
        Spacer(1, 3),
        field_block(
            "Applicable standard",
            'Product standard, e.g. "EN 10219".',
            st,
        ),
        Spacer(1, 12),
        Paragraph("How this template is read", st["h2"]),
        Paragraph(
            "Every value is extracted with the page it appears on and a verbatim "
            "excerpt. A value that cannot be converted with a tested unit rule is "
            "reported as unverified, never assumed. Scanned or image-only PDFs are not "
            "supported in V1 - export a text-based PDF.",
            st["note"],
        ),
    ]
    doc.build(story)


def build_manufacturer_template(path: Path) -> None:
    st = styles()
    doc = TemplateDoc(path, "Blank template - manufacturer datasheet", "TPL-MFR")
    story = [
        Paragraph("MANUFACTURER DATASHEET - BLANK TEMPLATE", st["brand"]),
        Paragraph("Manufacturer catalogue or datasheet input", st["title"]),
        Paragraph(
            "Fill in the five fields below and export to PDF. Write the values exactly "
            "as your catalogue states them, including the unit. Do not round or convert "
            "anything - SpecMatch AI keeps the printed value as evidence and applies "
            "tested conversions itself.",
            st["subtitle"],
        ),
        Paragraph("Product fields", st["h2"]),
        field_block("Outside dimensions", 'e.g. "60 x 60 mm".', st),
        Spacer(1, 3),
        field_block(
            "Wall thickness",
            'e.g. "3.0 mm nominal" or "3.2 mm minimum". State the kind if your catalogue does.',
            st,
        ),
        Spacer(1, 3),
        field_block("Steel grade", 'e.g. "S235JRH" or "S 235 JRH".', st),
        Spacer(1, 3),
        field_block(
            "Surface finish",
            'Process, standard and coating mass, e.g. "Hot-dip galvanized, EN ISO 1461, 620 g/m2".',
            st,
        ),
        Spacer(1, 3),
        field_block("Manufacturing standard", 'e.g. "EN 10219-1".', st),
        Spacer(1, 12),
        Paragraph("What happens if a field is empty", st["h2"]),
        Paragraph(
            "An empty field is treated as missing information. The matching criterion "
            "is reported as unverified - never as compliant - because missing "
            "information cannot demonstrate that a requirement is met.",
            st["note"],
        ),
    ]
    doc.build(story)


FIELD_GUIDE_ROWS = [
    {
        "criterion_key": "dimensions",
        "spec_label": "Section profile",
        "offer_label": "Outside dimensions / Dimensions",
        "value_type": "number x number",
        "accepted_units": "mm, cm, m, in",
        "example_value": "60 x 60 mm",
        "status_rule": "Both width and height must be present on both sides. Equal within 0.1 mm -> compliant; a clear difference -> non-compliant.",
    },
    {
        "criterion_key": "wall_thickness",
        "spec_label": "Wall thickness",
        "offer_label": "Wall thickness",
        "value_type": "number + kind (nominal/minimum/maximum)",
        "accepted_units": "mm, cm, m, in",
        "example_value": "3.0 mm minimum",
        "status_rule": "nominal: equal within 0.1 mm. minimum: offer >= minimum. maximum: offer <= maximum. Missing value -> unverified.",
    },
    {
        "criterion_key": "material_grade",
        "spec_label": "Steel grade",
        "offer_label": "Steel grade / Grade",
        "value_type": "text designation",
        "accepted_units": "n/a",
        "example_value": "S235JRH",
        "status_rule": "Normalized equality (case, spaces and hyphens ignored). Different grade -> non-compliant. 'Or equivalent' in the spec -> unverified.",
    },
    {
        "criterion_key": "galvanizing",
        "spec_label": "Galvanizing",
        "offer_label": "Surface finish / Coating",
        "value_type": "process + standard + coating mass or thickness",
        "accepted_units": "g/m2, mg/cm2, um, mm",
        "example_value": "Hot-dip galvanized to EN ISO 1461, 505 g/m2",
        "status_rule": "Process, standard and coating mass are checked separately. Conflict -> non-compliant. Missing or different standard -> unverified.",
    },
    {
        "criterion_key": "standard",
        "spec_label": "Applicable standard",
        "offer_label": "Manufacturing standard / Standard",
        "value_type": "text designation",
        "accepted_units": "n/a",
        "example_value": "EN 10219",
        "status_rule": "Normalized containment, so EN 10219 matches EN 10219-1. Clearly different product standard -> non-compliant.",
    },
]


def build_field_guide(path: Path) -> None:
    """A CSV field guide documenting labels, types, units and rules.

    This is documentation of what the extractor reads. It is not an input file:
    the application accepts PDFs only.
    """

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELD_GUIDE_ROWS[0].keys()))
        writer.writeheader()
        writer.writerows(FIELD_GUIDE_ROWS)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    build_specification_template(OUT / "template_specification.pdf")
    build_manufacturer_template(OUT / "template_manufacturer.pdf")
    build_field_guide(OUT / "field_guide.csv")

    for name in ("template_specification.pdf", "template_manufacturer.pdf", "field_guide.csv"):
        path = OUT / name
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

