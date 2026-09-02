# Contributing to OPA

Thank you for helping improve OPA — Orbital Perturbation Analysis. Contributions are welcome from software developers, researchers, students, and orbital-mechanics practitioners.

## Before contributing

- Search existing issues before opening a new one.
- Use an issue to discuss substantial features, numerical-model changes, data-source changes, or interface redesigns before implementation.
- Do not include confidential, proprietary, export-controlled, or non-redistributable data.
- Read `DATA_PROVENANCE.md` before adding kernels or datasets.

For security vulnerabilities, follow `SECURITY.md` instead of opening a public issue.

## Development setup

OPA requires Python 3.12 or newer.

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Activate the virtual environment using the command appropriate for your operating system, then run the application with:

```bash
python run_opa.py
```

Dependency versions are pinned to the verified release environment. If a change needs a different version, explain the constraint in the pull request and update the dependency inventory only after testing the complete supported environment.

## Branches and commits

- Create a focused branch from the current default branch.
- Keep each pull request limited to one coherent change.
- Write concise, imperative commit subjects, for example `Add lunar perturbation regression test`.
- Do not combine formatting-only changes with scientific or behavioral changes.

## Code expectations

- Follow PEP 8 and use clear scientific names and SI units.
- Add type hints where they improve correctness and readability.
- Document reference frames, epochs, time scales, units, constants, and sign conventions.
- Avoid hidden global state and machine-specific absolute paths.
- Keep GUI logic separate from propagation and scientific-model logic where practical.
- Preserve backwards compatibility unless the change is explicitly documented.

## Scientific changes

A pull request that changes numerical results must describe:

- the physical model and assumptions;
- the coordinate frame, origin, epoch, and time scale;
- all units and constants;
- integrator and tolerance settings, when relevant;
- the reference implementation, paper, textbook, or trusted dataset used for validation; and
- numerical error or acceptance thresholds.

Add regression tests for corrected bugs and validation tests for new models. Numerical comparisons should use physically justified tolerances rather than exact floating-point equality.

## SPICE kernels and datasets

Every new or changed external file must have a corresponding entry in `DATA_PROVENANCE.md`. Include a checksum for immutable files when possible. Confirm redistribution permission before committing large or externally sourced files.

Do not silently replace a kernel with a newer file under the same name. Record the change, source, date, and expected scientific impact.

## Pull-request checklist

- [ ] The change is focused and documented.
- [ ] The application starts through `run_opa.py`.
- [ ] Relevant tests pass.
- [ ] New behavior has tests or a documented validation procedure.
- [ ] Scientific units, frames, epochs, and assumptions are explicit.
- [ ] Kernel and data provenance is complete.
- [ ] No secrets, private data, local paths, caches, or generated output are included.
- [ ] User-facing changes are reflected in the documentation and changelog.
- [ ] Third-party licenses and notices have been preserved.

## Licensing of contributions

Unless explicitly stated otherwise, any contribution intentionally submitted for inclusion in OPA is provided under the Apache License, Version 2.0, as described in Section 5 of that license. By submitting a contribution, you confirm that you have the right to do so.

The project `NOTICE` attribution must remain intact. External libraries, kernels, and datasets retain their own licenses and notices.

## Contact

- Jamal Damirov — jamal7damirov@gmail.com
- Altay Yusifov — altay1yusifov@gmail.com
