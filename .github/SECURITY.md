# Security Policy

## Supported versions

nPhoneKIT is developed on `main` and shipped as releases. Security fixes are
applied to `main` and the latest release. Please make sure you are on the most
recent version before reporting an issue.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

Report privately through GitHub's **"Report a vulnerability"** button under this
repository's **Security** tab (Security Advisories). This keeps the details
private until a fix is available.

When reporting, include as much of the following as you can:

- A description of the issue and its impact.
- Steps to reproduce (and a proof of concept if you have one).
- The nPhoneKIT version, your OS, and how you ran it (e.g. as root/sudo).

We will acknowledge the report, investigate, and coordinate a fix and
disclosure timeline with you.

## Scope notes

nPhoneKIT is a device-flashing / repair toolbox: it runs external tools
(adb, fastboot, mtkclient), may require elevated privileges, and communicates
with connected devices. Security-relevant reports of particular interest
include:

- Command injection or unsafe handling of external/device-provided input.
- Unexpected network communication or data exfiltration.
- Code that modifies the host, the environment, or nPhoneKIT itself without
  clear, informed user consent.
- Supply-chain concerns in bundled or fetched dependencies.
