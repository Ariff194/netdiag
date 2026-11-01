# netdiag — Plan

## Goal
A CLI that diagnoses connectivity problems layer by layer and explains which layer failed.

## Why / what I'll learn
- DNS message format, TCP handshake, ICMP, sockets API
- Python packaging, CLI design, testing

## Scope
MVP: interface, ping, DNS (from scratch), TCP, HTTP, diagnose ladder, hints, --json
Stretch: Docker fault-injection lab, traceroute, cloud VM test
Out of scope: port scanning, GUI

## Estimate
~16h MVP. Stop-and-review point: 24h.
Used so far: ~2h (after M2)

## Milestones
- [x] M1 Setup + CheckResult (2026-10-31)
- [x] M2 TCP + HTTP (2026-11-01)
- [ ] M3 DNS from scratch
- [ ] M4 Interface/gateway/ping
- [ ] M5 Diagnose ladder + hints
- [ ] M6 Tests, README, write-up

## Definition of done
- [ ] Interface check works
- [ ] Ping check works
- [ ] DNS check works (my own packet builder/parser)
- [x] TCP check works (refused / timeout / unreachable / DNS failure)
- [x] HTTP check works (OK / WARN / SKIP / TLS error)
- [ ] `netdiag diagnose <host>` runs the checks in order and stops at the first failing layer
- [ ] Every FAIL/WARN result has a hint explaining what to check next
- [ ] `--json` outputs valid JSON
- [ ] `pytest` passes, with at least one test per failure type
- [ ] README: what it does, install, example output, how to test
- [ ] Short write-up I can explain in an interview
- [ ] Repo made public, with no secrets in the history

## Decisions log
- 2026-10-31: Develop in Ubuntu 24.04 on WSL 2, project in ~ (not /mnt/c) for speed and correct permissions.
- 2026-10-31: Repo private until MVP works, then public.
- 2026-10-31: Every check returns a shared CheckResult so the CLI/reporter stays independent of check logic.
- (planned, M4) Use subprocess ping instead of raw ICMP — raw sockets need root.
- 2026-11-01: Added Status.WARN for HTTP 4xx/5xx — network path worked, server answered with an error, which is a different problem from a failed connection.
- 2026-11-01: `netdiag http` checks TCP first and marks HTTP as SKIP if TCP fails, so output shows which layer broke. Trade-off: two connections instead of one.
- 2026-11-01: HTTP check does not follow redirects; a 3xx is reported as-is because the redirect itself is diagnostic information.