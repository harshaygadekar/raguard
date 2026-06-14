# Security Policy

## Supported Versions

We actively support and patch the latest version of RAGuard. If you discover a security issue, we recommend upgrading to the latest release to ensure you have all security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

As a security project, we take vulnerabilities very seriously. If you believe you have found a security vulnerability in RAGuard, please do **not** open a public issue. Doing so exposes users to potential exploits before a patch is ready.

Please report vulnerabilities privately by emailing the maintainers at [security@raguard.org].

### What to Include in Your Report:
*   A detailed description of the vulnerability.
*   A proof of concept (PoC) script, steps, or prompt injection payload to reproduce the issue.
*   The version(s) of RAGuard affected.
*   Any potential impact or exfiltration path (e.g., bypassing specific adapters like FastAPI/LangChain).

### Our Commitment:
1. **Acknowledgement:** We will acknowledge receipt of your report within **48 hours**.
2. **Triaging:** We will triage the report and work on a fix as quickly as possible.
3. **Disclosure:** We will coordinate with you to release a patch and issue a public disclosure (CVE) with appropriate credit to you.
