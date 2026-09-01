"""Generate an Ed25519 signing key pair outside the public repository."""

from __future__ import annotations

import argparse
from base64 import b64encode
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from admin_security import generate_signing_key  # noqa: E402


def _outside_repository(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        return path
    raise argparse.ArgumentTypeError("Signing keys must be stored outside the repository.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-key", required=True, type=_outside_repository)
    parser.add_argument("--public-key", required=True, type=_outside_repository)
    args = parser.parse_args()
    if args.private_key.exists() or args.public_key.exists():
        parser.error("Refusing to overwrite an existing key file.")
    private_key, public_key = generate_signing_key()
    args.private_key.parent.mkdir(parents=True, exist_ok=True)
    args.public_key.parent.mkdir(parents=True, exist_ok=True)
    args.private_key.write_bytes(private_key)
    try:
        os.chmod(args.private_key, 0o600)
    except OSError:
        pass
    args.public_key.write_text(b64encode(public_key).decode("ascii") + "\n", encoding="ascii")
    print("Signing key pair created outside the repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
