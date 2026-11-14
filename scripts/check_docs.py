"""Verify markdown links, image paths, and in-page anchors in the READMEs."""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def github_slug(text: str) -> str:
    """Approximate GitHub's heading slugger (keeps unicode letters)."""

    text = text.strip().lower()
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = text.replace("_", "-")
    return re.sub(r"\s+", "-", text).strip("-")


def headings(markdown: str) -> set[str]:
    found = set()
    in_fence = False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            found.add(github_slug(m.group(2)))
    return found


def main() -> int:
    problems: list[str] = []
    for name in ("README.md", "README.tr.md"):
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        anchors = headings(text)

        for match in re.finditer(r"!?\[[^\]]*\]\(([^)\s]+)\)", text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            if target.startswith("#"):
                slug = target[1:]
                if slug not in anchors:
                    problems.append(f"{name}: missing anchor {target}")
                continue
            local = (ROOT / target.split("#")[0]).resolve()
            if not local.is_file():
                problems.append(f"{name}: missing file {target}")

        # Screenshot count and order
        images = re.findall(r"!\[[^\]]*\]\((docs/screenshots/[^)]+)\)", text)
        expected = [
            "docs/screenshots/01-landing-page.png",
            "docs/screenshots/02-sample-demo.png",
            "docs/screenshots/03-document-upload.png",
            "docs/screenshots/04-comparison-results.png",
            "docs/screenshots/05-report-preview.png",
        ]
        if images != expected:
            problems.append(f"{name}: screenshot order/set is {images}")

        # Language switch must be in the first lines
        head = "\n".join(text.splitlines()[:6])
        other = "README.tr.md" if name == "README.md" else "README.md"
        if f"({other})" not in head:
            problems.append(f"{name}: language switch to {other} not at top")

        # Secrets and local absolute paths
        for pattern, label in (
            (r"DEPLOY_API_KEY\s*=\s*(?!your-deploy-api-key-here)[A-Za-z0-9_\-]{8,}", "real-looking API key"),
            (r"[A-Za-z]:\\\\", "drive path"),
            (r"/Users/|/home/", "posix home path"),
            (r"sk-[A-Za-z0-9]{10,}", "sk- token"),
        ):
            for hit in re.finditer(pattern, text):
                problems.append(f"{name}: suspicious {label}: {hit.group(0)[:40]}")

        # Placeholder must be present
        if "your-deploy-api-key-here" not in text:
            problems.append(f"{name}: .env placeholder missing")

        # Roadmap labels
        for label in ("Planned", "Planlanıyor"):
            pass
        if "V2" not in text or "V3" not in text:
            problems.append(f"{name}: roadmap versions missing")

        # Encoding sanity: no replacement characters on disk
        if "\ufffd" in text:
            problems.append(f"{name}: contains U+FFFD replacement characters")

        # NFC check for the Turkish file
        if name == "README.tr.md" and unicodedata.normalize("NFC", text) != text:
            problems.append(f"{name}: not NFC-normalized")

    print(f"checked 2 files, {len(problems)} problem(s)")
    for item in problems:
        print(" -", item)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
