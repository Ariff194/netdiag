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
Used so far: ~4h (after M4)

## Milestones
- [x] M1 Setup + CheckResult (2026-10-31)
- [x] M2 TCP + HTTP (2026-11-01)
- [x] M3 DNS from scratch (2026-11-03)
- [x] M4 Interface/gateway/ping (2026-11-11)
- [ ] M5 Diagnose ladder + hints
- [ ] M6 Tests, README, write-up

## Definition of done
- [x] Interface check works
- [x] Ping check works
- [x] DNS check works (my own packet builder/parser)
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

- 2026-11-01: Added Status.WARN for HTTP 4xx/5xx — network path worked, server answered with an error, which is a different problem from a failed connection.
- 2026-11-01: `netdiag http` checks TCP first and marks HTTP as SKIP if TCP fails, so output shows which layer broke. Trade-off: two connections instead of one.
- 2026-11-01: HTTP check does not follow redirects; a 3xx is reported as-is because the redirect itself is diagnostic information.

- 2026-11-03: DNS check queries the first nameserver in /etc/resolv.conf by default, with a --server override, so it tests what the machine actually uses.
- 2026-11-03: NOERROR with no A record is WARN, not FAIL: DNS worked, but the name has no IPv4 address (same reasoning as the HTTP WARN decision).
- 2026-11-03: MVP queries A records only over UDP; no AAAA and no TCP fallback for truncated replies (reported as WARN).

- 2026-11-11: Use subprocess ping instead of raw ICMP — raw sockets need root.
- 2026-11-11: No ping reply, partial packet loss, and a gateway that ignores ping are WARN, not FAIL: many hosts and firewalls drop ICMP, so silence doesn't prove the path is broken.
- 2026-11-11: FAIL only when it's unambiguous: host doesn't resolve, network/host unreachable, no default route, or interface has no IPv4 address (MVP is IPv4-only). Missing ping binary is SKIP.
- 2026-11-11: Interface link state is read from /sys/class/net/<iface>/carrier, not the RUNNING bit in sysfs flags (sysfs flags only hold admin-set flags).