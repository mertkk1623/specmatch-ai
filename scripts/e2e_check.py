"""End-to-end workflow test through the browser UI.

Uploads the three demo PDFs to the running app, runs the real analysis, verifies
the results table and downloads the report. This is the manual verification step
required before capturing documentation screenshots.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8531"
OUT = ROOT / "docs" / "screenshots"
DOCS = ROOT / "sample_docs"


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 950}, device_scale_factor=2)
        page.set_default_timeout(60_000)

        page.goto(BASE + "/new_analysis", wait_until="networkidle")
        page.wait_for_timeout(2000)

        inputs = page.locator('input[type="file"]')
        print("uploaders:", inputs.count())
        assert inputs.count() >= 3

        inputs.nth(0).set_input_files(str(DOCS / "demo_specification.pdf"))
        page.wait_for_timeout(2500)
        inputs = page.locator('input[type="file"]')
        inputs.nth(1).set_input_files(str(DOCS / "demo_manufacturer_a.pdf"))
        page.wait_for_timeout(2500)
        inputs = page.locator('input[type="file"]')
        inputs.nth(2).set_input_files(str(DOCS / "demo_manufacturer_b.pdf"))
        page.wait_for_timeout(2500)

        names = page.locator('input[type="text"]')
        print("text inputs:", names.count())
        names.nth(0).fill("Anadolu Profil")
        names.nth(1).fill("Ege Metal")
        page.wait_for_timeout(1200)

        page.screenshot(path=str(OUT / "_e2e-upload.png"))
        print("upload screenshot captured")

        run = page.get_by_role("button", name="Run analysis")
        run.wait_for(state="visible")
        print("run enabled:", run.is_enabled())
        assert run.is_enabled()
        run.click()

        # Wait for the results view (download button appears only on success).
        print("waiting for analysis …")
        page.get_by_role("button", name="Download comparison report (HTML)").wait_for(
            state="visible", timeout=600_000
        )
        page.wait_for_timeout(2500)
        body = page.inner_text("body")
        print("has Ege Metal:", "Ege Metal" in body)
        print("has Anadolu:", "Anadolu Profil" in body)
        print("error visible:", "Analysis failed" in body)
        page.screenshot(path=str(OUT / "_e2e-result-top.png"))

        # Comparison table region
        page.evaluate(
            """() => { const e = document.querySelector('[data-testid="stMain"]'); if (e) e.scrollTop = 1250; }"""
        )
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "_e2e-result-table.png"))
        page.evaluate(
            """() => { const e = document.querySelector('[data-testid="stMain"]'); if (e) e.scrollTop = 2400; }"""
        )
        page.wait_for_timeout(900)
        page.screenshot(path=str(OUT / "_e2e-result-table2.png"))

        # Download the report through the UI.
        with page.expect_download() as dl_info:
            page.get_by_role("button", name="Download comparison report (HTML)").click()
        download = dl_info.value
        target = ROOT / "docs" / "_capture" / "downloaded-report.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(target))
        print("downloaded:", download.suggested_filename, target.stat().st_size, "bytes")
        print("OK")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
