# Security Policy

## Supported versions

AegisOS is pre-1.0. Only the latest tagged release on the `main` branch
receives fixes.

| Version | Supported |
|---------|-----------|
| latest 0.x release | yes |
| older releases | no |

## Reporting a vulnerability

Please do **not** open a public issue for a security problem.

Use GitHub's private vulnerability reporting for this repository
("Security" tab, "Report a vulnerability"). The maintainers must enable that
feature on the published repository; until a dedicated contact address is
published, that is the only supported channel.

Include affected version, reproduction steps, and impact. We aim to
acknowledge reports promptly and to coordinate disclosure with the reporter.
No response-time guarantee is made for this volunteer project.

## Responsible disclosure

We ask reporters to give maintainers reasonable time to fix an issue before
public disclosure, and we will credit reporters who want credit.

## Security philosophy

- Prefer mature, existing Linux mechanisms over custom security code.
- Hardening is optional, documented, and reversible.
- Offensive-security tools are packaged for authorized testing and education.
  AegisOS ships no malware, credential theft, persistence, or automated attack
  tooling against third parties.
- Third-party software is only bundled after license verification.

## Secrets

No credentials, API keys, private keys, or passwords may be committed. CI and
`scripts/verify.sh` scan for common secret patterns. If you find one, report
it as above.

See also `docs/SECURITY.md` for the technical security model.
