"""Sample demo page: a precomputed analysis with no API call."""

from __future__ import annotations

import streamlit as st

from config import get_settings
from src.demo import (
    DEMO_DOCUMENTS,
    DemoUnavailable,
    demo_available,
    demo_document_path,
    demo_report_path,
    load_demo_result,
)
from src.ui import results as results_ui
from src.ui import theme

st.set_page_config(
    page_title="Sample analysis · SpecMatch AI",
    page_icon="◧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

theme.inject_css()
theme.top_nav(active="sample")

theme.eyebrow("Sample analysis")
theme.h1("A worked comparison, no upload required")
theme.lead(
    "This page shows a completed analysis of one synthetic project specification and "
    "two synthetic manufacturer catalogues. The results were produced once by the real "
    "pipeline and are stored, so opening this page makes no API call."
)

theme.callout(
    "<strong>Demonstration data.</strong> All three documents on this page are synthetic "
    "files created for this portfolio project. They do not describe a real project, a "
    "real supplier, or a real product. The comparison logic is the same code path used "
    "for uploaded documents.",
    tone="warn",
)

# ---------------------------------------------------------------------------
# Documents in this analysis
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head("Documents in this analysis")

doc_cols = st.columns(3, gap="medium")
for column, (role, filename, description) in zip(doc_cols, DEMO_DOCUMENTS):
    path = demo_document_path(filename)
    with column:
        size_kb = f"{path.stat().st_size / 1024:.0f} KB" if path.exists() else "missing"
        st.markdown(
            theme.markup(
                f"""
            <div class="sm-card" style="min-height:150px">
              <p class="sm-eyebrow" style="margin-bottom:8px">{role}</p>
              <h3 class="sm-h3">{filename}</h3>
              <p>{description}</p>
              <p class="sm-small" style="margin-top:10px;margin-bottom:0">{size_kb} · PDF</p>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )

if not demo_available():
    theme.callout(
        "The precomputed analysis file is missing. Run "
        "<code>python scripts/build_demo_analysis.py</code> to generate it.",
        tone="bad",
    )
    theme.footer()
    st.stop()

try:
    result = load_demo_result()
except DemoUnavailable as exc:
    theme.callout(str(exc), tone="bad")
    theme.footer()
    st.stop()

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
head_left, head_right = st.columns([0.72, 0.28], gap="medium")
with head_left:
    theme.section_head("Comparison results")
with head_right:
    results_ui.download_button(result, key="download-demo-report")

results_ui.results_header(result, show_meta=True)

for manufacturer in result.manufacturers:
    results_ui.manufacturer_block(manufacturer)

# ---------------------------------------------------------------------------
# Extracted requirements
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head(
    "Extracted project requirements",
    "Values as printed in the specification, with the page they came from.",
)
results_ui.requirements_table(result)

results_ui.validation_issues(result)
results_ui.parser_notes(result)

# ---------------------------------------------------------------------------
# Reading guide
# ---------------------------------------------------------------------------

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
theme.section_head("How to read this comparison")

st.markdown(
    theme.markup(
        """
    <div class="sm-card-grid">
      <div class="sm-card">
        <h3 class="sm-h3">Compliant</h3>
        <p>Available evidence meets the stated requirement, and every required sub-check passed.</p>
      </div>
      <div class="sm-card">
        <h3 class="sm-h3">Non-compliant</h3>
        <p>The available evidence clearly conflicts with the requirement — a different size, grade, standard or coating.</p>
      </div>
      <div class="sm-card">
        <h3 class="sm-h3">Unverified</h3>
        <p>Information is missing, ambiguous, or cannot be compared with the tested conversion rules. Never treated as compliant.</p>
      </div>
    </div>
    """
    ),
    unsafe_allow_html=True,
)

st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
results_ui.disclaimer()

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
settings = get_settings()
c1, c2, _ = st.columns([1, 1, 2], gap="small")
with c1:
    if st.button("Run your own analysis", type="primary", use_container_width=True):
        st.switch_page("pages/new_analysis.py")
with c2:
    if st.button("Back to landing page", use_container_width=True):
        st.switch_page("app.py")

theme.footer()
