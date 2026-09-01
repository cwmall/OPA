# Publication checklist

## Automated gate

- [x] `python scripts/check_public_release.py` passes with the external private denylist.
- [x] Full unit/GUI suite passes offscreen (123 tests on the release workstation).
- [x] DPI smoke matrix passes at 100%, 125%, 150%, and 200%.
- [x] A tracked-files-only fresh copy installs into a new virtual environment and launches.
- [x] No file is 100 MB or larger.
- [x] `git ls-files` inventory contains only intended public files.
- [ ] GitHub secret scanning and dependency review are enabled.

## Manual legal/security gate

- [ ] Code ownership is confirmed for every source file.
- [ ] Authorship and redistribution rights are confirmed for the selected OPA emblem and mission-banner raster artwork.
- [x] Apache License 2.0 is selected by the project authors and included with a joint-author `NOTICE`.
- [ ] The PyQt6 GPLv3/commercial licensing route is approved.
- [ ] NAIF acknowledgement/rules and USNO/IERS attribution are retained.
- [ ] Repository visibility remains private until all gates pass.
- [ ] GitHub Security Advisories or Private Vulnerability Reporting are configured before publication.
- [ ] Signing private keys, enrollment files, packages, passwords, and quarantine paths are outside Git and backed up securely.

## History gate

The supplied source working tree has Git metadata, but its current public-release files are staged as additions. Audit the branch and all prior reachable commits before publication. If private data exists in history, make a verified backup and perform a separately reviewed history rewrite; do not delete history blindly.
