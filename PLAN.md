## Decisions log
- 2026-10-31: Develop in Ubuntu 24.04 on WSL 2, project in ~ (not /mnt/c) for speed and correct permissions.
- 2026-10-31: Repo private until MVP works, then public.
- 2026-10-31: Every check returns a shared CheckResult so the CLI/reporter stays independent of check logic.