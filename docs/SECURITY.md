# Security model

- Reporting: see the root `SECURITY.md`.
- Live user is unprivileged; privilege via `sudo`. Default live credentials come from `live-config`
  and apply to the live session only (NOT VERIFIED in a booted image).
- Aegis never replaces apt, never adds unsigned repositories, and `aegis doctor` fails on `trusted=yes`.
- `aegis hardening` writes one sysctl drop-in plus a state file; `revert` removes both. It is never applied
  by the image build. It deliberately does not set `kernel.yama.ptrace_scope` so debuggers keep working.
- Security Center: read-only, binds to 127.0.0.1, rejects foreign `Host` headers, answers 405 to non-GET.
  It is not a substitute for a firewall or IDS.
- Offensive tools: authorized testing and education only. No attack automation ships with AegisOS.
- Secrets: none in the repository; `make verify` scans for common patterns (pattern scan only).
