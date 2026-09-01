# Third-party software and data

OPA's own source code is licensed under Apache License 2.0. That license does not replace the licenses of dependencies, Qt components, NASA SPICE software, kernels, or datasets.

## Direct Python dependencies

The current dependency template lists:

- NumPy
- SciPy
- Matplotlib
- PyQt6
- Skyfield
- SpiceyPy
- cryptography
- argon2-cffi

Before publishing a source or binary release, generate and review a complete dependency inventory for the resolved environment and include every notice or license required by the versions actually distributed.

## PyQt6

Riverbank Computing provides PyQt6 under GNU GPL v3 and a commercial license. A distributor using the freely available GPL build must comply with the GPL obligations applicable to the combined application. A party that cannot distribute compatibly with the GPL should obtain appropriate commercial licensing or seek qualified legal advice.

OPA's Apache License 2.0 describes the license selected by the OPA copyright holders; it does not grant rights in PyQt6 or override PyQt6's license.

## NASA SPICE and kernels

SpiceyPy, the NASA SPICE Toolkit, NAIF documentation, and individual SPICE kernels may have distinct attribution, citation, redistribution, and disclaimer requirements. Record every distributed kernel in `DATA_PROVENANCE.md` and preserve its accompanying terms.

Do not imply endorsement by NASA, JPL, NAIF, a kernel producer, or any dependency maintainer.

## Release checklist

- [ ] Resolve and record the exact dependency versions.
- [ ] Inventory transitive dependencies and bundled Qt components.
- [ ] Preserve required licenses and notices.
- [ ] Confirm the selected PyQt6 licensing path.
- [ ] Confirm redistribution rights for every kernel and dataset.
- [ ] Update `DATA_PROVENANCE.md` and this file.
