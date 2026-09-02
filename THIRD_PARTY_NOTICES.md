# Third-party software and data

OPA's own source code is licensed under Apache License 2.0. That license does not replace the licenses of dependencies, Qt components, NASA SPICE software, kernels, or datasets.

## Direct Python dependencies

The current dependency template lists:

- NumPy
- SciPy
- Matplotlib
- PySide6
- Skyfield
- SpiceyPy
- cryptography
- argon2-cffi

Before publishing a source or binary release, generate and review a complete dependency inventory for the resolved environment and include every notice or license required by the versions actually distributed.

The verified source-release environment is recorded in `DEPENDENCY_INVENTORY.md`.

## PySide6 and Qt

The Qt Company provides Qt for Python/PySide6 under LGPLv3/GPLv3 community licenses and a commercial license. OPA uses the community PySide6 wheel and dynamically loaded Qt libraries. The OPA source remains under Apache License 2.0; PySide6, Shiboken6, and Qt retain their own terms.

A source-only checkout installs PySide6 separately from PyPI and does not redistribute Qt binaries in this repository. A binary distributor must review the exact bundled Qt modules, provide the required notices and license texts, permit relinking/replacement as required by LGPLv3, and avoid imposing conflicting restrictions.

Official licensing references:

- <https://doc.qt.io/qtforpython-6/>
- <https://doc.qt.io/qtforpython-6/licenses.html>
- <https://doc.qt.io/qtforpython-6/overviews/qtdoc-lgpl.html>

## NASA SPICE and kernels

SpiceyPy, the NASA SPICE Toolkit, NAIF documentation, and individual SPICE kernels may have distinct attribution, citation, redistribution, and disclaimer requirements. Record every distributed kernel in `DATA_PROVENANCE.md` and preserve its accompanying terms.

Do not imply endorsement by NASA, JPL, NAIF, a kernel producer, or any dependency maintainer.

## Release checklist

- [x] Resolve and record the exact source-environment dependency versions.
- [x] Inventory transitive dependencies for the source-release environment.
- [ ] Preserve required licenses and notices.
- [x] Use the PySide6 LGPLv3/GPLv3 community licensing route for source publication.
- [x] Confirm redistribution rights for every bundled kernel and dataset.
- [x] Update `DATA_PROVENANCE.md` and this file.
