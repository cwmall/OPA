# Repository release policy

- `src/app_version.py` is the only application-version source.
- Every user-visible release must update `APP_VERSION` using Semantic Versioning.
- Use PATCH for corrections, MINOR for backward-compatible capabilities, and
  MAJOR only for incompatible model, data, or workflow changes.
- Keep the small version label in the upper-right application header sourced
  from `APP_VERSION`; never duplicate a literal version in the UI.
