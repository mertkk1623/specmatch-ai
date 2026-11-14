"""Design system: CSS, page shell, and shared UI primitives.

The visual direction is restrained B2B SaaS: a single accent colour, a light
neutrals palette, one serif-free type scale, generous spacing, and no
decorative gradients or animations. Tables and evidence must stay highly legible
because that is what a technical-office reviewer actually reads.
"""

from __future__ import annotations

from html import escape

import streamlit as st

ACCENT = "#1F4E79"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --ink: #1B2430;
  --ink-soft: #3D4956;
  --muted: #66727F;
  --line: #E1E6EB;
  --line-strong: #C9D2DA;
  --surface: #FFFFFF;
  --surface-alt: #F7F9FB;
  --surface-tint: #F1F5F9;
  --accent: #1F4E79;
  --accent-dark: #173C5E;
  --accent-soft: #EBF2F8;
  --ok: #1D6B45;
  --ok-soft: #E8F4EE;
  --bad: #A32A2A;
  --bad-soft: #FBECEC;
  --warn: #8A5A00;
  --warn-soft: #FFF6E5;
  --radius: 8px;
}

html, body, [class*="css"], .stApp {
  font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
  color: var(--ink);
}
.stApp { background: var(--surface); }
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stSidebar"], [data-testid="stSidebarNav"],
[data-testid="stSidebarCollapsedControl"], [data-testid="stExpandSidebarButton"],
[data-testid="stMainMenu"] { display: none !important; }
[data-testid="stSkipToMainContent"], a[href="#main"] { display: none !important; }
[data-testid="stAppViewContainer"] > .main { padding-top: 0; }
.block-container {
  padding: 0 2.4rem 4rem 2.4rem;
  max-width: 1180px;
}
@media (max-width: 900px) {
  .block-container { padding: 0 1rem 3rem 1rem; }
}

/* ---------- Top navigation ---------- */
.sm-nav {
  display: flex; align-items: center; justify-content: space-between;
  gap: 24px; padding: 18px 0 16px; border-bottom: 1px solid var(--line);
  margin-bottom: 0;
}
.sm-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.sm-mark {
  width: 26px; height: 26px; border-radius: 5px; background: var(--accent);
  display: inline-flex; align-items: center; justify-content: center;
  color: #fff; font-weight: 700; font-size: 13px; letter-spacing: .02em;
}
.sm-wordmark { font-weight: 700; font-size: 15.5px; color: var(--ink); letter-spacing: -.01em; }
.sm-wordmark span { color: var(--accent); }
.sm-navlinks { display: flex; align-items: center; gap: 6px; }
.sm-navlinks a {
  color: var(--ink-soft); text-decoration: none; font-size: 13.5px; font-weight: 500;
  padding: 7px 12px; border-radius: 5px;
}
.sm-navlinks a:hover { background: var(--surface-tint); color: var(--ink); }
.sm-navlinks a.active { color: var(--accent); background: var(--accent-soft); font-weight: 600; }
.sm-navmeta { font-size: 11.5px; color: var(--muted); display: flex; align-items: center; gap: 8px; }
.sm-navmeta .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--ok); display: inline-block; }
.sm-navmeta .dot.off { background: #B9C2CB; }

/* ---------- Typography ---------- */
.sm-eyebrow {
  font-size: 11px; font-weight: 600; letter-spacing: .13em; text-transform: uppercase;
  color: var(--accent); margin: 0 0 14px;
}
h1.sm-h1 {
  font-size: 40px; line-height: 1.14; font-weight: 700; letter-spacing: -.022em;
  color: var(--ink); margin: 0 0 18px;
}
h2.sm-h2 { font-size: 22px; line-height: 1.3; font-weight: 650; letter-spacing: -.012em; margin: 0 0 10px; }
h3.sm-h3 { font-size: 15px; font-weight: 650; margin: 0 0 6px; letter-spacing: -.005em; }
p.sm-lead { font-size: 16.5px; line-height: 1.6; color: var(--ink-soft); margin: 0 0 22px; max-width: 66ch; }
p.sm-body { font-size: 14px; line-height: 1.65; color: var(--ink-soft); margin: 0 0 12px; }
p.sm-small { font-size: 12.5px; line-height: 1.6; color: var(--muted); margin: 0 0 8px; }
.sm-section { margin: 56px 0 0; }
.sm-section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 20px; margin-bottom: 18px; }
.sm-rule { height: 1px; background: var(--line); border: 0; margin: 0; }

/* ---------- Hero ---------- */
.sm-hero { padding: 68px 0 20px; }
.sm-hero-grid { display: grid; grid-template-columns: 1.15fr .85fr; gap: 56px; align-items: start; }
@media (max-width: 980px) { .sm-hero-grid { grid-template-columns: 1fr; gap: 32px; } }

/* ---------- Cards ---------- */
.sm-card {
  border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface);
  padding: 20px 22px;
}
.sm-card.flat { background: var(--surface-alt); border-color: var(--line); }
.sm-card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 900px) { .sm-card-grid { grid-template-columns: 1fr; } }
.sm-step-num {
  font-size: 11px; font-weight: 700; letter-spacing: .1em; color: var(--accent);
  border: 1px solid var(--accent-soft); background: var(--accent-soft);
  border-radius: 4px; padding: 2px 7px; display: inline-block; margin-bottom: 12px;
}
.sm-card p { margin: 0; font-size: 13.2px; line-height: 1.6; color: var(--muted); }

/* ---------- Stat strip ---------- */
.sm-stats { display: grid; grid-template-columns: repeat(4, 1fr); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
@media (max-width: 760px) { .sm-stats { grid-template-columns: repeat(2, 1fr); } }
.sm-stat { padding: 14px 18px; border-right: 1px solid var(--line); }
.sm-stat:last-child { border-right: 0; }
.sm-stat .v { font-size: 19px; font-weight: 650; letter-spacing: -.01em; font-variant-numeric: tabular-nums; }
.sm-stat .l { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); margin-top: 2px; }
.sm-stat .v.ok { color: var(--ok); }
.sm-stat .v.bad { color: var(--bad); }
.sm-stat .v.warn { color: var(--warn); }

/* ---------- Badges ---------- */
.sm-badge {
  display: inline-flex; align-items: center; gap: 5px; padding: 3px 9px; border-radius: 4px;
  font-size: 11.5px; font-weight: 600; letter-spacing: .005em; white-space: nowrap;
}
.sm-badge.ok { background: var(--ok-soft); color: var(--ok); }
.sm-badge.bad { background: var(--bad-soft); color: var(--bad); }
.sm-badge.warn { background: var(--warn-soft); color: var(--warn); }
.sm-badge.muted { background: var(--surface-tint); color: var(--muted); }

/* ---------- Comparison table ---------- */
.sm-table { width: 100%; border-collapse: collapse; font-size: 13px; table-layout: fixed; }
.sm-table thead th {
  text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: .085em;
  color: var(--muted); font-weight: 650; padding: 8px 12px; border-bottom: 1px solid var(--line-strong);
  background: var(--surface-alt);
}
.sm-table tbody td { padding: 13px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
.sm-table tbody tr:last-child td { border-bottom: 0; }
.sm-table .c-crit { font-weight: 600; color: var(--ink); }
.sm-table .c-crit .sub { font-weight: 400; color: var(--muted); font-size: 12px; display: block; margin-top: 3px; line-height: 1.45; }
.sm-table .c-val { font-variant-numeric: tabular-nums; }
.sm-table .c-val .k {
  display: inline-block; min-width: 42px; font-size: 10px; text-transform: uppercase;
  letter-spacing: .07em; color: var(--muted); font-weight: 600;
}
.sm-table .c-val div + div { margin-top: 6px; }
.sm-table .c-expl { font-size: 12.5px; line-height: 1.6; color: var(--ink-soft); }

.sm-evidence { margin-top: 5px; font-size: 11.5px; color: var(--muted); line-height: 1.5; }
.sm-evidence .pg {
  display: inline-block; font-weight: 600; color: var(--accent); background: var(--accent-soft);
  border-radius: 3px; padding: 1px 5px; margin-right: 5px; font-size: 10.5px;
}
.sm-evidence q { font-style: italic; quotes: '"' '"'; }

.sm-checks { margin: 8px 0 0; padding: 0; list-style: none; }
.sm-checks li { padding: 4px 0; border-top: 1px dashed var(--line); font-size: 11.5px; color: var(--muted); }
.sm-checks .lbl { color: var(--ink); font-weight: 600; margin-right: 6px; }
.sm-checks .tone { font-size: 9.5px; text-transform: uppercase; letter-spacing: .06em; margin-right: 6px; font-weight: 700; }
.sm-checks .tone.pass { color: var(--ok); }
.sm-checks .tone.fail { color: var(--bad); }
.sm-checks .tone.unknown { color: var(--warn); }
.sm-checks .note { display: block; font-style: italic; margin-top: 2px; }
.sm-src { font-size: 10.5px; color: #97A3AE; margin-top: 6px; }

/* ---------- Manufacturer header ---------- */
.sm-mfr { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; padding-bottom: 10px; border-bottom: 1.5px solid var(--ink); margin-top: 34px; }
.sm-mfr h2 { font-size: 17px; margin: 0; font-weight: 650; letter-spacing: -.01em; }
.sm-mfr .doc { font-size: 12px; color: var(--muted); margin: 3px 0 0; }
.sm-tally { display: flex; gap: 14px; font-size: 11.5px; font-weight: 600; white-space: nowrap; }
.sm-tally .ok { color: var(--ok); }
.sm-tally .bad { color: var(--bad); }
.sm-tally .warn { color: var(--warn); }

/* ---------- Callouts ---------- */
.sm-callout { border-left: 3px solid var(--accent); background: var(--accent-soft); padding: 12px 16px; border-radius: 0 5px 5px 0; font-size: 13px; color: var(--ink-soft); line-height: 1.6; }
.sm-callout.warn { border-color: #D9A33E; background: var(--warn-soft); color: #6C4A00; }
.sm-callout.bad { border-color: #C25A5A; background: var(--bad-soft); color: #7E2323; }
.sm-callout strong { color: inherit; }

/* ---------- Roadmap ---------- */
.sm-roadmap { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 900px) { .sm-roadmap { grid-template-columns: 1fr; } }
.sm-roadmap .sm-card { min-height: 172px; }
.sm-roadmap .tag { font-size: 10.5px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.sm-roadmap .tag.live { color: var(--ok); }
.sm-roadmap ul { margin: 10px 0 0; padding-left: 16px; font-size: 12.8px; color: var(--muted); line-height: 1.65; }

/* ---------- Doc list ---------- */
.sm-doclist { border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
.sm-docrow { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 11px 16px; border-bottom: 1px solid var(--line); font-size: 13px; }
.sm-docrow:last-child { border-bottom: 0; }
.sm-docrow .nm { font-weight: 500; }
.sm-docrow .meta { font-size: 11.5px; color: var(--muted); }

/* ---------- Quick start ---------- */
.sm-quick { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 0 0 20px; }
@media (max-width: 1080px) { .sm-quick { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 620px) { .sm-quick { grid-template-columns: 1fr; } }
.sm-quick .sm-card { padding: 16px 16px 14px; }
.sm-quick .tag {
  display: inline-block; font-size: 10px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--muted);
  background: var(--surface-tint); border-radius: 4px; padding: 2px 7px; margin-bottom: 9px;
}
.sm-quick .tag.ok { color: var(--ok); background: var(--ok-soft); }
.sm-quick .tag.bad { color: var(--bad); background: var(--bad-soft); }
.sm-quick h4 { font-size: 13.5px; font-weight: 650; margin: 0 0 5px; letter-spacing: -.005em; }
.sm-quick p { font-size: 12.4px; line-height: 1.55; color: var(--muted); margin: 0; }
.sm-quick .res {
  margin-top: 10px; padding-top: 9px; border-top: 1px solid var(--line);
  font-size: 11.5px; font-weight: 600; color: var(--ink-soft); font-variant-numeric: tabular-nums;
}
.sm-quick .res.ok { color: var(--ok); }
.sm-quick .res.bad { color: var(--bad); }

/* ---------- Streamlit widget polish ---------- */
.stButton > button {
  border-radius: 6px; font-weight: 600; font-size: 14px; padding: .55rem 1.15rem;
  border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink);
  transition: background .12s ease, border-color .12s ease;
}
.stButton > button:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-soft); }
.stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.stButton > button[kind="primary"]:hover, .stButton > button[data-testid="baseButton-primary"]:hover {
  background: var(--accent-dark); border-color: var(--accent-dark); color: #fff;
}
.stDownloadButton > button {
  border-radius: 6px; font-weight: 600; font-size: 13.5px;
  border: 1px solid var(--accent); background: var(--accent); color: #fff; padding: .5rem 1rem;
}
.stDownloadButton > button:hover { background: var(--accent-dark); border-color: var(--accent-dark); color: #fff; }
[data-testid="stFileUploader"] section {
  border: 1px dashed var(--line-strong); border-radius: var(--radius); background: var(--surface-alt);
  padding: 18px;
}
[data-testid="stFileUploader"] section:hover { border-color: var(--accent); background: var(--accent-soft); }
[data-testid="stFileUploader"] label { font-size: 13px; font-weight: 600; color: var(--ink); }
[data-testid="stFileUploaderDropzoneInstructions"] div { font-size: 12.5px; color: var(--muted); }
.stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
  border-radius: 6px; border-color: var(--line-strong); font-size: 13.5px;
}
.stProgress > div > div > div { background: var(--accent); }
[data-testid="stExpander"] { border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); }
[data-testid="stExpander"] summary { font-size: 13px; font-weight: 600; }
[data-testid="stSidebar"] { background: var(--surface-alt); border-right: 1px solid var(--line); }
.stMarkdown code { background: var(--surface-tint); border-radius: 4px; padding: 1px 5px; font-size: 12px; }
div[data-testid="stAlert"] { border-radius: 6px; font-size: 13px; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--line); }
.stTabs [data-baseweb="tab"] { font-size: 13px; font-weight: 600; padding: 8px 12px; }
.sm-foot { margin-top: 64px; padding-top: 16px; border-top: 1px solid var(--line); font-size: 11.5px; color: var(--muted); display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
</style>
"""


def markup(markup_html: str) -> str:
    """Prepare an HTML fragment for ``st.markdown(...unsafe_allow_html=True)``.

    Streamlit renders Markdown, so a blank line inside an HTML fragment ends the
    block and the following indented lines are shown as a code block. Removing
    whitespace-only lines and indentation makes any fragment safe to inject,
    including fragments with empty optional sections.
    """

    lines = [line.strip() for line in markup_html.splitlines()]
    return " ".join(line for line in lines if line)


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def configured() -> bool:
    from config import get_settings

    return get_settings().api_configured


def top_nav(active: str = "", show_status: bool = True) -> None:
    """Custom top bar. Streamlit's own navigation is hidden by CSS."""

    links = [
        ("Landing", "/", "home"),
        ("Sample analysis", "/sample_demo", "sample"),
        ("New analysis", "/new_analysis", "new"),
    ]
    items = []
    for label, href, key in links:
        cls = "active" if key == active else ""
        items.append(
            f'<a class="{cls}" href="{href}" target="_self">{escape(label)}</a>'
        )
    status = ""
    if show_status:
        on = configured()
        dot = "dot" if on else "dot off"
        text = "API connected" if on else "API key not set"
        status = f'<div class="sm-navmeta"><span class="{dot}"></span>{text}</div>'

    st.markdown(
        markup(
            f"""
        <div class="sm-nav">
          <a class="sm-brand" href="/" target="_self">
            <span class="sm-mark">SM</span>
            <span class="sm-wordmark">SpecMatch <span>AI</span></span>
          </a>
          <div class="sm-navlinks">{''.join(items)}</div>
          {status}
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def footer() -> None:
    from config import get_settings

    settings = get_settings()
    st.markdown(
        markup(
            f"""
        <div class="sm-foot">
          <span>SpecMatch AI · V1 portfolio demo · First-pass comparison assistant, not an engineering approval.</span>
          <span>{escape(settings.model)} via Deploy</span>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def section_head(title: str, note: str | None = None) -> None:
    note_html = f'<p class="sm-small" style="margin:0">{escape(note)}</p>' if note else ""
    st.markdown(
        f'<div class="sm-section-head"><h2 class="sm-h2">{escape(title)}</h2>{note_html}</div>',
        unsafe_allow_html=True,
    )


def eyebrow(text: str) -> None:
    st.markdown(f'<p class="sm-eyebrow">{escape(text)}</p>', unsafe_allow_html=True)


def h1(text: str) -> None:
    st.markdown(f'<h1 class="sm-h1">{escape(text)}</h1>', unsafe_allow_html=True)


def lead(text: str) -> None:
    st.markdown(f'<p class="sm-lead">{escape(text)}</p>', unsafe_allow_html=True)


def body(text: str) -> None:
    st.markdown(f'<p class="sm-body">{escape(text)}</p>', unsafe_allow_html=True)


def small(text: str) -> None:
    st.markdown(f'<p class="sm-small">{escape(text)}</p>', unsafe_allow_html=True)


def callout(text: str, tone: str = "info") -> None:
    cls = {"info": "", "warn": " warn", "bad": " bad"}.get(tone, "")
    st.markdown(f'<div class="sm-callout{cls}">{text}</div>', unsafe_allow_html=True)


def badge(status: str) -> str:
    mapping = {
        "compliant": ("ok", "Compliant"),
        "non_compliant": ("bad", "Non-compliant"),
        "unverified": ("warn", "Unverified"),
        "not_specified": ("muted", "Not specified"),
    }
    cls, label = mapping.get(status, ("muted", status))
    return f'<span class="sm-badge {cls}">{escape(label)}</span>'


def stat_strip(items: list[tuple[str, str, str]]) -> None:
    """items: (label, value, tone)"""

    cells = "".join(
        f'<div class="sm-stat"><div class="v {tone}">{escape(value)}</div>'
        f'<div class="l">{escape(label)}</div></div>'
        for label, value, tone in items
    )
    st.markdown(f'<div class="sm-stats">{cells}</div>', unsafe_allow_html=True)
