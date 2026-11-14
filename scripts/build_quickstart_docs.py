"""Build the four-scenario Quick Start dataset.

Three PDFs that together exercise all four demonstration scenarios through the
real pipeline:

* **Exact match** — 60 x 60 mm stated identically on both sides.
* **Semantic match** — the offer writes the same facts differently
  (``S 235 JRH`` vs ``S235JRH``, ``EN 10219-1`` vs ``EN 10219``).
* **Critical deviation** — a nominal wall thickness, a different grade, and a
  pre-galvanized coating where hot-dip is required.
* **Over-spec** — a thicker minimum wall and a heavier coating than required.

Every page carries the same synthetic-document banner as the original demo set,
so generated files can never be mistaken for real project documents.

Run:  python scripts/build_quickstart_docs.py
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
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sample_docs" / "quickstart"

INK = colors.HexColor("#1B2430")
MUTED = colors.HexColor("#5A6672")
RULE = colors.HexColor("#D6DCE2")
DEMO_BG = colors.HexColor("#FFF4E5")
DEMO_INK = colors.HexColor("#8A5A00")
ACCENT = colors.HexColor("#1F4E79")
ZEBRA = colors.HexColor("#F5F7F9")

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
for regular, bold in (
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
):
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("QuickSans", str(regular)))
        pdfmetrics.registerFont(TTFont("QuickSans-Bold", str(bold)))
        FONT, FONT_BOLD = "QuickSans", "QuickSans-Bold"
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
            "cell", parent=base["Normal"], fontName=FONT, fontSize=8.8,
            textColor=INK, leading=12,
        ),
        "celllabel": ParagraphStyle(
            "celllabel", parent=base["Normal"], fontName=FONT_BOLD, fontSize=8.8,
            textColor=INK, leading=12,
        ),
    }


class QuickDoc(BaseDocTemplate):
    """A4 document with the synthetic-data banner on every page."""

    def __init__(self, path: Path, label: str, doc_id: str):
        super().__init__(
            str(path), pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=16 * mm, bottomMargin=18 * mm,
            title=label, author="SpecMatch AI quick start dataset",
            subject="Synthetic demonstration document",
        )
        self.label = label
        self.doc_id = doc_id
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(
            [PageTemplate(id="page", frames=[frame], onPage=self._decorate)]
        )

    def _decorate(self, canvas, doc) -> None:
        canvas.saveState()
        width, height = A4
        banner_h = 11 * mm
        canvas.setFillColor(DEMO_BG)
        canvas.rect(0, height - banner_h, width, banner_h, stroke=0, fill=1)
        canvas.setFillColor(DEMO_INK)
        canvas.setFont(FONT_BOLD, 8)
        canvas.drawString(
            20 * mm, height - 7.4 * mm,
            "SYNTHETIC DEMO DOCUMENT  |  Quick Start dataset  |  "
            "Not a real specification or manufacturer datasheet",
        )
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.6)
        canvas.line(20 * mm, height - banner_h, width - 20 * mm, height - banner_h)
        canvas.setFillColor(MUTED)
        canvas.setFont(FONT, 7.6)
        canvas.drawString(20 * mm, 11 * mm, f"{self.label}  |  {self.doc_id}")
        canvas.drawRightString(width - 20 * mm, 11 * mm, f"Page {doc.page}")
        canvas.restoreState()


def spec_table(rows: list[tuple[str, str]], st: dict) -> Table:
    data = [[Paragraph(k, st["celllabel"]), Paragraph(v, st["cell"])] for k, v in rows]
    table = Table(data, colWidths=[48 * mm, 122 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), ZEBRA),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
                ("BOX", (0, 0), (-1, -1), 0.6, RULE),
            ]
        )
    )
    return table


# ---------------------------------------------------------------------------
# 1. Project specification
# ---------------------------------------------------------------------------


def build_specification(path: Path) -> None:
    st = styles()
    doc = QuickDoc(path, "Section 05 12 23 - Galvanized square hollow sections", "QS-SPEC-01")
    story = [
        Paragraph("MERIDIAN CONSTRUCTION - TECHNICAL OFFICE", st["brand"]),
        Paragraph("Section 05 12 23 - Galvanized square hollow sections", st["title"]),
        Paragraph(
            "Project: Bosphorus Logistics Hub, Warehouse B - structural steel package. "
            "Document status: Issued for tender. Revision A.",
            st["subtitle"],
        ),
        Paragraph("1. Scope", st["h2"]),
        Paragraph(
            "This section covers hot-dip galvanized square hollow sections used for the "
            "canopy framing, mezzanine handrails and secondary structure of Warehouse B. "
            "All sections are hot-dip galvanized after fabrication.",
            st["body"],
        ),
        Paragraph("2. Technical requirements", st["h2"]),
        spec_table(
            [
                ("Section profile", "Square hollow section, 60 x 60 mm"),
                ("Wall thickness", "3.0 mm minimum"),
                ("Steel grade", "S235JRH"),
                (
                    "Galvanizing",
                    "Hot-dip galvanized to EN ISO 1461, minimum coating mass 505 g/m2",
                ),
                ("Applicable standard", "EN 10219"),
            ],
            st,
        ),
        Spacer(1, 10),
        Paragraph("3. Verification", st["h2"]),
        Paragraph(
            "The Contractor shall submit mill certificates and galvanizing thickness "
            "readings for every delivered batch. Offers that state a nominal wall "
            "thickness only, or a coating process other than hot-dip galvanizing, are "
            "considered non-compliant with this section.",
            st["body"],
        ),
        Paragraph("4. Notes", st["h2"]),
        Paragraph(
            "Cut edges and site welds shall be repaired with a zinc-rich compound to "
            "EN ISO 1461. Substitution of the steel grade requires written approval from "
            "the Structural Engineer.",
            st["note"],
        ),
    ]
    doc.build(story)


# ---------------------------------------------------------------------------
# 2. Manufacturer A - exact match, semantic match and over-spec
# ---------------------------------------------------------------------------


def build_manufacturer_a(path: Path) -> None:
    st = styles()
    doc = QuickDoc(path, "Marmara Celik - product datasheet", "QS-MFR-A")
    story = [
        Paragraph("MARMARA CELIK SANAYI A.S.", st["brand"]),
        Paragraph("Square hollow sections - hot-dip galvanized range", st["title"]),
        Paragraph(
            "Product datasheet for structural square hollow sections, hot-dip galvanized "
            "after fabrication. Rev. 3, valid from January.",
            st["subtitle"],
        ),
        Paragraph("Product data", st["h2"]),
        spec_table(
            [
                ("Outside dimensions", "60 x 60 mm"),
                ("Wall thickness", "3.2 mm minimum"),
                ("Steel grade", "S 235 JRH"),
                (
                    "Surface finish",
                    "Hot-dip galvanised after fabrication, EN ISO 1461, "
                    "coating mass 620 g/m2",
                ),
                ("Manufacturing standard", "EN 10219-1"),
            ],
            st,
        ),
        Spacer(1, 10),
        Paragraph("Range information", st["h2"]),
        Paragraph(
            "Standard stock lengths are 6 m and 12 m. Other lengths are cut to order. "
            "The minimum wall thickness stated above is guaranteed for every delivered "
            "length; the actual measured thickness is typically 3.25 mm.",
            st["body"],
        ),
        Paragraph("Coating", st["h2"]),
        Paragraph(
            "Sections are hot-dip galvanized after fabrication in accordance with "
            "EN ISO 1461. The average coating mass of 620 g/m2 exceeds the 505 g/m2 "
            "minimum required for this section range, which provides additional "
            "corrosion protection for exterior exposure.",
            st["body"],
        ),
        Paragraph("Notes", st["h2"]),
        Paragraph(
            "Material certificates to EN 10204 3.1 are supplied with each delivery. "
            "The grade is designated S 235 JRH in accordance with EN 10025-2.",
            st["note"],
        ),
    ]
    doc.build(story)


# ---------------------------------------------------------------------------
# 3. Manufacturer B - critical technical deviations
# ---------------------------------------------------------------------------


def build_manufacturer_b(path: Path) -> None:
    st = styles()
    doc = QuickDoc(path, "Karadeniz Boru - catalogue extract", "QS-MFR-B")
    story = [
        Paragraph("KARADENIZ BORU VE PROFIL", st["brand"]),
        Paragraph("Box profile catalogue - structural range", st["title"]),
        Paragraph(
            "Catalogue extract for cold formed square hollow sections, "
            "pre-galvanized strip. Edition 2024.",
            st["subtitle"],
        ),
        Paragraph("Dimensions and grade", st["h2"]),
        spec_table(
            [
                ("Outside dimensions", "60 x 60 mm"),
                ("Wall thickness", "2.5 mm nominal"),
                ("Steel grade", "S275J0H"),
                (
                    "Surface finish",
                    "Pre-galvanized strip, EN 10346, coating class Z275, "
                    "coating mass 275 g/m2 total (both surfaces)",
                ),
            ],
            st,
        ),
        Spacer(1, 10),
        Paragraph("Coating", st["h2"]),
        Paragraph(
            "Profiles are formed from pre-galvanized strip to EN 10346, coating class "
            "Z275. Cut edges are not re-coated. For exterior applications, additional "
            "site treatment is recommended.",
            st["body"],
        ),
        Paragraph("Notes", st["h2"]),
        Paragraph(
            "Wall thickness is stated as nominal for the strip used in forming. "
            "The range is intended for interior partitions and light shelving.",
            st["note"],
        ),
    ]
    doc.build(story)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    build_specification(OUT / "quickstart_specification.pdf")
    build_manufacturer_a(OUT / "quickstart_manufacturer_a.pdf")
    build_manufacturer_b(OUT / "quickstart_manufacturer_b.pdf")

    for name in (
        "quickstart_specification.pdf",
        "quickstart_manufacturer_a.pdf",
        "quickstart_manufacturer_b.pdf",
    ):
        path = OUT / name
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
