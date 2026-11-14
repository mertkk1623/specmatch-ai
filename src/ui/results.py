"""Results presentation shared by the sample demo and the live analysis page."""

from __future__ import annotations

from html import escape

import streamlit as st

from ..schemas import AnalysisResult, CriterionResult, ManufacturerAnalysis
from .theme import badge, callout, markup, stat_strip

_TONE = {"pass": ("pass", "Pass"), "fail": ("fail", "Conflict"), "unknown": ("unknown", "Not verifiable")}

CRITERION_TITLES = {
    "dimensions": "Profile dimensions",
    "wall_thickness": "Wall thickness",
    "material_grade": "Material grade",
    "galvanizing": "Galvanizing / coating",
    "standard": "Applicable standard",
}


def _e(value: object | None) -> str:
    if value is None or value == "":
        return "—"
    return escape(_one_line(value))


def _one_line(value: object) -> str:
    """Collapse all whitespace runs (including newlines) into single spaces.

    Model-written explanations can contain line breaks. Inline HTML is later
    parsed as Markdown, where a blank line inside an HTML block ends the block
    and the remaining indented lines render as a code block. Keeping every
    dynamic string on one line prevents that class of rendering bug.
    """

    return " ".join(str(value).split())


def _t(value: object | None) -> str:
    """Escape free-form prose and keep it on a single line."""

    if value is None or value == "":
        return ""
    return escape(_one_line(value))


def _evidence_html(ref) -> str:
    if ref is None or not getattr(ref, "is_present", False):
        return ""
    parts = []
    if ref.page:
        parts.append(f'<span class="pg">p. {ref.page}</span>')
    if ref.excerpt:
        parts.append(f"<q>{escape(ref.short(170))}</q>")
    return f'<div class="sm-evidence">{"".join(parts)}</div>'


def _checks_html(result: CriterionResult) -> str:
    if not result.checks:
        return ""
    items = []
    for check in result.checks:
        cls, label = _TONE.get(check.outcome, ("unknown", check.outcome))
        note = f'<span class="note">{_t(check.note)}</span>' if check.note else ""
        values = ""
        if check.spec_text or check.offer_text:
            values = f" · {_e(check.spec_text)} → {_e(check.offer_text)}"
        items.append(
            f'<li><span class="lbl">{escape(check.label)}</span>'
            f'<span class="tone {cls}">{escape(label)}</span>'
            f'<span>{values}</span>{note}</li>'
        )
    return f'<ul class="sm-checks">{"".join(items)}</ul>'


def _row_html(result: CriterionResult) -> str:
    title = CRITERION_TITLES.get(result.criterion, result.criterion)
    source = "AI explanation" if result.explanation_source == "ai" else "Deterministic rule"
    return f"""
    <tr>
      <td class="c-crit">{escape(title)}
        <span class="sub">{_t(result.headline)}</span>
      </td>
      <td>{badge(result.status.value)}</td>
      <td class="c-val">
        <div><span class="k">Spec</span> {_e(result.spec_display)}{_evidence_html(result.spec_evidence)}</div>
        <div><span class="k">Offer</span> {_e(result.offer_display)}{_evidence_html(result.offer_evidence)}</div>
      </td>
      <td class="c-expl">{_t(result.explanation)}{_checks_html(result)}
        <div class="sm-src">{source}</div>
      </td>
    </tr>
    """


def manufacturer_block(manufacturer: ManufacturerAnalysis) -> None:
    counts = manufacturer.counts
    st.markdown(
        f"""
        <div class="sm-mfr">
          <div>
            <h2>{escape(manufacturer.name)}</h2>
            <p class="doc">{escape(manufacturer.document_name)} · {manufacturer.document_meta.page_count} page(s)
            · parsed with {escape(manufacturer.document_meta.parser)}</p>
          </div>
          <div class="sm-tally">
            <span class="ok">{counts.compliant} compliant</span>
            <span class="bad">{counts.non_compliant} non-compliant</span>
            <span class="warn">{counts.unverified} unverified</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    rows = "".join(_row_html(result) for result in manufacturer.criteria)
    st.markdown(
        markup(
            f"""
        <table class="sm-table">
          <thead>
            <tr>
              <th style="width:19%">Criterion</th>
              <th style="width:11%">Status</th>
              <th style="width:29%">Values and evidence</th>
              <th style="width:41%">Explanation</th>
            </tr>
          </thead>
          <tbody>{rows}</tbody>
        </table>
        """
        ),
        unsafe_allow_html=True,
    )


def results_header(result: AnalysisResult, show_meta: bool = True) -> None:
    totals = result.all_counts()
    stat_strip(
        [
            ("Compliant", str(totals.compliant), "ok"),
            ("Non-compliant", str(totals.non_compliant), "bad"),
            ("Unverified", str(totals.unverified), "warn"),
            ("Not specified", str(totals.not_specified), ""),
        ]
    )
    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    source = "AI narrative · statuses fixed by deterministic rules" if result.summary_source == "ai" else "Deterministic summary"
    st.markdown(
        f'<div class="sm-callout">{_t(result.summary)}'
        f'<div class="sm-src" style="margin-top:6px">{escape(source)}</div></div>',
        unsafe_allow_html=True,
    )

    if show_meta:
        meta_bits = [
            f"Specification: {escape(result.spec.document_name)}",
            f"Generated {result.created_at.strftime('%d %b %Y, %H:%M UTC')}",
            f"Analysis {escape(result.analysis_id)}",
        ]
        if result.duration_seconds:
            meta_bits.append(f"{result.duration_seconds:g}s processing")
        st.markdown(
            '<p class="sm-small" style="margin-top:12px">' + " · ".join(meta_bits) + "</p>",
            unsafe_allow_html=True,
        )


def requirements_table(result: AnalysisResult) -> None:
    req = result.spec.requirements
    rows = [
        ("Profile dimensions", _dim_display(req.dimensions), getattr(req.dimensions, "page", None)),
        (
            "Wall thickness",
            (
                f"{req.wall_thickness.value:g} {req.wall_thickness.unit or ''} "
                f"({req.wall_thickness.kind.value})".strip()
                if req.wall_thickness and req.wall_thickness.value is not None
                else None
            ),
            getattr(req.wall_thickness, "page", None),
        ),
        ("Material grade", req.material_grade.grade if req.material_grade else None,
         getattr(req.material_grade, "page", None)),
        ("Galvanizing", _galv_display(req.galvanizing), getattr(req.galvanizing, "page", None)),
        ("Applicable standard", req.standard.designation if req.standard else None,
         getattr(req.standard, "page", None)),
    ]
    body = "".join(
        f'<tr><td class="c-crit">{escape(name)}</td><td class="c-val">{_e(value)}</td>'
        f'<td class="c-val">{f"p. {page}" if page else "—"}</td></tr>'
        for name, value, page in rows
    )
    st.markdown(
        markup(
            f"""
        <table class="sm-table">
          <thead><tr>
            <th style="width:26%">Requirement</th>
            <th style="width:56%">Extracted value</th>
            <th style="width:18%">Source page</th>
          </tr></thead>
          <tbody>{body}</tbody>
        </table>
        """
        ),
        unsafe_allow_html=True,
    )


def _dim_display(field) -> str | None:
    if field is None:
        return None
    if field.width and field.height and field.width.value and field.height.value:
        unit = field.width.unit or ""
        return f"{field.width.value:g} × {field.height.value:g} {unit}".strip()
    return field.raw_text


def _galv_display(field) -> str | None:
    if field is None:
        return None
    if field.raw_text and len(field.raw_text) <= 90:
        return field.raw_text
    parts = []
    if field.process:
        parts.append(field.process.value.replace("_", " "))
    if field.standard:
        parts.append(field.standard)
    if field.coating_mass_value is not None:
        parts.append(f"{field.coating_mass_value:g} {field.coating_mass_unit or ''}".strip())
    return " · ".join(parts) or field.raw_text


def validation_issues(result: AnalysisResult) -> None:
    issues = result.validation_issues
    if not issues:
        return
    with st.expander(f"Extraction and validation notes ({len(issues)})", expanded=False):
        for issue in issues:
            icon = "⚠" if issue.severity == "warning" else "⛔"
            st.markdown(f"{icon} **{escape(issue.document)}** — {_t(issue.message)}")


def parser_notes(result: AnalysisResult) -> None:
    if not result.parser_notes:
        return
    with st.expander("Document processing details", expanded=False):
        for note in result.parser_notes:
            st.markdown(f"- {escape(note)}", unsafe_allow_html=True)
        if result.model:
            st.markdown(f"- Extraction model: `{result.model}`")
        st.markdown(
            "- Compliance statuses are decided by Python rules, not by the model."
        )


def download_button(result: AnalysisResult, key: str) -> None:
    from ..report import build_report_html, report_filename

    st.download_button(
        "Download comparison report (HTML)",
        data=build_report_html(result).encode("utf-8"),
        file_name=report_filename(result),
        mime="text/html",
        key=key,
        help="Self-contained HTML report. Open it in a browser or print it to PDF.",
    )


def disclaimer() -> None:
    callout(
        "<strong>Responsible use.</strong> SpecMatch AI is a first-pass comparison "
        "assistant. It is not an engineering approval, a certification, or a purchasing "
        "decision. Always verify values against the original documents.",
        tone="info",
    )
