# netdiag

A command-line tool that diagnoses network connectivity problems layer by layer and tells you which layer failed.

**Status: work in progress.** Milestones 1–4 of 6 are done: the individual checks work. The `diagnose` command, `--json` output and pytest tests are still to come. See [PLAN.md](PLAN.md) for the milestones, definition of done and decisions log.

This is a personal learning project about DNS, TCP, ICMP, socket programming and CLI design.

## What works now

Each check reports a status (`OK`, `WARN`, `FAIL` or `SKIP`), a short detail line, its latency and, when something is wrong, a hint about what to check next.

| Command | What it checks |
|---|---|
| `netdiag selftest` | netdiag itself works (resolves `localhost`) |
| `netdiag interface` | the default-route interface is up, has a link and has an IPv4 address |
| `netdiag gateway` | finds the default gateway and pings it |
| `netdiag ping HOST [--count N] [--timeout S]` | pings HOST using the system `ping` |
| `netdiag dns HOST [--server IP]` | resolves HOST with netdiag's own DNS client |
| `netdiag tcp HOST PORT` | opens a TCP connection and classifies failures |
| `netdiag http URL` | TCP first, then an HTTP(S) request (HTTP shows `SKIP` if TCP fails) |

Some details:

- **DNS** is a hand-written client over UDP using `socket` and `struct`. It builds the query, parses the response (including compressed names) and reports NXDOMAIN, SERVFAIL/REFUSED, timeouts and malformed replies. It uses the first nameserver in `/etc/resolv.conf` by default. It supports A records only: no AAAA, no TCP fallback.
- **TCP** failures are classified as DNS failure, connection refused, timeout or unreachable.
- **HTTP** doesn't follow redirects. 2xx/3xx is `OK`, 4xx/5xx is `WARN`, TLS errors and timeouts are `FAIL`.
- **Ping silence is `WARN`, not `FAIL`**, because many hosts and firewalls drop ICMP.

## Example output

```
$ netdiag http https://example.com/
[OK  ] TCP connect          example.com:443 accepted connection (21.9 ms)
[OK  ] HTTP GET             200 OK (477.3 ms)

$ netdiag dns doesnotexist.invalid
[FAIL] DNS lookup           doesnotexist.invalid does not exist (NXDOMAIN) (5.6 ms)
       Hint: Check the spelling. Compare with: dig <host> @1.1.1.1
```

## Install

Requires Python 3.10+ on Linux (the interface and gateway checks read `/proc` and `/sys`; developed on Ubuntu 24.04 under WSL 2). No external dependencies.

```bash
git clone https://github.com/Ariff194/netdiag.git
cd netdiag
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
netdiag --help
```

## Planned

- `netdiag diagnose HOST`: runs interface → gateway → ping 1.1.1.1 → DNS → TCP :443 → HTTPS in order. `WARN` continues, `FAIL` stops, and later layers show as `SKIP`.
- Hints for every `FAIL`/`WARN` result
- `--json` output
- pytest tests, at least one per failure type
