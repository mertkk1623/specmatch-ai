"""Downloadable report export.

The report is a single self-contained HTML file: inline CSS, no external
assets, no scripts. It opens in any browser, prints cleanly to PDF, and can be
attached to an email without broken links. Every value shown here comes from the
validated :class:`AnalysisResult`; nothing is generated at export time.
"""

from __future__ import annotations

from datetime import timezone
from html import escape

from .schemas import AnalysisResult, CriterionResult, ManufacturerAnalysis, Status

STATUS_TONE = {
    Status.COMPLIANT: ("Compliant", "ok"),
    Status.NON_COMPLIANT: ("Non-compliant", "bad"),
    Status.UNVERIFIED: ("Unverified", "warn"),
    Status.NOT_SPECIFIED: ("Not specified", "muted"),
}

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
    return escape(str(value))


def _status_badge(status: Status) -> str:
    label, tone = STATUS_TONE[status]
    return f'<span class="badge badge-{tone}">{escape(label)}</span>'


def _evidence(ref) -> str:
    if ref is None or not getattr(ref, "is_present", False):
        return ""
    page = f'<span class="page">p. {ref.page}</span>' if ref.page else ""
    excerpt = f'<q>{escape(ref.short(180))}</q>' if ref.excerpt else ""
    return f'<div class="evidence">{page}{excerpt}</div>'


def _criterion_row(result: CriterionResult) -> str:
    checks = ""
    if result.checks:
        items = []
        for check in result.checks:
            outcome = {"pass": "Pass", "fail": "Conflict", "unknown": "Not verifiable"}.get(
                check.outcome, check.outcome
            )
            note = f'<span class="chk-note">{escape(check.note)}</span>' if check.note else ""
            items.append(
                "<li>"
                f'<span class="chk-label">{escape(check.label)}</span>'
                f'<span class="chk-tone chk-{escape(check.outcome)}">{escape(outcome)}</span>'
                f'<span class="chk-values">{_e(check.spec_text)} → {_e(check.offer_text)}</span>'
                f"{note}</li>"
            )
        checks = f'<ul class="checks">{"".join(items)}</ul>'

    return f"""
    <tr>
      <td class="crit">
        <div class="crit-title">{escape(CRITERION_TITLES.get(result.criterion, result.criterion))}</div>
        <div class="crit-headline">{escape(result.headline)}</div>
      </td>
      <td>{_status_badge(result.status)}</td>
      <td class="vals">
        <div><span class="k">Spec</span> {_e(result.spec_display)}{_evidence(result.spec_evidence)}</div>
        <div><span class="k">Offer</span> {_e(result.offer_display)}{_evidence(result.offer_evidence)}</div>
      </td>
      <td class="expl">
        <p>{escape(result.explanation)}</p>
        {checks}
        <div class="src">Explanation: {'AI' if result.explanation_source == 'ai' else 'deterministic rule'}</div>
      </td>
    </tr>
    """


def _manufacturer_block(manufacturer: ManufacturerAnalysis) -> str:
    counts = manufacturer.counts
    rows = "".join(_criterion_row(result) for result in manufacturer.criteria)
    return f"""
    <section class="manufacturer">
      <header class="mfr-head">
        <div>
          <h2>{escape(manufacturer.name)}</h2>
          <p class="doc">{escape(manufacturer.document_name)} · {manufacturer.document_meta.page_count} page(s) · parsed with {escape(manufacturer.document_meta.parser)}</p>
        </div>
        <div class="tally">
          <span class="tally-ok">{counts.compliant} compliant</span>
          <span class="tally-bad">{counts.non_compliant} non-compliant</span>
          <span class="tally-warn">{counts.unverified} unverified</span>
        </div>
      </header>
      <table class="grid">
        <thead>
          <tr>
            <th style="width:20%">Criterion</th>
            <th style="width:11%">Status</th>
            <th style="width:30%">Values</th>
            <th style="width:39%">Explanation and checks</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
    """


def build_report_html(result: AnalysisResult) -> str:
    """Render a standalone HTML report."""

    created = result.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    stamp = created.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    totals = result.all_counts()
    blocks = "".join(_manufacturer_block(m) for m in result.manufacturers)

    issues = ""
    if result.validation_issues:
        items = "".join(
            f'<li><strong>{escape(issue.document)}</strong>: {escape(issue.message)}</li>'
            for issue in result.validation_issues
        )
        issues = f"""
        <section class="notes">
          <h2>Extraction and validation notes</h2>
          <ul>{items}</ul>
        </section>
        """

    spec_req = result.spec.requirements
    evidence_rows = []
    for key, title in CRITERION_TITLES.items():
        field = getattr(spec_req, key, None)
        page = getattr(field, "page", None) if field else None
        excerpt = getattr(field, "excerpt", None) if field else None
        evidence_rows.append(
            f"<tr><td>{escape(title)}</td><td>{_e(page)}</td><td>{_e(excerpt)}</td></tr>"
        )

    demo_note = (
        '<p class="demo-note">Demonstration analysis. The input documents are synthetic '
        "sample files created for this portfolio project.</p>"
        if result.demo
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SpecMatch AI comparison report — {escape(result.spec.document_name)}</title>
<style>
  :root {{
    --ink:#1B2430; --muted:#5C6875; --line:#DCE2E8; --soft:#F6F8FA;
    --ok:#1E6B45; --ok-bg:#E9F5EE; --bad:#A02929; --bad-bg:#FBEBEB;
    --warn:#8A5A00; --warn-bg:#FFF5E3; --muted-bg:#EEF1F4;
    --accent:#1F4E79;
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; padding:40px 32px 64px; background:#fff; color:var(--ink);
    font:14px/1.55 "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  .sheet {{ max-width:1120px; margin:0 auto; }}
  header.top {{ border-bottom:2px solid var(--ink); padding-bottom:16px; margin-bottom:8px; }}
  .eyebrow {{ font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); font-weight:600; }}
  h1 {{ font-size:24px; margin:8px 0 6px; letter-spacing:-.01em; }}
  .meta {{ display:flex; flex-wrap:wrap; gap:6px 22px; font-size:12px; color:var(--muted); }}
  .demo-note {{
    margin:18px 0 0; padding:10px 14px; border-left:3px solid var(--warn);
    background:var(--warn-bg); color:#6C4A00; font-size:12.5px;
  }}
  .summary {{ display:grid; grid-template-columns:1fr 300px; gap:24px; margin:24px 0 8px; }}
  .summary p {{ margin:0; font-size:14.5px; }}
  .summary .src {{ margin-top:8px; font-size:11.5px; color:var(--muted); }}
  .totals {{ border:1px solid var(--line); border-radius:6px; overflow:hidden; font-size:12.5px; }}
  .totals div {{ display:flex; justify-content:space-between; padding:7px 12px; border-bottom:1px solid var(--line); }}
  .totals div:last-child {{ border-bottom:0; }}
  .totals b {{ font-variant-numeric:tabular-nums; }}
  h2 {{ font-size:15px; margin:0; letter-spacing:-.005em; }}
  section.manufacturer {{ margin-top:34px; page-break-inside:avoid; }}
  .mfr-head {{ display:flex; justify-content:space-between; align-items:flex-end; gap:16px; padding-bottom:9px; border-bottom:1px solid var(--ink); }}
  .mfr-head .doc {{ margin:3px 0 0; font-size:12px; color:var(--muted); }}
  .tally {{ display:flex; gap:12px; font-size:12px; white-space:nowrap; }}
  .tally-ok {{ color:var(--ok); font-weight:600; }}
  .tally-bad {{ color:var(--bad); font-weight:600; }}
  .tally-warn {{ color:var(--warn); font-weight:600; }}
  table.grid {{ width:100%; border-collapse:collapse; margin-top:10px; table-layout:fixed; }}
  table.grid th {{ text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:.08em;
    color:var(--muted); font-weight:600; padding:7px 10px; border-bottom:1px solid var(--line); }}
  table.grid td {{ padding:12px 10px; border-bottom:1px solid var(--line); vertical-align:top; font-size:12.6px; }}
  .crit-title {{ font-weight:600; }}
  .crit-headline {{ color:var(--muted); font-size:12px; margin-top:3px; }}
  .vals .k {{ display:inline-block; min-width:34px; font-size:10.5px; text-transform:uppercase;
    letter-spacing:.07em; color:var(--muted); }}
  .vals div + div {{ margin-top:6px; }}
  .evidence {{ margin:4px 0 0 34px; font-size:11.5px; color:var(--muted); }}
  .evidence .page {{ font-weight:600; margin-right:6px; color:var(--accent); }}
  .evidence q {{ font-style:italic; }}
  .badge {{ display:inline-block; padding:3px 8px; border-radius:3px; font-size:11px; font-weight:600; white-space:nowrap; }}
  .badge-ok {{ background:var(--ok-bg); color:var(--ok); }}
  .badge-bad {{ background:var(--bad-bg); color:var(--bad); }}
  .badge-warn {{ background:var(--warn-bg); color:var(--warn); }}
  .badge-muted {{ background:var(--muted-bg); color:var(--muted); }}
  .expl p {{ margin:0 0 6px; }}
  ul.checks {{ margin:6px 0 0; padding-left:0; list-style:none; font-size:11.7px; color:var(--muted); }}
  ul.checks li {{ padding:4px 0; border-top:1px dotted var(--line); }}
  .chk-label {{ color:var(--ink); font-weight:600; margin-right:6px; }}
  .chk-tone {{ font-size:10px; text-transform:uppercase; letter-spacing:.06em; margin-right:6px; }}
  .chk-pass {{ color:var(--ok); }}
  .chk-fail {{ color:var(--bad); }}
  .chk-unknown {{ color:var(--warn); }}
  .chk-values {{ color:var(--muted); }}
  .chk-note {{ display:block; margin-top:2px; font-style:italic; }}
  .src {{ margin-top:6px; font-size:10.5px; color:#8593a1; }}
  section.notes {{ margin-top:34px; page-break-inside:avoid; }}
  section.notes ul {{ margin:10px 0 0; padding-left:18px; font-size:12.4px; color:var(--muted); }}
  section.spec {{ margin-top:34px; page-break-inside:avoid; }}
  table.plain {{ width:100%; border-collapse:collapse; margin-top:10px; font-size:12.4px; }}
  table.plain th {{ text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:.08em;
    color:var(--muted); padding:6px 10px; border-bottom:1px solid var(--line); }}
  table.plain td {{ padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
  footer {{ margin-top:40px; padding-top:14px; border-top:1px solid var(--line); font-size:11.5px; color:var(--muted); }}
  @media print {{
    body {{ padding:0; font-size:11.5px; }}
    section.manufacturer, section.notes, section.spec {{ break-inside:avoid; }}
    .demo-note {{ border-left-color:#8A5A00; }}
  }}
  @media (max-width:860px) {{
    body {{ padding:24px 16px 48px; }}
    .summary {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>
<div class="sheet">
  <header class="top">
    <div class="eyebrow">SpecMatch AI · Technical specification comparison</div>
    <h1>Compliance comparison report</h1>
    <div class="meta">
      <span><strong>Specification:</strong> {escape(result.spec.document_name)}</span>
      <span><strong>Generated:</strong> {stamp}</span>
      <span><strong>Analysis ID:</strong> {escape(result.analysis_id)}</span>
      <span><strong>Model:</strong> {escape(result.model or '—')}</span>
      <span><strong>Documents compared:</strong> {len(result.manufacturers)}</span>
    </div>
  </header>
  {demo_note}

  <div class="summary">
    <div>
      <p>{escape(result.summary)}</p>
      <div class="src">Summary source: {'AI narrative, statuses fixed by deterministic rules' if result.summary_source == 'ai' else 'deterministic rules'}</div>
    </div>
    <div class="totals">
      <div><span>Compliant</span><b>{totals.compliant}</b></div>
      <div><span>Non-compliant</span><b>{totals.non_compliant}</b></div>
      <div><span>Unverified</span><b>{totals.unverified}</b></div>
      <div><span>Not specified in project spec</span><b>{totals.not_specified}</b></div>
    </div>
  </div>

  {blocks}

  <section class="spec">
    <h2>Specification requirements and evidence</h2>
    <table class="plain">
      <thead><tr><th style="width:34%">Criterion</th><th style="width:10%">Page</th><th>Extracted evidence</th></tr></thead>
      <tbody>{''.join(evidence_rows)}</tbody>
    </table>
  </section>

  {issues}

  <footer>
    SpecMatch AI is a first-pass comparison assistant. This report is not an engineering approval,
    a certification, or a purchasing decision. Verify all values against the original documents before use.
    Statuses are decided by deterministic rules; the AI extracts fields and writes explanations only.
  </footer>
</div>
</body>
</html>
"""


def report_filename(result: AnalysisResult) -> str:
    stem = result.spec.document_name.rsplit(".", 1)[0]
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in stem).strip("-")
    return f"specmatch-report-{safe or 'analysis'}-{result.analysis_id}.html"
