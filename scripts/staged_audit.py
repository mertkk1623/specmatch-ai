"""Audit the staged Git index for secrets before committing.

Reads each staged blob exactly as Git would store it and searches for the real
Deploy API key and common credential patterns. Also lists any staged path that
should never be published.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_PATHS = {
    ".env", "opencode.json", ".streamlit/secrets.toml",
    ".DS_Store", "Thumbs.db",
}
FORBIDDEN_PREFIXES = (".venv/", "venv/", "__pycache__/", ".pytest_cache/", "docs/_capture/")

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "OpenAI-style token"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub PAT"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout


def real_key() -> str:
    env = ROOT / ".env"
    if not env.is_file():
        return ""
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.strip().startswith("DEPLOY_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main() -> int:
    findings: list[str] = []
    key = real_key()

    staged = [p for p in git("diff", "--cached", "--name-only").splitlines() if p.strip()]
    print(f"staged files: {len(staged)}")

    if not key:
        findings.append("Could not read DEPLOY_API_KEY from .env; cannot verify absence.")
    else:
        print(f"real key loaded, length {len(key)}")

    for rel in staged:
        norm = rel.replace("\\", "/")
        if norm in FORBIDDEN_PATHS:
            findings.append(f"forbidden path staged: {norm}")
        if norm.startswith(FORBIDDEN_PREFIXES):
            findings.append(f"forbidden directory staged: {norm}")

        try:
            blob = subprocess.run(
                ["git", "show", f":{norm}"],
                cwd=ROOT, capture_output=True, check=True,
            ).stdout
        except subprocess.CalledProcessError:
            findings.append(f"could not read staged blob: {norm}")
            continue

        if b"\x00" in blob[:8000]:
            continue  # binary (PDF/PNG); checked by hash below

        text = blob.decode("utf-8", errors="ignore")
        if key and key in text:
            findings.append(f"REAL API KEY IN STAGED BLOB: {norm}")
        for pattern, label in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(f"{label} in {norm}: {match.group(0)[:20]}...")

    # Binary files must not embed the key either.
    for rel in staged:
        norm = rel.replace("\\", "/")
        blob = subprocess.run(
            ["git", "show", f":{norm}"], cwd=ROOT, capture_output=True, check=True
        ).stdout
        if b"\x00" in blob[:8000] and key:
            if key.encode() in blob:
                findings.append(f"REAL API KEY IN BINARY BLOB: {norm}")

    print(f"findings: {len(findings)}")
    for item in findings:
        print(" -", item)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
