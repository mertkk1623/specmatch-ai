"""New analysis page: upload, validate, run, and hand off to results."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from config import (
    MAX_CATALOGUE_PAGES,
    MAX_SPEC_PAGES,
    MAX_UPLOAD_BYTES,
    get_settings,
)
from src.pipeline import AnalysisError, AnalysisInput, run_analysis
from src.ui import quickstart_panel, theme
from src.ui.results import disclaimer, download_button, manufacturer_block, requirements_table
from src.ui.results import results_header, parser_notes, validation_issues

st.set_page_config(
    page_title="New analysis · SpecMatch AI",
    page_icon="◧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

theme.inject_css()
theme.top_nav(active="new")

settings = get_settings()

theme.eyebrow("New analysis")
theme.h1("Compare a specification against manufacturer documents")
theme.lead(
    "Upload one project specification and up to two manufacturer catalogues or "
    "datasheets. Processing usually takes one to three minutes, depending on how many "
    "pages the PDFs contain."
)

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


def _reset() -> None:
    for key in ("analysis_result", "analysis_error", "analysis_inputs"):
        st.session_state.pop(key, None)


if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "analysis_error" not in st.session_state:
    st.session_state.analysis_error = None

# ---------------------------------------------------------------------------
# Quick start (also available without an API key)
# ---------------------------------------------------------------------------

result = st.session_state.analysis_result
if result is None:
    st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
    quickstart_panel.panel(inline_results=False, show_scenarios=False)
    st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Configuration guard
# ---------------------------------------------------------------------------

if result is None and not settings.api_configured:
    theme.callout(
        "<strong>No API key configured.</strong> Add <code>DEPLOY_API_KEY</code> to the "
        "<code>.env</code> file in the project root, then reload this page. The Quick "
        "Start demo and the sample analysis work without a key.",
        tone="bad",
    )
    with st.expander("How to configure the Deploy API key", expanded=True):
        st.markdown(
            "```bash\n"
            "# .env in the project root\n"
            "DEPLOY_API_KEY=your-deploy-api-key\n"
            "```\n"
            "The key is read from the environment only. It is never written to the "
            "repository, the report, or the session state."
        )
    theme.footer()
    st.stop()

# ---------------------------------------------------------------------------
# Existing result
# ---------------------------------------------------------------------------

result = st.session_state.analysis_result
if result is not None:
    if result.demo:
        theme.callout(
            "<strong>Quick Start demo loaded.</strong> This is the precomputed "
            "comparison of one synthetic specification and two synthetic manufacturer "
            "offers. It was produced by the real pipeline and needed no API call. "
            "Use <em>Start another analysis</em> to upload your own PDFs.",
            tone="warn",
        )
    else:
        theme.callout(
            f"<strong>Analysis complete.</strong> {len(result.manufacturers)} manufacturer "
            f"document(s) compared against <code>{result.spec.document_name}</code>.",
            tone="info",
        )
    top_left, top_right, _ = st.columns([0.32, 0.3, 0.38], gap="small")
    with top_left:
        download_button(result, key="download-live-report")
    with top_right:
        if st.button("Start another analysis", use_container_width=True):
            _reset()
            st.rerun()

    st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
    results_header(result, show_meta=True)

    tabs = st.tabs(["Comparison", "Extracted requirements", "Processing details"])
    with tabs[0]:
        for manufacturer in result.manufacturers:
            manufacturer_block(manufacturer)
    with tabs[1]:
        requirements_table(result)
        validation_issues(result)
    with tabs[2]:
        parser_notes(result)
        for manufacturer in result.manufacturers:
            st.markdown(
                f"**{manufacturer.name}** — `{manufacturer.document_name}`, "
                f"{manufacturer.document_meta.page_count} page(s), "
                f"{manufacturer.document_meta.tables_found} table(s), "
                f"parsed with {manufacturer.document_meta.parser}."
            )
            for warning in manufacturer.warnings:
                st.markdown(f"- {warning}")

    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    disclaimer()
    theme.footer()
    st.stop()

# ---------------------------------------------------------------------------
# Error state
# ---------------------------------------------------------------------------

if st.session_state.analysis_error:
    theme.callout(
        f"<strong>Analysis failed.</strong> {st.session_state.analysis_error}",
        tone="bad",
    )
    st.markdown(
        "Common causes: a scanned (image-only) PDF, a password-protected file, a "
        "document that is not about steel hollow sections, or a temporary API problem. "
        "The sample analysis shows what a successful run looks like."
    )

# ---------------------------------------------------------------------------
# Upload form
# ---------------------------------------------------------------------------

left, right = st.columns([0.62, 0.38], gap="large")

with left:
    theme.section_head("1 · Project specification")
    spec_file = st.file_uploader(
        "Specification PDF",
        type=["pdf"],
        accept_multiple_files=False,
        key="spec_upload",
        help="One technical specification PDF. Digital (text-based) PDFs work best.",
    )

    theme.section_head("2 · Manufacturer documents")
    theme.small("One or two catalogue/datasheet PDFs. Each document is compared separately.")
    mfr_cols = st.columns(2, gap="medium")
    with mfr_cols[0]:
        mfr_one = st.file_uploader(
            "Manufacturer A",
            type=["pdf"],
            key="mfr_a",
            help="Catalogue or datasheet PDF for the first supplier.",
        )
        name_one = st.text_input(
            "Display name (optional)",
            key="mfr_a_name",
            placeholder="e.g. Anadolu Profil",
        )
    with mfr_cols[1]:
        mfr_two = st.file_uploader(
            "Manufacturer B (optional)",
            type=["pdf"],
            key="mfr_b",
            help="A second supplier document, or leave empty.",
        )
        name_two = st.text_input(
            "Display name (optional)",
            key="mfr_b_name",
            placeholder="e.g. Ege Metal",
        )

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    uploads = [f for f in (spec_file, mfr_one, mfr_two) if f is not None]
    problems: list[str] = []
    for upload in uploads:
        if upload.size > MAX_UPLOAD_BYTES:
            problems.append(
                f"{upload.name} is {upload.size / 1024 / 1024:.1f} MB; the limit is "
                f"{MAX_UPLOAD_BYTES // 1024 // 1024} MB."
            )
    if problems:
        for problem in problems:
            theme.callout(problem, tone="bad")

    can_run = spec_file is not None and mfr_one is not None and not problems
    if not can_run:
        theme.small("Select a specification and at least one manufacturer document to continue.")

    if st.button(
        "Run analysis",
        type="primary",
        disabled=not can_run,
        use_container_width=False,
    ):
        progress_bar = st.progress(0.0, text="Preparing documents")
        status = st.empty()
        temp_files: list[Path] = []

        def progress(message: str, fraction: float) -> None:
            progress_bar.progress(min(max(fraction, 0.0), 1.0), text=message)
            status.caption(message)

        try:
            with tempfile.TemporaryDirectory(prefix="specmatch-") as workdir:
                work = Path(workdir)
                spec_path = work / "specification.pdf"
                spec_path.write_bytes(spec_file.getbuffer().tobytes())
                temp_files.append(spec_path)

                mfr_paths: list[Path] = []
                names: list[str] = []
                for index, (upload, name) in enumerate(
                    ((mfr_one, name_one), (mfr_two, name_two)), start=1
                ):
                    if upload is None:
                        continue
                    path = work / f"manufacturer_{index}.pdf"
                    path.write_bytes(upload.getbuffer().tobytes())
                    mfr_paths.append(path)
                    names.append((name or "").strip() or Path(upload.name).stem)

                data = AnalysisInput(
                    spec_path=str(spec_path),
                    manufacturer_paths=[str(p) for p in mfr_paths],
                    manufacturer_names=names,
                )

                st.session_state.analysis_inputs = {
                    "original_names": {
                        "spec": spec_file.name,
                        "manufacturers": [
                            upload.name
                            for upload in (mfr_one, mfr_two)
                            if upload is not None
                        ],
                    }
                }

                analysis = run_analysis(
                    data,
                    api_key=settings.api_key or "",
                    settings=settings,
                    enable_ai_explanations=True,
                    progress=progress,
                )

                original = st.session_state.analysis_inputs["original_names"]
                analysis.spec.document_name = original["spec"]
                analysis.spec.document_meta.filename = original["spec"]
                for manufacturer, original_name in zip(
                    analysis.manufacturers, original["manufacturers"]
                ):
                    manufacturer.document_name = original_name
                    manufacturer.document_meta.filename = original_name

                progress_bar.progress(1.0, text="Analysis complete")
                st.session_state.analysis_result = analysis
                st.session_state.analysis_error = None
                st.rerun()
        except AnalysisError as exc:
            st.session_state.analysis_error = str(exc)
            st.session_state.analysis_result = None
            st.rerun()
        except Exception as exc:  # noqa: BLE001 - never crash the page
            st.session_state.analysis_error = (
                f"Unexpected error while processing the documents ({type(exc).__name__})."
            )
            st.session_state.analysis_result = None
            st.rerun()
        finally:
            progress_bar.empty()
            status.empty()

with right:
    st.markdown(
        theme.markup(
            f"""
        <div class="sm-card flat">
          <p class="sm-eyebrow" style="margin-bottom:12px">Before you run</p>
          <h3 class="sm-h3">What works well</h3>
          <p>Digital PDF specifications and catalogue pages where the five fields are
          stated in text or a simple table. English documents are the primary target;
          German and Turkish standards designations are handled.</p>
          <hr class="sm-rule" style="margin:16px 0">
          <h3 class="sm-h3">Limits in V1</h3>
          <p>Scanned pages need OCR and are not supported. Complex multi-column
          catalogue matrices may leave a criterion unverified. Comparisons are nominal,
          without tolerance analysis.</p>
          <hr class="sm-rule" style="margin:16px 0">
          <h3 class="sm-h3">Processing</h3>
          <p>Up to {MAX_SPEC_PAGES} specification pages and {MAX_CATALOGUE_PAGES} catalogue
          pages. Large PDFs take longer because Docling performs layout and table analysis.</p>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    st.markdown(
        theme.markup(
            f"""
        <div class="sm-card">
          <h3 class="sm-h3">Model</h3>
          <p><code>{settings.model}</code><br>via Deploy · OpenAI-compatible Chat Completions</p>
          <p style="margin-top:10px">Statuses come from Python rules. The model extracts
          fields and writes explanations only.</p>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )

st.markdown('<div class="sm-section"></div>', unsafe_allow_html=True)
disclaimer()
theme.footer()
