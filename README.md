# OPA — Orbital Perturbation Analysis

OPA is a Python/PySide6 desktop engineering application for satellite orbit analysis, perturbation modelling, numerical propagation, eclipse geometry, GEO station-keeping indicators, reference comparison, and scientific visualization.

The desktop product is presented as **Orbital Perturbation Analyzer — Public Edition**. This repository contains the public, synthetic-data edition of the joint OPA project by **Jamal Damirov** and **Altay Yusifov**.

Current release: **2.43.6**

> Engineering notice: OPA is an analysis and education tool. It is not flight-certified, does not generate spacecraft commands, and must not be used as the sole basis for operational or safety-critical decisions.

## Public-edition data policy

Every bundled spacecraft profile, orbit state, observation, station, reference trajectory, and eclipse event is fictional and marked `SYNTHETIC/DEMO`. The repository contains no private operator package and starts locked on every launch.

The first launch needs no private data or network connection. The bundled short-span JPL ephemeris and IERS Earth-orientation series support the public scientific demonstrations. A public TLE catalogue is optional and is downloaded only when the user requests an update.

## Features

- `PROPAGATION`: synthetic telemetry, perturbation analysis, orbital views, propagation, GEO operations, and reference validation.
- `ECLIPSE`: generic Earth/Moon occultation analysis and synthetic reference events.
- Scientific plotting and 2D/3D visualization with Matplotlib.
- Ephemeris and reference-frame calculations using SpiceyPy and NASA SPICE kernels.
- Normal and Windows XP-inspired Retro themes.
- Azerbaijani and English user interfaces.
- One public synthetic GEO profile plus locally created user profiles.
- Safe per-user settings persistence and optional, externally provisioned admin extensions.

## Requirements

- Python 3.14 is the verified release and CI environment.
- Python 3.12 is the minimum dependency-compatible baseline; environments below 3.14 have not yet passed the full OPA release test matrix.
- A supported Windows or Linux desktop environment for PySide6.
- Packages pinned in `requirements.txt`.
- Bundled scientific data under `data/`, `demo_data/`, and `kernels/`.

## Install and run

### Windows

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_opa.py
```

`run_opa.cmd` is an equivalent repository-relative Windows launcher. The existing desktop shortcut also starts the root `run_opa.py` entry point through `pythonw.exe` and contains no application logic.

### Linux

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run_opa.py
```

## Test

From PowerShell:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
$env:PYTHONPATH = (Resolve-Path src)
python -m compileall -q src scripts run_opa.py
python scripts/check_public_release.py
python -m unittest discover -s src -p "test_*.py"
python scripts/headless_smoke.py
```

Continuous integration runs the release checks on Windows and Ubuntu. See [headless testing](docs/HEADLESS_TESTING.md) for DPI and visual-QA commands.

## Settings and private extensions

Live configuration is stored under Qt's per-user application configuration directory, not in this repository. Writes are atomic and schema-validated. Admin unlock state, passwords, package paths, private profiles, and recent private projects are never persisted in ordinary configuration.

The optional `ADMIN ACCESS` system accepts only an externally provisioned, device-bound, signed and encrypted data package. The repository includes a fictional content example, but no signing key, device enrollment, password, or usable private package. See [Admin extensions](docs/ADMIN_EXTENSIONS.md) and the [threat model](docs/THREAT_MODEL.md).

## Scientific data and kernels

OPA includes redistributable SPICE kernels and Earth-orientation data required by the public demonstrations. Sources, checksums, purposes, and redistribution notes are recorded in [DATA_PROVENANCE.md](DATA_PROVENANCE.md).

External kernels and datasets retain their own terms and are not relicensed under Apache License 2.0 merely by being included in this repository. Preserve all upstream notices and update the provenance record whenever a file changes.

## Repository layout

```text
OPA/
├── .github/       CI, dependency updates, and contribution templates
├── assets/        User-interface and product artwork
├── data/          Public scientific data
├── demo_data/     Reproducible synthetic reference trajectories
├── docs/          Security, testing, publication, and extension guides
├── examples/      Synthetic configuration examples
├── kernels/       Redistributable NASA SPICE kernels
├── scripts/       Release, test, security, and data-generation utilities
├── src/           Application, GUI, scientific models, and tests
├── run_opa.py     Confirmed Python entry point
└── run_opa.cmd    Windows launcher
```

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening an issue or pull request. Numerical changes must document their units, frames, epochs, assumptions, reference sources, and validation tolerances.

## Citation and authors

Use [CITATION.cff](CITATION.cff) when citing OPA in research, software, reports, or presentations.

- Jamal Damirov — jamal7damirov@gmail.com
- Altay Yusifov — altay1yusifov@gmail.com

## License and attribution

OPA source code is licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE). The `NOTICE` attribution identifies Jamal Damirov and Altay Yusifov and must be preserved in downstream distributions as required by Apache License 2.0 Section 4(d).

Dependencies and scientific data retain their own licenses and terms. OPA uses the official Qt for Python bindings, PySide6, under the LGPLv3/GPLv3 community licensing route. Source-only publication does not bundle dependency wheels; binary distributors must preserve the applicable Qt and third-party notices and satisfy the LGPL requirements. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the [publication checklist](docs/PUBLICATION_CHECKLIST.md).

## Publication status

The project license, author attribution, PySide6 licensing route, scientific-data provenance, author attestations, history cleanup, and automated release checks are complete. The remaining post-publication GitHub checks are tracked in `docs/PUBLICATION_CHECKLIST.md`.
