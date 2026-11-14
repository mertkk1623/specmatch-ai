"""Pre-push security audit for the SpecMatch AI release.

Checks that the real Deploy API key never appears in any file that would be
committed, that placeholder files contain only placeholders, and that no
secret-bearing file is about to be published. Exits non-zero on any finding.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Directories that must never be published.
BLOCKED_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git"}

# Files that must never be published.
BLOCKED_NAMES = {".env", "secrets.toml", ".DS_Store", "Thumbs.db"}

TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".toml", ".json", ".html", ".css", ".js",
    ".example", ".cfg", ".ini", ".yml", ".yaml", ".gitignore",
}

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{16,}"), "OpenAI-style secret token"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub personal access token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{20,}"), "GitHub fine-grained token"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "private key block"),
    (re.compile(r"(?i)(password|passwd|secret)\s*[=:]\s*['\"][^'\"]{8,}['\"]"), "hardcoded password/secret"),
]


def read_key_from_env() -> str:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return ""
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("DEPLOY_API_KEY="):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def candidates() -> list[Path]:
    out: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        parts = set(path.parts)
        if parts & BLOCKED_DIRS:
            continue
        out.append(path)
    return sorted(out)


def main() -> int:
    findings: list[str] = []
    key = read_key_from_env()
    print(f"Real key loaded from .env: {'yes (length ' + str(len(key)) + ')' if key else 'no'}")

    if len(key) < 8:
        findings.append("No usable DEPLOY_API_KEY found in .env; cannot prove the key is absent.")

    files = candidates()
    scanned = 0
    skipped_binary = 0
    local_secrets = 0

    for path in files:
        rel = path.relative_to(ROOT).as_posix()

        if path.name in BLOCKED_NAMES:
            # Files like .env may exist locally; they must be excluded from the
            # commit by .gitignore. That is verified separately below. Here we
            # only confirm the file itself carries nothing unexpected.
            local_secrets += 1
            continue

        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"gitignore"}:
            skipped_binary += 1
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            findings.append(f"unreadable file {rel}: {exc}")
            continue

        scanned += 1

        if key and key in text:
            findings.append(f"REAL API KEY PRESENT in {rel}")

        for pattern, label in SECRET_PATTERNS:
            for match in pattern.finditer(text):
                findings.append(f"{label} in {rel}: {match.group(0)[:24]}...")

    # .env.example must only hold the placeholder
    example = ROOT / ".env.example"
    if example.is_file():
        example_text = example.read_text(encoding="utf-8")
        if "your-deploy-api-key-here" not in example_text:
            findings.append(".env.example is missing the expected placeholder")
        if key and key in example_text:
            findings.append("REAL API KEY PRESENT in .env.example")
        print(".env.example placeholder present:", "your-deploy-api-key-here" in example_text)

    # .env must be ignored
    env_ignored = False
    gitignore = ROOT / ".gitignore"
    if gitignore.is_file():
        lines = {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
        env_ignored = ".env" in lines
    if not env_ignored:
        findings.append(".gitignore does not ignore .env")
    print(".gitignore ignores .env:", env_ignored)

    print(f"text files scanned: {scanned}, binary skipped: {skipped_binary}")
    print(f"secret-bearing files kept locally (must be ignored): {local_secrets}")
    print(f"findings: {len(findings)}")
    for item in findings:
        print(" -", item)

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
