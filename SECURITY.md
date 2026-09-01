# Security policy

## Supported release

Security fixes are evaluated for the current `2.43.x` public release line.

## Reporting

Do not disclose a suspected vulnerability in a public issue, discussion, or pull request. Configure GitHub Private Vulnerability Reporting or private Security Advisories before making the repository public.

Until a private GitHub reporting channel is available, report vulnerabilities privately to both maintainers when practical:

- Jamal Damirov — jamal7damirov@gmail.com
- Altay Yusifov — altay1yusifov@gmail.com

Do not include real passwords, private datasets, packages, enrollment files, signing keys, screenshots containing confidential information, or destructive payloads.

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
