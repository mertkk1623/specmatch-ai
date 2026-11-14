"""SpecMatch AI — application shell and landing page.

Run:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from config import get_settings
from src.demo import DEMO_DOCUMENTS, demo_available, demo_document_path
from src.ui import theme

st.set_page_config(
    page_title="SpecMatch AI — Technical specification comparison",
    page_icon="◧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

theme.inject_css()
theme.top_nav(active="home")

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

left, right = st.columns([1.25, 0.75], gap="large")

with left:
    theme.eyebrow("Construction procurement · technical office")
    theme.h1("Check a manufacturer datasheet against the specification, before it reaches the tender file.")
    theme.lead(
        "SpecMatch AI reads one project specification and up to two manufacturer "
        "catalogues, extracts the five measurable requirements for galvanized square "
        "steel hollow sections, and shows exactly where the offer complies, conflicts, "
        "or cannot be verified — with the page it came from."
    )
    cta1, cta2, _ = st.columns([1.05, 1.05, 0.9], gap="small")
    with cta1:
        if st.button("Start a new analysis", type="primary", use_container_width=True):
            st.switch_page("pages/new_analysis.py")
    with cta2:
        if st.button("Open sample analysis", use_container_width=True):
            st.switch_page("pages/sample_demo.py")
    theme.small(
        "Sample analysis opens instantly with precomputed results and needs no API key."
    )

with right:
    st.markdown(
        theme.markup(
            """
        <div class="sm-card flat" style="margin-top:6px">
          <p class="sm-eyebrow" style="margin-bottom:12px">V1 comparison scope</p>
          <div class="sm-doclist" style="background:#fff">
            <div class="sm-docrow"><span class="nm">Profile dimensions</span><span class="meta">e.g. 40 × 40 mm</span></div>
            <div class="sm-docrow"><span class="nm">Wall thickness</span><span class="meta">nominal / min</span></div>
            <div class="sm-docrow"><span class="nm">Material grade</span><span class="meta">S235JRH</span></div>
            <div class="sm-docrow"><span class="nm">Galvanizing / coating</span><span class="meta">EN ISO 1461</span></div>
            <div class="sm-docrow"><span class="nm">Applicable standard</span><span class="meta">EN 10219</span></div>
          </div>
          <p class="sm-small" style="margin-top:14px;margin-bottom:0">
            One specification PDF and up to two manufacturer PDFs per analysis.
            Statuses are decided by deterministic Python rules, never by the language model.
          </p>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )

# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head("How it works", "Three steps, no configuration.")

st.markdown(
    theme.markup(
        """
    <div class="sm-card-grid">
      <div class="sm-card">
        <span class="sm-step-num">01</span>
        <h3 class="sm-h3">Upload</h3>
        <p>Add the project specification and one or two manufacturer catalogues or datasheets as PDF files.</p>
      </div>
      <div class="sm-card">
        <span class="sm-step-num">02</span>
        <h3 class="sm-h3">Compare</h3>
        <p>Documents are parsed page by page. DeepSeek extracts the five technical fields; Python evaluates them against explicit rules.</p>
      </div>
      <div class="sm-card">
        <span class="sm-step-num">03</span>
        <h3 class="sm-h3">Review evidence</h3>
        <p>Every value is shown with its page reference and a short explanation. Unclear or missing data stays unverified.</p>
      </div>
    </div>
    """
    ),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sample documents
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head(
    "Sample documents",
    "Synthetic demonstration files, clearly labelled as demo data.",
)

rows = []
for role, filename, description in DEMO_DOCUMENTS:
    rows.append(
        f'<div class="sm-docrow"><div><span class="nm">{role}</span>'
        f'<span class="meta" style="display:block">{description}</span></div>'
        f'<span class="meta">{filename}</span></div>'
    )
st.markdown(f'<div class="sm-doclist">{"".join(rows)}</div>', unsafe_allow_html=True)

dl1, dl2, dl3, _ = st.columns([1, 1, 1, 2.4], gap="small")

for column, (role, filename, _desc) in zip((dl1, dl2, dl3), DEMO_DOCUMENTS):
    path = demo_document_path(filename)
    with column:
        if path.exists():
            st.download_button(
                "Download PDF",
                data=path.read_bytes(),
                file_name=filename,
                mime="application/pdf",
                key=f"dl-{filename}",
                use_container_width=True,
                help=f"Download {role.lower()}: {filename}",
            )
        else:
            st.caption("Not generated")

if not demo_available():
    theme.callout(
        "The sample analysis file has not been generated yet. "
        "Run <code>python scripts/build_demo_analysis.py</code> to create it.",
        tone="warn",
    )

# ---------------------------------------------------------------------------
# Why the separation matters
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head("Designed around auditability")

col_a, col_b, col_c = st.columns(3, gap="large")
with col_a:
    st.markdown('<h3 class="sm-h3">The model extracts, it does not judge</h3>', unsafe_allow_html=True)
    theme.body(
        "DeepSeek returns structured fields with page references. Compliance is "
        "computed by explicit Python rules, so the same documents always produce "
        "the same statuses."
    )
with col_b:
    st.markdown('<h3 class="sm-h3">Missing is never compliant</h3>', unsafe_allow_html=True)
    theme.body(
        "If a catalogue does not state a value, or states it in a unit outside the "
        "tested conversion rules, the criterion is marked unverified — not accepted."
    )
with col_c:
    st.markdown('<h3 class="sm-h3">Evidence is checked</h3>', unsafe_allow_html=True)
    theme.body(
        "Every excerpt the model cites is verified against the parsed page text. "
        "References that cannot be found are removed and reported, never displayed."
    )

# ---------------------------------------------------------------------------
# Roadmap
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head("Roadmap", "Only V1 is implemented. V2 and V3 are planned.")

st.markdown(
    theme.markup(
        """
    <div class="sm-roadmap">
      <div class="sm-card">
        <span class="tag live">V1 · Available now</span>
        <ul>
          <li>Galvanized square steel hollow sections</li>
          <li>Five comparison criteria</li>
          <li>One specification + up to two catalogues</li>
          <li>Compliant / non-compliant / unverified</li>
          <li>Page-level evidence and HTML report</li>
        </ul>
      </div>
      <div class="sm-card">
        <span class="tag">V2 · Planned</span>
        <ul>
          <li>More profile sizes and variants</li>
          <li>Better extraction from complex catalogue tables</li>
          <li>Tolerance-aware dimension comparison</li>
          <li>Stronger evidence and confidence handling</li>
        </ul>
      </div>
      <div class="sm-card">
        <span class="tag">V3 · Planned</span>
        <ul>
          <li>Additional steel product families</li>
          <li>Cross-document technical Q&amp;A</li>
          <li>Alternative product comparison</li>
          <li>Broader standards coverage</li>
        </ul>
      </div>
    </div>
    """
    ),
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Scope + CTA
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head("What V1 does not do")
theme.body(
    "No supplier discovery or web crawling, no RFQ generation, no ERP or purchase "
    "order integration, no user accounts or payments, and no engineering approval "
    "or certification. It compares one product family against one specification at a time."
)

settings = get_settings()
st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
if not settings.api_configured:
    theme.callout(
        "<strong>API key not configured.</strong> The sample analysis still works. "
        "To run a new analysis, add <code>DEPLOY_API_KEY</code> to your <code>.env</code> file.",
        tone="warn",
    )

theme.footer()
