# Threat model

## Protected against

- Accidental publication of private data in the public repository.
- Opening a package on a Windows user/device that was not separately enrolled.
- Package modification, forged metadata, wrong signing key, wrong password, unknown schema fields, and replay on another device identity.
- Archive traversal and symlink extraction: admin content is JSON data and is never extracted as an archive.
- Accidental persistence of admin unlock state, password, package path, decrypted profiles, or decrypted references in ordinary settings.
- Repeated online guessing through an increasing in-process delay.

## Trust boundaries

- The public repository and its Python code are not secret and may be modified by an attacker.
- The offline signing private key and source private data are high-value secrets.
- Windows DPAPI protects the device secret for the enrolled user account on that machine.
- The application process necessarily holds selected decrypted content while unlocked.

## Not protected against

- A Windows administrator, kernel-level attacker, debugger, or malware that can read the running Python process memory.
- A compromised authorized account while the admin session is unlocked.
- Screen capture, deliberate user export, clipboard capture, or photographs of displayed information.
- Replacement of the public application by malicious code that captures a password or decrypted values.
- Theft of both the offline signing key and provisioning inputs.
- Unlimited offline guessing if an attacker obtains all required device-bound secret material from a fully compromised host.

No claim of absolute DRM or secrecy is made. For higher assurance, use managed Windows devices, disk encryption, least privilege, code signing, endpoint protection, short unlocked sessions, and offline key custody. Rotate/re-enroll after a suspected compromise.
