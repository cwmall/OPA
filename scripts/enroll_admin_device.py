"""Enroll the current Windows user/device with a provisioned public key."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from admin_security import enroll_device, load_verification_key_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verification-key", required=True)
    args = parser.parse_args()
    key = load_verification_key_file(args.verification_key)
    enroll_device(key)
    print("This Windows user/device is enrolled. No password was stored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
