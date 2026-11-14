"""The Quick Start panel shown above the upload area.

Two entry points use the same panel:

* the landing page, where the demo results open inline on the page;
* the new-analysis page, where the demo result is loaded into the same session
  state key the normal upload flow uses, so the existing result view takes over.

Nothing in this module decides a compliance status. It reads a precomputed
result produced once by the real pipeline and renders it with the shared
results helpers, exactly like the sample analysis page.
"""

from __future__ import annotations

from html import escape

import streamlit as st

from src import quickstart
from src.ui import results as results_ui
from src.ui import theme

OPEN_KEY = "quickstart_demo_open"

TEMPLATES_ZIP = "specmatch-ai-templates.zip"
DATASET_ZIP = "specmatch-ai-quickstart-dataset.zip"


def _scenario_cards() -> None:
    cards = []
    for scenario in quickstart.SCENARIOS:
        cards.append(
            f"""
            <div class="sm-card">
              <span class="tag {scenario["tone"]}">{escape(scenario["tag"])}</span>
              <h4>{escape(scenario["title"])}</h4>
              <p>{escape(scenario["detail"])}</p>
              <div class="res {scenario["tone"]}">{escape(scenario["result"])}</div>
            </div>
            """
        )
    st.markdown(
        theme.markup(f'<div class="sm-quick">{"".join(cards)}</div>'),
        unsafe_allow_html=True,
    )


def _archive_button(
    label: str,
    builder,
    file_name: str,
    key: str,
    help_text: str,
) -> None:
    try:
        payload = builder()
    except quickstart.QuickStartUnavailable as exc:
        st.button(label, key=f"{key}-disabled", disabled=True, use_container_width=True)
        st.caption(str(exc))
        return
    st.download_button(
        label,
        data=payload,
        file_name=file_name,
        mime="application/zip",
        key=key,
        help=help_text,
        use_container_width=True,
    )


def _individual_downloads() -> None:
    with st.expander("Download files one by one", expanded=False):
        st.markdown(
            '<p class="sm-small" style="margin-bottom:10px">'
            "The blank templates are PDFs. The field guide is a CSV that documents "
            "the five fields and their rules; the application reads PDFs, not CSV.</p>",
            unsafe_allow_html=True,
        )
        cols = st.columns(3, gap="small")
        for column, (label, filename, description) in zip(
            cols, quickstart.TEMPLATE_FILES
        ):
            path = quickstart.template_path(filename)
            with column:
                if not path.exists():
                    st.caption(f"{label}: not generated")
                    continue
                st.download_button(
                    f"📄 {label}",
                    data=path.read_bytes(),
                    file_name=filename,
                    mime="text/csv" if filename.endswith(".csv") else "application/pdf",
                    key=f"qs-template-{filename}",
                    help=description,
                    use_container_width=True,
                )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.markdown(
            '<p class="sm-small" style="margin-bottom:10px">'
            "The three sample PDFs, in the order they are compared.</p>",
            unsafe_allow_html=True,
        )
        doc_cols = st.columns(3, gap="small")
        for column, (role, filename, description) in zip(
            doc_cols, quickstart.QUICKSTART_DOCUMENTS
        ):
            path = quickstart.document_path(filename)
            with column:
                if not path.exists():
                    st.caption(f"{role}: not generated")
                    continue
                st.download_button(
                    f"📄 {role}",
                    data=path.read_bytes(),
                    file_name=filename,
                    mime="application/pdf",
                    key=f"qs-doc-{filename}",
                    help=description,
                    use_container_width=True,
                )


def _demo_results(result) -> None:
    """Render the precomputed comparison inline (landing page only)."""

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    theme.callout(
        "<strong>Demonstration result.</strong> These are synthetic documents created "
        "for this project. The numbers below came from the real pipeline — Docling "
        "parsing, DeepSeek extraction, deterministic Python comparison — but they are "
        "stored, so this view makes no API call and needs no key. Statuses are decided "
        "by Python rules, never by the model.",
        tone="warn",
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    head_left, head_right = st.columns([0.7, 0.3], gap="medium")
    with head_left:
        st.markdown(
            '<h3 class="sm-h3" style="font-size:17px">Comparison results</h3>',
            unsafe_allow_html=True,
        )
    with head_right:
        results_ui.download_button(result, key="download-quickstart-report")

    results_ui.results_header(result, show_meta=True)

    for manufacturer in result.manufacturers:
        results_ui.manufacturer_block(manufacturer)

    with st.expander("Extracted project requirements", expanded=False):
        results_ui.requirements_table(result)
    results_ui.validation_issues(result)
    results_ui.parser_notes(result)
    results_ui.disclaimer()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    close_left, _ = st.columns([0.28, 0.72], gap="small")
    with close_left:
        if st.button("Close demo results", use_container_width=True):
            st.session_state[OPEN_KEY] = False
            st.rerun()


def panel(*, inline_results: bool = True, show_scenarios: bool = True) -> None:
    """Draw the Quick Start section.

    ``inline_results`` is true on the landing page, where the result is shown
    right below the panel. On the new-analysis page the result is loaded into
    ``analysis_result`` and the page's own result view renders it.

    ``show_scenarios`` is turned off on the new-analysis page, where the panel
    sits directly above the upload form and should stay short.
    """

    theme.eyebrow("Quick start & demo data")
    theme.section_head(
        "Test the comparison without preparing a single file",
        "One click opens a finished comparison. The other two buttons give you a blank "
        "template and the sample dataset behind it.",
    )

    if show_scenarios:
        _scenario_cards()

    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        if st.button(
            "🚀 Load the demo comparison",
            type="primary",
            key="qs-load-demo",
            help=(
                "Loads the precomputed comparison of one specification and two "
                "manufacturer offers. No upload, no API key, no waiting."
            ),
            use_container_width=True,
        ):
            try:
                result = quickstart.load_result()
            except quickstart.QuickStartUnavailable as exc:
                theme.callout(str(exc), tone="bad")
            else:
                if inline_results:
                    st.session_state[OPEN_KEY] = True
                else:
                    st.session_state.analysis_result = result
                    st.session_state.analysis_error = None
                    st.rerun()
    with c2:
        _archive_button(
            "📥 Blank templates",
            quickstart.templates_archive,
            TEMPLATES_ZIP,
            key="qs-download-templates",
            help_text=(
                "ZIP with the blank specification PDF, the blank manufacturer PDF and "
                "the field guide."
            ),
        )
    with c3:
        _archive_button(
            "📊 Sample dataset",
            quickstart.dataset_archive,
            DATASET_ZIP,
            key="qs-download-dataset",
            help_text=(
                "ZIP with the three sample PDFs and a short readme. Upload them on the "
                "New analysis page to run the comparison yourself."
            ),
        )

    theme.small(
        "The demo result is a stored run of the real pipeline, so the four scenarios "
        "reproduce exactly. There is no numeric matching score in V1: each criterion "
        "gets a status, every value keeps its page and verbatim excerpt, and missing "
        "information stays unverified rather than being assumed."
    )

    _individual_downloads()

    if inline_results and st.session_state.get(OPEN_KEY):
        try:
            result = quickstart.load_result()
        except quickstart.QuickStartUnavailable as exc:
            theme.callout(str(exc), tone="bad")
        else:
            _demo_results(result)
