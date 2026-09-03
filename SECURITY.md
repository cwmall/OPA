# Security policy

## Supported release

Security fixes are prepared for the current `2.42.x` public release line.

## Reporting

Before publication, configure a private GitHub Security Advisory channel. Do not place suspected private datasets, passwords, packages, enrollment files, keys, screenshots, or local paths in a public issue.

## Security properties

- Every process starts locked in Public Mode.
- Admin packages are verified with Ed25519 before decryption.
- AES-256-GCM authenticated encryption binds a package to its schema and device identity.
- Argon2id combines the admin password with a random device secret.
- On Windows, the device secret is protected for the current user by DPAPI.
- Package content is schema-validated, data-only, bounded in size, and never archive-extracted or executed.
- Wrong password, wrong device, modified ciphertext, unknown fields, and invalid signatures fail closed with rate limiting.
- Logout and close stop calculation workers and remove session profiles, references, and module pages.

No system can promise secrecy after a Windows administrator controls the host or an attacker reads the live Python process memory. See [Threat model](docs/THREAT_MODEL.md).
