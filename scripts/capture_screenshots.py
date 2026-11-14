"""Capture documentation screenshots from the running application.

Streamlit keeps its content inside a fixed-height internal scroller, so a
"full page" screenshot would only capture the viewport. Each capture therefore
expands the scroll container, resizes the viewport to the full content height,
and then crops the region that documents the state. All images come from the
real application.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8531"
OUT = ROOT / "docs" / "screenshots"
SCALE = 2
WIDTH = 1440

EXPAND_CSS = """
[data-testid="stAppViewContainer"], [data-testid="stMain"], section.main, .main {
  height: auto !important; overflow: visible !important; max-height: none !important;
}
[data-testid="stAppViewContainer"] { display: block !important; }
"""


def open_tall(page, path: str) -> int:
    """Navigate, expand the scroll container, and grow the viewport to fit."""

    page.set_viewport_size({"width": WIDTH, "height": 1000})
    page.goto(BASE + path, wait_until="networkidle")
    page.wait_for_timeout(2500)
    page.add_style_tag(content=EXPAND_CSS)
    page.wait_for_timeout(800)
    height = page.evaluate(
        """() => {
        const main = document.querySelector('[data-testid="stMain"]');
        const content = document.querySelector('.block-container');
        return Math.ceil(Math.max(
          main ? main.scrollHeight : 0,
          content ? content.getBoundingClientRect().bottom : 0
        ));
        }"""
    )
    height = min(int(height) + 8, 16000)
    page.set_viewport_size({"width": WIDTH, "height": height})
    page.wait_for_timeout(900)
    return height


def box_of(page, class_name: str, occurrence: int = 0) -> tuple[int, int, int, int]:
    box = page.evaluate(
        """([cls, index]) => {
        const els = document.querySelectorAll(cls);
        const el = els[index];
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { top: r.top, height: r.height, left: r.left, width: r.width };
        }""",
        [class_name, occurrence],
    )
    if not box:
        raise RuntimeError(f"element not found: {class_name}[{occurrence}]")
    return (
        int(box["left"]),
        int(box["top"]),
        int(box["left"] + box["width"]),
        int(box["top"] + box["height"]),
    )


def crop(source: Path, box: tuple[int, int, int, int], target: Path) -> None:
    from PIL import Image

    with Image.open(source) as image:
        left, top, right, bottom = (
            max(0, int(box[0] * SCALE)),
            max(0, int(box[1] * SCALE)),
            int(box[2] * SCALE),
            int(box[3] * SCALE),
        )
        bottom = min(bottom, image.height)
        right = min(right, image.width)
        if bottom <= top or right <= left:
            raise ValueError(f"empty crop for {target.name}: {box}")
        image.crop((left, top, right, bottom)).save(target)


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / "_raw"
    raw.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": 1000}, device_scale_factor=SCALE)
        page.set_default_timeout(90_000)

        # 01 — Landing page
        open_tall(page, "/")
        page.screenshot(path=str(OUT / "01-landing-page.png"))
        print("01 landing page")

        # 02 — Sample demo: framing, demo disclosure, documents, result summary
        open_tall(page, "/sample_demo")
        shot = raw / "sample_demo.png"
        page.screenshot(path=str(shot))
        summary = box_of(page, ".sm-callout", 1)
        crop(shot, (110, 0, WIDTH - 110, summary[3] + 48), OUT / "02-sample-demo.png")
        print("02 sample demo")

        # 03 — New analysis upload form
        open_tall(page, "/new_analysis")
        page.screenshot(path=str(OUT / "03-document-upload.png"))
        print("03 document upload")

        # 04 — Comparison results: second manufacturer block (all three statuses)
        open_tall(page, "/sample_demo")
        shot = raw / "sample_demo.png"
        page.screenshot(path=str(shot))
        header = box_of(page, ".sm-mfr", 1)
        table = box_of(page, "table.sm-table", 1)
        crop(shot, (110, header[1] - 24, WIDTH - 110, table[3] + 24), OUT / "04-comparison-results.png")
        print("04 comparison results")

        # 05 — Report preview: the generated HTML report
        report = ROOT / "sample_docs" / "precomputed" / "demo_report.html"
        page.set_viewport_size({"width": 1280, "height": 1200})
        page.goto("file:///" + report.as_posix())
        page.wait_for_timeout(800)
        height = min(page.evaluate("document.documentElement.scrollHeight") + 4, 16000)
        page.set_viewport_size({"width": 1280, "height": int(height)})
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / "05-report-preview.png"))
        print("05 report preview")

        browser.close()

    for leftover in raw.glob("*.png"):
        leftover.unlink()
    raw.rmdir()
    (ROOT / "scripts" / "debug_capture.py").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
