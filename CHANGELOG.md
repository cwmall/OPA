# Changelog

## Unreleased

- Added Apache License 2.0, the joint-author `NOTICE`, citation metadata, contribution guidance, third-party licensing guidance, and GitHub collaboration templates.
- Added repository metadata and dependency-update configuration for publication readiness.

## 2.43.6 — 2026-09-02

- Replaced GPL-only PyQt6 bindings with the official LGPLv3/GPLv3 Qt for Python bindings, PySide6.
- Replaced unverified raster branding with the repository-native SVG mark and a deterministic code-drawn mission header.
- Expanded publication checks to cover Git history, dependency licensing, provenance, and repository security settings.

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
