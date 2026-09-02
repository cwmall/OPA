# Publication checklist

## Automated gate

- [x] `python scripts/check_public_release.py` passes with the external private denylist.
- [x] Full unit/GUI suite passes offscreen (123 tests on the release workstation).
- [x] DPI smoke matrix passes at 100%, 125%, 150%, and 200%.
- [x] A tracked-files-only fresh copy installs into a new virtual environment and launches.
- [x] No file is 100 MB or larger.
- [x] `git ls-files` inventory contains only intended public files.
- [x] Exact direct and transitive source-environment dependencies are recorded in `DEPENDENCY_INVENTORY.md`.
- [x] GitHub dependency graph, Dependabot alerts, malware alerts, security updates, and grouped security updates are enabled.
- [x] Pull requests run `actions/dependency-review-action` in CI.
- [ ] After the repository becomes public, verify automatic GitHub secret scanning and enable Private Vulnerability Reporting.

## Manual legal/security gate

- [x] Code ownership is confirmed by both named authors in `docs/OWNERSHIP_ATTESTATION.md`.
- [x] Unverified raster branding is excluded; the release uses repository-native SVG geometry and a code-drawn mission header.
- [x] Apache License 2.0 is selected by the project authors and included with a joint-author `NOTICE`.
- [x] PyQt6 was replaced with PySide6; the source release uses the documented LGPLv3/GPLv3 community route.
- [x] NAIF acknowledgement/rules and USNO/IERS attribution are retained in `DATA_PROVENANCE.md` and `THIRD_PARTY_NOTICES.md`.
- [x] Repository visibility remained private until all pre-publication gates passed.
- [x] `SECURITY.md` provides a private maintainer contact while the repository is private.
- [ ] Enable Private Vulnerability Reporting immediately after publication; GitHub exposes it for public repositories.
- [x] Signing private keys, enrollment files, packages, passwords, and quarantine paths are outside Git; the pre-rewrite repository is backed up outside the working tree.

## History gate

- [x] `python scripts/audit_git_history.py --denylist <external-file>` passes across every local and remote ref.
- [x] Unverified historical raster assets were removed in a separately reviewed history rewrite before publication.

If any private data exists in history, make a verified backup and perform a
separately reviewed history rewrite; do not delete history blindly.
