"""PDF parsing: Docling for layout-aware text and tables, pypdf as fallback.

The application needs three things from a PDF:

1. Per-page text, so an evidence excerpt can be verified against the page it
   claims to come from.
2. Tables, rendered as compact text that preserves row structure, because
   catalogue data usually lives in tables.
3. Honest metadata: which parser ran, how many pages, and any warnings.

Docling is the primary parser. If it is not installed, fails, or returns empty
text, the parser falls back to pypdf and says so. The UI shows the parser name
so a reviewer always knows which path produced the extraction.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .schemas import ParsedPage


@dataclass
class ParsedDocument:
    filename: str
    pages: list[ParsedPage]
    parser: str
    tables: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def char_count(self) -> int:
        return sum(len(page.text) for page in self.pages)

    @property
    def is_empty(self) -> bool:
        return self.char_count < 40

    def page_text(self, number: int) -> str:
        for page in self.pages:
            if page.number == number:
                return page.text
        return ""

    def numbered_text(self, max_chars: int = 60_000) -> str:
        """Model input: page-tagged text so citations can be validated."""

        chunks: list[str] = []
        budget = max_chars
        for page in self.pages:
            header = f"\n===== PAGE {page.number} ====="
            body = page.text.strip()
            if not body:
                body = "(no extractable text on this page)"
            block = f"{header}\n{body}"
            if len(block) > budget:
                block = block[:budget] + "\n[truncated]"
            chunks.append(block)
            budget -= len(block)
            if budget <= 0:
                chunks.append("\n[remaining pages omitted: document too long]")
                break
        if self.tables:
            chunks.append("\n===== EXTRACTED TABLES =====")
            for index, table in enumerate(self.tables, start=1):
                chunks.append(f"\n[Table {index}]\n{table}")
        return "\n".join(chunks).strip()


class DocumentParseError(RuntimeError):
    """Raised when both parsers fail to produce usable text."""


# ---------------------------------------------------------------------------
# pypdf fallback
# ---------------------------------------------------------------------------


def parse_with_pypdf(path: Path) -> ParsedDocument:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # noqa: BLE001 - surfaced as a user-facing warning
            raise DocumentParseError("The PDF is password protected.") from exc

    pages: list[ParsedPage] = []
    warnings: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            text = ""
            warnings.append(f"Page {index} could not be read ({type(exc).__name__}).")
        pages.append(ParsedPage(number=index, text=text))

    if not pages:
        raise DocumentParseError("The PDF contains no readable pages.")

    return ParsedDocument(
        filename=path.name,
        pages=pages,
        parser="pypdf (fallback)",
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Docling
# ---------------------------------------------------------------------------


def _table_to_text(table) -> str:
    """Render a Docling table as pipe-separated rows."""

    try:
        frame = table.export_to_dataframe()
    except Exception:  # noqa: BLE001 - degrade to markdown/plain text
        try:
            return str(table.export_to_markdown()).strip()
        except Exception:  # noqa: BLE001
            return ""

    if frame is None or frame.empty:
        return ""
    rows: list[str] = []
    header = [str(col).strip() for col in frame.columns]
    if any(header):
        rows.append(" | ".join(header))
    for _, row in frame.iterrows():
        cells = ["" if value is None else str(value).strip() for value in row.tolist()]
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _docling_pages(document, filename: str) -> tuple[list[ParsedPage], list[str], list[str]]:
    per_page: dict[int, list[str]] = {}
    tables: list[str] = []

    for item, _level in document.iterate_items():
        page_no = None
        for prov in getattr(item, "prov", None) or []:
            if prov.page_no is not None:
                page_no = int(prov.page_no)
                break
        text: str | None = None
        label = getattr(item, "label", "") or ""

        table_text = ""
        if label == "table":
            table_text = _table_to_text(item)
            if table_text:
                tables.append(table_text)
        if table_text:
            text = table_text
        else:
            candidate = getattr(item, "text", None)
            if isinstance(candidate, str) and candidate.strip():
                text = candidate.strip()

        if not text or page_no is None:
            continue
        per_page.setdefault(page_no, []).append(text)

    total_pages = 0
    pages_meta = getattr(document, "pages", None) or {}
    try:
        total_pages = max(pages_meta.keys()) if pages_meta else 0
    except Exception:  # noqa: BLE001
        total_pages = 0
    if per_page:
        total_pages = max(total_pages, max(per_page))

    pages = [
        ParsedPage(number=number, text="\n\n".join(per_page.get(number, [])))
        for number in range(1, total_pages + 1)
    ]
    warnings: list[str] = []
    blank = [page.number for page in pages if not page.text.strip()]
    if blank and len(blank) < len(pages):
        warnings.append(
            "Docling returned no text for page(s) " + ", ".join(map(str, blank))[:80] + "."
        )
    return pages, tables, warnings


def parse_with_docling(path: Path) -> ParsedDocument:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = False  # digital PDFs; OCR is out of scope for V1
    options.do_table_structure = True
    options.generate_page_images = False

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )
    result = converter.convert(str(path))
    pages, tables, warnings = _docling_pages(result.document, path.name)
    return ParsedDocument(
        filename=path.name,
        pages=pages,
        parser="Docling",
        tables=tables,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_pdf(
    path: str | Path,
    *,
    prefer_docling: bool = True,
    max_pages: int | None = None,
) -> ParsedDocument:
    """Parse a PDF into per-page text, falling back to pypdf when needed."""

    file_path = Path(path)
    if not file_path.exists():
        raise DocumentParseError(f"File not found: {file_path.name}")
    if file_path.suffix.lower() != ".pdf":
        raise DocumentParseError("Only PDF files are supported in this version.")

    warnings: list[str] = []
    document: ParsedDocument | None = None

    if prefer_docling:
        try:
            document = parse_with_docling(file_path)
            if document.is_empty:
                warnings.append(
                    "Docling produced little or no text; the document may be a scan."
                )
        except Exception as exc:  # noqa: BLE001 - fall back deliberately
            warnings.append(
                f"Docling could not parse this file ({type(exc).__name__}); "
                "pypdf fallback was used."
            )
            document = None

    if document is None or document.is_empty:
        fallback = parse_with_pypdf(file_path)
        fallback.warnings = warnings + fallback.warnings
        document = fallback
    else:
        document.warnings = warnings + document.warnings

    if max_pages and document.page_count > max_pages:
        document.warnings.append(
            f"Document has {document.page_count} pages; only the first {max_pages} were used."
        )
        document.pages = document.pages[:max_pages]

    if document.is_empty:
        raise DocumentParseError(
            "No extractable text was found. Scanned PDFs need OCR, which this version "
            "does not support."
        )

    return document


def parse_uploaded_file(data: bytes, filename: str) -> ParsedDocument:
    """Parse uploaded bytes by writing them to a temporary file."""

    suffix = Path(filename).suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
        handle.write(data)
        temp_path = Path(handle.name)
    try:
        document = parse_pdf(temp_path)
        document.filename = filename
        return document
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
