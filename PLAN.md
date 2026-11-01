## Decisions log
- 2026-10-31: Develop in Ubuntu 24.04 on WSL 2, project in ~ (not /mnt/c) for speed and correct permissions.
- 2026-10-31: Repo private until MVP works, then public.
- 2026-10-31: Every check returns a shared CheckResult so the CLI/reporter stays independent of check logic.

- 2026-11-01: Added Status.WARN for HTTP 4xx/5xx — network path worked, server answered with an error, which is a different problem from a failed connection.
- 2026-11-01: `netdiag http` checks TCP first and marks HTTP as SKIP if TCP fails, so output shows which layer broke. Trade-off: two connections instead of one.
- 2026-11-01: HTTP check does not follow redirects; a 3xx is reported as-is because the redirect itself is diagnostic information.