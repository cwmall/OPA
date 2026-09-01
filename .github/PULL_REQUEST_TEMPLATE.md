## Summary

Describe the change and why it is needed.

## Validation

List the tests, reference data, or manual checks used to validate the change.

## Scientific impact

State any effect on numerical results, physical assumptions, units, coordinate frames, epochs, time scales, constants, integrators, or tolerances. Write `None` when the change has no scientific impact.

## Data and licensing impact

List added or changed dependencies, kernels, datasets, licenses, notices, and provenance records. Write `None` when there is no impact.

## Checklist

- [ ] The application starts through `run_opa.py`.
- [ ] Relevant tests pass.
- [ ] New or changed numerical behavior is validated with justified tolerances.
- [ ] Documentation and `CHANGELOG.md` are updated where needed.
- [ ] `DATA_PROVENANCE.md` is updated for every changed external file.
- [ ] No secrets, private data, local absolute paths, caches, or generated output are included.
- [ ] The `LICENSE` and `NOTICE` files remain intact.
