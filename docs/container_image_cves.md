# Container Image CVE Report

**Image**: `python:3.14-slim-trixie`
**Scan date**: 2026-04-01
**Scanner**: Grype 0.110.0

## CI Strategy

The CI pipeline (`security.yml`) runs Grype with `only-fixed: true` and `severity-cutoff: high`.
This means the build only fails on high/critical CVEs that have a fix available.
Unfixed CVEs are reported in the GitHub Security tab (SARIF upload) but do not block the pipeline.

## Known Unfixed CVEs (High)

| CVE | Package | Installed | Fixed In | Severity | Notes |
|-----|---------|-----------|----------|----------|-------|
| CVE-2026-2673 | libcrypto3 / libssl3 (OpenSSL) | 3.5.5-r0 | - | High | No fix available in Alpine yet |
| CVE-2026-4519 | CPython | 3.13.12 | - | High | Fix announced for 3.15.0a6 only (alpha), not backported to 3.13.x |

## Known Unfixed CVEs (Medium / Low)

| CVE | Package | Installed | Fixed In | Severity |
|-----|---------|-----------|----------|----------|
| CVE-2026-3644 | CPython | 3.13.12 | - | Medium |
| CVE-2025-15366 | CPython | 3.13.12 | 3.15.0a6 | Medium |
| CVE-2025-15367 | CPython | 3.13.12 | 3.15.0a6 | Medium |
| CVE-2026-4224 | CPython | 3.13.12 | - | Medium |
| CVE-2025-12781 | CPython | 3.13.12 | - | Medium |
| CVE-2026-2297 | CPython | 3.13.12 | - | Medium |
| CVE-2025-60876 | busybox | 1.37.0-r30 | - | Medium |
| CVE-2026-27171 | zlib | 1.3.1-r2 | 1.3.2-r0 | Medium |
| GHSA-6vgw-5pg2-w6jp | pip | 25.3 | 26.0 | Low |
| CVE-2025-13462 | CPython | 3.13.12 | - | Low |
| CVE-2026-3479 | CPython | 3.13.12 | - | Low |

## Mitigation

- **Alpine base image** was chosen over Debian slim to minimize the attack surface (117MB vs ~150MB, fewer system packages).
- **Multi-stage build** ensures build tools (gcc, make, dev headers) are not present in the runtime image.
- **Runtime image** only contains `libpq` and `libgcc` as additional system packages.
- CVEs are monitored via the GitHub Security tab through automated SARIF uploads on every push/PR.
- This document should be updated when the base image is upgraded or CVEs are resolved.
