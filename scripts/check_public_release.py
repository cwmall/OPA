"""Fail closed on common public-release leaks and unsafe repository artifacts."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
MAX_GITHUB_FILE_BYTES = 100_000_000
SKIPPED_DIRECTORY_NAMES = {".git", ".venv", "venv", "__pycache__"}
FORBIDDEN_DIRECTORY_NAMES = {
    ".codex_tmp",
    "logs",
    "outputs",
    "reports",
    "quarantine",
    "secrets",
    "private",
    "admin-packages",
}
FORBIDDEN_SUFFIXES = {
    ".pyc", ".pyo", ".zip", ".7z", ".rar", ".docx", ".xlsx",
    ".pptx", ".p12", ".pfx", ".key", ".pem", ".opa-admin",
}
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".csv", ".svg", ".vbs", ".cmd", ".ps1",
}
GENERIC_SECRET_PATTERNS = (
    ("hard-coded Windows user path", re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.I)),
    ("private key block", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY", re.I)),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("hard-coded password", re.compile(r"(?im)^\s*(?:admin_)?password\s*=\s*['\"][^'\"]+['\"]")),
)


def iter_public_files():
    for path in ROOT.rglob("*"):
        if any(part in SKIPPED_DIRECTORY_NAMES for part in path.parts):
            continue
        if path.is_file():
            yield path


def load_external_denylist(path: str | None) -> tuple[str, ...]:
    if not path:
        return ()
    source = Path(path).expanduser().resolve()
    entries = []
    for line in source.read_text(encoding="utf-8").splitlines():
        value = line.strip().casefold()
        if value and not value.startswith("#"):
            entries.append(value)
    return tuple(entries)


def scan(denylist: tuple[str, ...]) -> list[str]:
    problems: list[str] = []
    for directory in ROOT.rglob("*"):
        if any(
            part in SKIPPED_DIRECTORY_NAMES
            for part in directory.relative_to(ROOT).parts
        ):
            continue
        if directory.is_dir() and directory.name.casefold() in FORBIDDEN_DIRECTORY_NAMES:
            problems.append(f"forbidden generated/private directory: {directory.relative_to(ROOT)}")
    for path in iter_public_files():
        relative = path.relative_to(ROOT)
        size = path.stat().st_size
        if size >= MAX_GITHUB_FILE_BYTES:
            problems.append(f"GitHub file-size limit: {relative} ({size} bytes)")
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            problems.append(f"forbidden release file type: {relative}")
        if path.name.casefold() in {"opa_config.json", "admin_enrollment.json"}:
            problems.append(f"forbidden live state file: {relative}")
        if path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        for label, pattern in GENERIC_SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{label}: {relative}")
        folded = text.casefold()
        for term in denylist:
            if term in folded:
                problems.append(f"external denylist match in {relative}")
                break
    return sorted(set(problems))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--denylist",
        default=os.environ.get("OPA_PRIVATE_DENYLIST_PATH"),
        help="External newline-delimited private terms; keep this file outside Git.",
    )
    args = parser.parse_args()
    problems = scan(load_external_denylist(args.denylist))
    if problems:
        print("PUBLIC RELEASE SCAN FAILED", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 1
    print(f"PUBLIC RELEASE SCAN PASSED: {sum(1 for _ in iter_public_files())} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
