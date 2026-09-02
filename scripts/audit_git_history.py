"""Scan every Git blob reachable from every ref for public-release leaks."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
MAX_SCANNED_BLOB_BYTES = 20_000_000
FORBIDDEN_NAMES = re.compile(
    r"(?:^|/)(?:\.env(?:\..*)?|[^/]+\.(?:key|pem|p12|pfx|opa-admin)|"
    r"admin_enrollment\.json|secrets?|private|quarantine)(?:/|$)",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    ("private key block", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY", re.I)),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[0-9A-Za-z]{16,}\b")),
    (
        "hard-coded password",
        re.compile(r"(?im)^\s*(?:admin_)?password\s*=\s*['\"][^'\"]+['\"]"),
    ),
    ("hard-coded Windows user path", re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.I)),
)


def git(*args: str) -> bytes:
    return subprocess.check_output(("git", *args), cwd=ROOT)


def load_denylist(path: str | None) -> tuple[str, ...]:
    if not path:
        return ()
    source = Path(path).expanduser().resolve()
    return tuple(
        line.strip().casefold()
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--denylist",
        help="External newline-delimited private terms; keep it outside Git.",
    )
    args = parser.parse_args()
    denylist = load_denylist(args.denylist)

    rows = git("rev-list", "--objects", "--all").decode("utf-8", "replace").splitlines()
    problems: set[str] = set()
    scanned: set[str] = set()
    blob_count = 0

    for row in rows:
        object_id, _, path = row.partition(" ")
        if path and FORBIDDEN_NAMES.search(path.replace("\\", "/")):
            problems.add(f"forbidden historical path: {path}")
        if object_id in scanned or git("cat-file", "-t", object_id).strip() != b"blob":
            continue
        scanned.add(object_id)
        blob_count += 1
        size = int(git("cat-file", "-s", object_id))
        if size > MAX_SCANNED_BLOB_BYTES:
            continue
        content = git("cat-file", "blob", object_id)
        if b"\x00" in content[:8192]:
            continue
        text = content.decode("utf-8", "replace")
        label = path or object_id
        for pattern_label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.add(f"{pattern_label}: {label} ({object_id[:12]})")
        folded = text.casefold()
        if any(term in folded for term in denylist):
            problems.add(f"external denylist match: {label} ({object_id[:12]})")

    if problems:
        print("GIT HISTORY AUDIT FAILED", file=sys.stderr)
        for problem in sorted(problems):
            print(f"- {problem}", file=sys.stderr)
        return 1

    print(f"GIT HISTORY AUDIT PASSED: {blob_count} unique blobs across all refs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
