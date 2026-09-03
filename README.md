# Orbital Perturbation Analyzer — Public Edition

OPA is a Python/PyQt6 desktop engineering application for inspecting generic orbital propagation, perturbations, eclipse geometry, GEO station-keeping indicators, and reference comparisons.

This repository is the **Public Mode** distribution. Every bundled spacecraft profile, orbit state, observation, station, reference trajectory, and eclipse event is fictional and marked `SYNTHETIC/DEMO`. It contains no private operator package and starts locked on every launch.

> Engineering notice: OPA is an analysis and education tool. It is not flight-certified and does not generate spacecraft commands.

## Install and run

Python 3.14 is the verified environment. From PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_opa.py
```

On Windows, `run_opa.cmd` is an equivalent relative-path launcher and contains
no machine-specific Python or user-directory path.

The first launch needs no private data and no network connection. The bundled short-span JPL ephemeris and IERS EOP series support the public scientific demonstrations. A public TLE catalogue is optional and is downloaded only when the user requests an update.

## Public features

- `PROPAGATION`: live synthetic telemetry, perturbation analysis, orbital view, propagation, GEO operations, and reference validation.
- `ECLIPSE`: generic Earth/Moon occultation analysis and synthetic reference events.
- Normal and Windows XP-inspired Retro themes, Azerbaijani/English UI, and safe per-user settings persistence.
- One public synthetic GEO profile plus user-created local profiles.

## Test

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:PYTHONPATH = (Resolve-Path src)
python -m compileall -q src scripts
python scripts/check_public_release.py
python -m unittest discover -s src -p "test_*.py"
python scripts/headless_smoke.py
```

See [headless testing](docs/HEADLESS_TESTING.md) for DPI and visual-QA commands.

## Settings and private extensions

Live configuration is stored under Qt's per-user application configuration directory, not in this repository. Writes are atomic and schema-validated. Admin unlock state, passwords, package paths, private profiles, and recent private projects are never persisted in ordinary configuration.

The optional `ADMIN ACCESS` system accepts only an externally provisioned, device-bound, signed and encrypted data package. The repository includes a fictional content example, but no signing key, device enrollment, password, or usable package. See [Admin extensions](docs/ADMIN_EXTENSIONS.md) and the [threat model](docs/THREAT_MODEL.md).

## Publication status

Do not publish this repository until the code owner selects and approves a project license. No license has been invented or added. PyQt6 also requires a deliberate GPLv3 or commercial-license decision; see [data and dependency provenance](DATA_PROVENANCE.md) and [publication checklist](docs/PUBLICATION_CHECKLIST.md).
