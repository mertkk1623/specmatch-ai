"""Build the three synthetic demo PDFs.

Every document carries an explicit "SYNTHETIC DEMO DOCUMENT" banner so demo
data can never be mistaken for a real project specification or a real
manufacturer datasheet. The content is intentionally simple and realistic:
one specification plus two catalogue offers that exercise compliant,
non-compliant and unverified outcomes.

Run:  python scripts/build_demo_pdfs.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
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
OUT = ROOT / "sample_docs"

INK = colors.HexColor("#1B2430")
MUTED = colors.HexColor("#5A6672")
RULE = colors.HexColor("#D6DCE2")
DEMO_BG = colors.HexColor("#FFF4E5")
DEMO_INK = colors.HexColor("#8A5A00")
ACCENT = colors.HexColor("#1F4E79")
ZEBRA = colors.HexColor("#F5F7F9")

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
for candidate in (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/segoeui.ttf")):
    if candidate.exists():
        pdfmetrics.registerFont(TTFont("DocSans", str(candidate)))
        bold = candidate.with_name(candidate.name.replace("arial", "arialbd").replace("segoeui", "segoeuib"))
        if not bold.exists():
            bold = Path("C:/Windows/Fonts/arialbd.ttf")
        if bold.exists():
            pdfmetrics.registerFont(TTFont("DocSans-Bold", str(bold)))
            FONT, FONT_BOLD = "DocSans", "DocSans-Bold"
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
            "subtitle", parent=base["Normal"], fontName=FONT, fontSize=10,
            textColor=MUTED, leading=14, spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Normal"], fontName=FONT_BOLD, fontSize=10.5,
            textColor=ACCENT, leading=14, spaceBefore=10, spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"], fontName=FONT, fontSize=9,
            textColor=INK, leading=13.5, alignment=TA_LEFT, spaceAfter=5,
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"], fontName=FONT, fontSize=8,
            textColor=MUTED, leading=11.5,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontName=FONT, fontSize=8.6,
            textColor=INK, leading=11.5,
        ),
        "celllabel": ParagraphStyle(
            "celllabel", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.6,
            textColor=INK, leading=11.5,
        ),
        "demo": ParagraphStyle(
            "demo", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8,
            textColor=DEMO_INK, leading=11,
        ),
    }


class DemoDoc(BaseDocTemplate):
    def __init__(self, path: Path, label: str, demo_id: str, **kwargs):
        super().__init__(str(path), pagesize=A4, leftMargin=20 * mm,
                         rightMargin=20 * mm, topMargin=16 * mm, bottomMargin=18 * mm,
                         title=label, author="SpecMatch AI demo dataset",
                         subject="Synthetic demonstration document", **kwargs)
        self.label = label
        self.demo_id = demo_id
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=self._decorate)])

    def _decorate(self, canvas, doc):
        canvas.saveState()
        width, height = A4
        # Demo banner
        banner_h = 11 * mm
        canvas.setFillColor(DEMO_BG)
        canvas.rect(0, height - banner_h, width, banner_h, stroke=0, fill=1)
        canvas.setFillColor(DEMO_INK)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawString(20 * mm, height - 7.4 * mm,
                          "SYNTHETIC DEMO DOCUMENT  |  Demonstration data only  |  Not a real specification or manufacturer datasheet")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(20 * mm, height - banner_h, width - 20 * mm, height - banner_h)
        # Footer
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 7.6)
        canvas.drawString(20 * mm, 11 * mm, f"{self.label}  |  {self.demo_id}")
        canvas.drawRightString(width - 20 * mm, 11 * mm, f"Page {doc.page}")
        canvas.restoreState()


def info_table(rows: list[tuple[str, str]], st: dict, widths=(42 * mm, 128 * mm)) -> Table:
    data = [[Paragraph(k, st["celllabel"]), Paragraph(v, st["cell"])] for k, v in rows]
    table = Table(data, colWidths=list(widths), hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
            ]
        )
    )
    return table


def grid_table(header: list[str], rows: list[list[str]], st: dict, widths: list[float]) -> Table:
    data = [[Paragraph(h, st["celllabel"]) for h in header]]
    for row in rows:
        data.append([Paragraph(str(cell), st["cell"]) for cell in row])
    table = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF1F5")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, RULE),
    ]
    for index in range(1, len(data)):
        if index % 2 == 0:
            style.append(("BACKGROUND", (0, index), (-1, index), ZEBRA))
    table.setStyle(TableStyle(style))
    return table


# ---------------------------------------------------------------------------
# 1. Project specification
# ---------------------------------------------------------------------------


def build_specification(path: Path) -> None:
    st = styles()
    doc = DemoDoc(path, "Section 05 12 23 - Galvanized square hollow sections", "DEMO-SPEC-01")
    story = [
        Paragraph("ATLAS CONSTRUCTION - TECHNICAL OFFICE", st["brand"]),
        Paragraph("Section 05 12 23 - Galvanized square hollow sections", st["title"]),
        Paragraph(
            "Project: Atlas Distribution Centre, Phase 1 - structural steel package. "
            "Document status: Issued for tender. Revision B.",
            st["subtitle"],
        ),
        Paragraph("1. Scope", st["h2"]),
        Paragraph(
            "This section covers cold-formed square steel hollow sections used for roof "
            "purlin bracing, handrail framing and secondary structural members. Sections "
            "are supplied in 6 m lengths unless noted otherwise in the schedule.",
            st["body"],
        ),
        Paragraph("2. Product requirements", st["h2"]),
        grid_table(
            ["Requirement", "Specified value"],
            [
                ["Section profile", "Square hollow section, 40 x 40 mm"],
                ["Wall thickness", "3.0 mm nominal"],
                ["Steel grade", "S235JRH"],
                ["Galvanizing", "Hot-dip galvanized to EN ISO 1461, minimum coating mass 505 g/m2"],
                ["Applicable standard", "EN 10219 (cold formed welded structural hollow sections)"],
            ],
            st,
            [42 * mm, 128 * mm],
        ),
        Spacer(1, 6),
        Paragraph(
            "All values in this table are absolute requirements for the tender. "
            "Substitutions require written approval from the technical office.",
            st["note"],
        ),
        Paragraph("3. Coating and finish", st["h2"]),
        Paragraph(
            "Sections shall be hot-dip galvanized after fabrication in accordance with "
            "EN ISO 1461. The minimum average coating mass shall be 505 g/m2 on the "
            "external surface. Pre-galvanized strip material (EN 10346) is not accepted "
            "for this package. Cut edges and weld seams shall be repaired with a zinc-rich "
            "compound compatible with the applied coating.",
            st["body"],
        ),
        Paragraph("4. Material traceability", st["h2"]),
        Paragraph(
            "Each delivery shall include mill certificates showing the steel grade "
            "S235JRH to EN 10219 and the coating inspection record to EN ISO 1461.",
            st["body"],
        ),
    ]

    doc.build(story)


# ---------------------------------------------------------------------------
# 2. Manufacturer A - compliant offer
# ---------------------------------------------------------------------------


def build_manufacturer_a(path: Path) -> None:
    st = styles()
    doc = DemoDoc(path, "Anadolu Profil - Square hollow sections datasheet", "DEMO-MFR-A")
    story = [
        Paragraph("ANADOLU PROFIL CELIK A.S.", st["brand"]),
        Paragraph("Square hollow sections - product datasheet", st["title"]),
        Paragraph(
            "Cold-formed welded square hollow sections for structural and architectural "
            "applications. Datasheet edition 04/2026. Page 1 of 2.",
            st["subtitle"],
        ),
        Paragraph("1. Product description", st["h2"]),
        Paragraph(
            "Anadolu Profil square hollow sections are produced from hot-rolled coil on "
            "continuous forming and welding lines. Sections are available in 6 m and 12 m "
            "stock lengths. Edges are deburred and the weld seam is dressed flush.",
            st["body"],
        ),
        Paragraph("2. Technical data - order item SHS 40.40.3.0", st["h2"]),
        info_table(
            [
                ("Profile", "Square hollow section 40 x 40 x 3.0 mm"),
                ("Outside dimensions", "40 mm x 40 mm"),
                ("Wall thickness", "3.0 mm nominal"),
                ("Steel grade", "S235JRH"),
                ("Manufacturing standard", "EN 10219-1"),
                ("Surface finish", "Hot-dip galvanized after fabrication, EN ISO 1461"),
                ("Coating mass", "620 g/m2 average (external surface)"),
                ("Length", "6000 mm and 12000 mm"),
                ("Tolerance", "EN 10219-2"),
            ],
            st,
            widths=(46 * mm, 124 * mm),
        ),
        Spacer(1, 4),
        Paragraph("3. Coating", st["h2"]),
        Paragraph(
            "All sections of this order item are hot-dip galvanized after fabrication in "
            "accordance with EN ISO 1461. The measured average coating mass is 620 g/m2, "
            "above the 505 g/m2 minimum of that standard. Coating thickness is typically "
            "86 microns.",
            st["body"],
        ),
        Paragraph("4. Quality and certification", st["h2"]),
        Paragraph(
            "Mill certificates to EN 10204 3.1 are issued with each delivery. Sections are "
            "dimensionally inspected to EN 10219-2 and coating mass is verified per batch.",
            st["body"],
        ),
        Paragraph("5. Range summary", st["h2"]),
        grid_table(
            ["Size (mm)", "Wall (mm)", "Grade", "Coating"],
            [
                ["40 x 40", "2.0 / 2.5 / 3.0", "S235JRH", "Hot-dip EN ISO 1461"],
                ["50 x 50", "2.5 / 3.0 / 4.0", "S235JRH", "Hot-dip EN ISO 1461"],
                ["60 x 60", "3.0 / 4.0", "S275J0H", "Hot-dip EN ISO 1461"],
                ["80 x 80", "4.0 / 5.0", "S275J0H", "Hot-dip EN ISO 1461"],
            ],
            st,
            [34 * mm, 42 * mm, 40 * mm, 54 * mm],
        ),
        Spacer(1, 6),
        Paragraph(
            "Values in this datasheet are typical catalogue values for the listed order "
            "item. Project-specific certificates prevail where they differ.",
            st["note"],
        ),
    ]
    doc.build(story)


# ---------------------------------------------------------------------------
# 3. Manufacturer B - partially non-compliant offer
# ---------------------------------------------------------------------------


def build_manufacturer_b(path: Path) -> None:
    st = styles()
    doc = DemoDoc(path, "Ege Metal - Box profile catalogue extract", "DEMO-MFR-B")
    story = [
        Paragraph("EGE METAL BORU SANAYI", st["brand"]),
        Paragraph("Box profile catalogue - structural range", st["title"]),
        Paragraph(
            "Cold-formed box profiles, zinc coated strip. Catalogue extract, "
            "edition 2026. Page 1 of 2.",
            st["subtitle"],
        ),
        Paragraph("1. General information", st["h2"]),
        Paragraph(
            "Ege Metal produces cold-formed box profiles from zinc coated steel strip. "
            "Profiles are formed, welded and cut to length on automated lines. The zinc "
            "coating is applied to the strip before forming, so cut ends and weld seams "
            "expose the base steel.",
            st["body"],
        ),
        Paragraph("2. Technical data - item BP-40.40.25", st["h2"]),
        info_table(
            [
                ("Profile", "Box profile 40 x 40 mm"),
                ("Outside dimensions", "40 mm x 40 mm"),
                ("Wall thickness", "2.5 mm nominal"),
                ("Steel grade", "S275J0H"),
                ("Surface finish", "Pre-galvanized strip, EN 10346, coating class Z275"),
                ("Coating mass", "275 g/m2 total (both surfaces)"),
                ("Length", "6000 mm"),
                ("Quality system", "ISO 9001 certified production"),
            ],
            st,
            widths=(46 * mm, 124 * mm),
        ),
        Spacer(1, 4),
        Paragraph("3. Surface protection", st["h2"]),
        Paragraph(
            "The base material is continuously hot-dip zinc coated strip to EN 10346 with "
            "a coating class of Z275, corresponding to 275 g/m2 total coating mass. "
            "Profiles are not galvanized after forming. Welded seams are left as formed.",
            st["body"],
        ),
        Paragraph("4. Availability", st["h2"]),
        Paragraph(
            "Standard stock lengths are 6 m. Alternative lengths and perforation patterns "
            "are available on request. Minimum order quantity applies to non-stock items.",
            st["body"],
        ),
        Paragraph("5. Range summary", st["h2"]),
        grid_table(
            ["Size (mm)", "Wall (mm)", "Grade", "Coating"],
            [
                ["25 x 25", "1.5 / 2.0", "S250GD", "Z275 pre-galvanized"],
                ["40 x 40", "2.0 / 2.5", "S275J0H", "Z275 pre-galvanized"],
                ["50 x 50", "2.5", "S275J0H", "Z275 pre-galvanized"],
                ["60 x 40", "2.5 / 3.0", "S275J0H", "Z275 pre-galvanized"],
            ],
            st,
            [34 * mm, 42 * mm, 40 * mm, 54 * mm],
        ),
        Spacer(1, 6),
        Paragraph(
            "Coatings on cut edges are not restored. For exterior applications, additional "
            "site treatment is recommended.",
            st["note"],
        ),
    ]
    doc.build(story)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_specification(OUT / "demo_specification.pdf")
    build_manufacturer_a(OUT / "demo_manufacturer_a.pdf")
    build_manufacturer_b(OUT / "demo_manufacturer_b.pdf")
    for name in ("demo_specification.pdf", "demo_manufacturer_a.pdf", "demo_manufacturer_b.pdf"):
        path = OUT / name
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
