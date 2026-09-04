# Changelog

## 2.45.0 — 2026-09-04

- Added a graph-local Full Screen control to the Perturbation page.
- Full Screen hides the complete application shell and leaves only the live graph visible; Escape restores the exact previous window state.
- Added matching Normal, Retro, English, and Azerbaijani presentation.

## 2.44.1 — 2026-09-04

- Anchored Perturbation prediction to the selected spacecraft state and epoch instead of the default TLE.
- Applied the active profile's effective area, mass, and CP consistently to both live and predicted SRP.
- Kept Perturbation controls permanently visible and made the graph fill the remaining page without whole-page scrolling.

## 2.44.0 — 2026-09-04

- Moved the expensive past/future Perturbation prediction off the Qt GUI thread without changing its numerical model, settings, sampling, or outputs.
- Added live prediction progress and safe cancellation while keeping the application responsive.
- Reorganized Perturbation controls into compact filter/action rows and made the graph fit common laptop work areas.
- Added Azerbaijani text for the new background-calculation states.

## 2.43.5 — 2026-09-01

- Renamed the distributable repository folder and desktop launcher to Orbital Perturbation Analyzer branding.
- Removed the last obsolete product-path reference while preserving the scientific Moon perturbation module and labels.

## 2.43.4 — 2026-09-01

- Removed the built-in synthetic LEO profile from the public spacecraft catalogue.
- Migrates a previously selected retired LEO profile safely to the synthetic GEO profile.
- Corrected remaining GEO reference/SRP labels that still said LEO.

## 2.43.3 — 2026-09-01

- Simplified Admin Access to password-only unlock when external device provisioning and the encrypted package are ready.
- Hid private package paths and setup controls during normal admin use.
- Added explicit UI confirmation that private content remains outside the shareable application folder.

## 2.43.2 — 2026-09-01

- Temporarily removed the unfinished Orbit Determination workspace from the visible application shell and Retro navigation.
- Preserved the isolated OD engine for a future reviewed reintroduction.
- Safely redirects a previously saved OD module selection to Propagation.

## 2.43.1 — 2026-09-01

- Restored the established generic OPA orbit emblem and mission banner artwork.
- Kept the Windows XP-inspired Retro header compact and artwork-free.
- Stabilized the Windows per-user application-data path used by configuration and admin packages.

## 2.43.0 — 2026-08-31

- Extended signed admin packages with validated in-memory Eclipse and Orbit Determination datasets.
- Added automatic discovery of the installed device-bound admin package so unlock requires only the password after provisioning.
- Kept all private session data volatile and cleared it on logout or restart.

## 2.42.0 — 2026-08-31

- Converted the distributable application to a synthetic-only Public Mode.
- Added device-bound, signed and encrypted data-only Admin extensions.
- Moved settings, TLE cache, logs, diagnostics, profiles, and exports outside the repository.
- Added atomic configuration migration and full restart restoration.
- Added responsive Settings layout, Azerbaijani Admin UI, release scans, CI, and headless visual QA.
- Replaced unverified artwork with an original code-drawn header and repository-native SVG mark.
- Added real Windows DPAPI integration coverage and a machine-independent Windows launcher.

Historical private release notes are intentionally not included in the public distribution.
