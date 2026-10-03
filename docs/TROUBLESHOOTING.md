# Troubleshooting

| Symptom | Cause / action |
|---------|----------------|
| `make build` says missing tools | Run on Debian 13 with the packages listed in `docs/BUILD.md` |
| `aegis doctor` WARN on connectivity | An HTTPS request to deb.debian.org failed or was filtered; offline use still works |
| `aegis install X` says "no candidate" | The candidate package is not in your configured repositories; run `aegis update` or check the manifest |
| `aegis hardening apply` needs root | Run with sudo, or use `--dry-run` to preview |
| Services show "unavailable" in Security Center | systemd is not PID 1 (for example in a container) |
| Firewall "status needs root" | Querying ufw/nftables/iptables needs privileges |
| Listening ports show no process name | Process mapping needs privileges for other users' processes |
