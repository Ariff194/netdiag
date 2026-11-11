import os
import re
import subprocess
from dataclasses import dataclass

from netdiag.models import CheckResult, Status

# Lines we parse from iputils ping output (forced to English with LC_ALL=C):
#   3 packets transmitted, 3 received, 0% packet loss, time 2003ms
#   rtt min/avg/max/mdev = 9.1/10.2/11.0/0.7 ms
SUMMARY = re.compile(r"(\d+) packets transmitted, (\d+) received")
RTT = re.compile(r"= [\d.]+/([\d.]+)/")


@dataclass
class PingResult:
    sent: int = 0
    received: int = 0
    avg_ms: float | None = None
    unreachable: bool = False   # a router sent back ICMP "Destination ... Unreachable"
    error: str | None = None    # ping could not run properly (unknown host, no route, ...)


def run_ping(host: str, count: int = 3, timeout: float = 2.0) -> PingResult:
    """Run the system ping and parse its summary. Raises FileNotFoundError if ping is missing."""
    if not host or host.startswith("-"):
        # A "host" like "-f" would be read by ping as an option, not a target.
        return PingResult(error="invalid host name")
    # -n: numeric output (no reverse DNS)  -c: number of echo requests  -W: seconds to wait per reply
    cmd = ["ping", "-n", "-c", str(count), "-W", f"{timeout:g}", host]
    env = {**os.environ, "LC_ALL": "C"}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env,
                           timeout=count + timeout + 5)  # ping sends one request per second
    except subprocess.TimeoutExpired:
        return PingResult(error="ping did not finish in time")

    summary = SUMMARY.search(p.stdout)
    # Exit code 2 (or no summary line) means ping never got to send packets.
    if p.returncode == 2 or summary is None:
        lines = (p.stderr.strip() or p.stdout.strip()).splitlines()
        return PingResult(error=lines[-1] if lines else f"ping exited with code {p.returncode}")

    rtt = RTT.search(p.stdout)
    return PingResult(sent=int(summary.group(1)),
                      received=int(summary.group(2)),
                      avg_ms=float(rtt.group(1)) if rtt else None,
                      unreachable="Unreachable" in p.stdout)


def check_ping(host: str, count: int = 3, timeout: float = 2.0) -> CheckResult:
    name = "Ping"
    try:
        r = run_ping(host, count, timeout)
    except FileNotFoundError:
        return CheckResult(name, Status.SKIP, "ping command not found",
                           hint="Install it: sudo apt install iputils-ping")

    if r.error:
        low = r.error.lower()
        if any(s in low for s in ("name or service not known",
                                  "temporary failure in name resolution",
                                  "no address associated")):
            return CheckResult(name, Status.FAIL, f"cannot resolve {host}",
                               hint="DNS lookup failed. Try: netdiag dns <host>")
        if "network is unreachable" in low:
            return CheckResult(name, Status.FAIL, f"{host}: network unreachable",
                               hint="No route to that network. Try: netdiag gateway, ip route")
        return CheckResult(name, Status.FAIL, f"{host}: {r.error}")

    if r.received == r.sent:
        return CheckResult(name, Status.OK, f"{host} replied {r.received}/{r.sent}",
                           latency_ms=r.avg_ms)
    if r.received > 0:
        loss = round(100 * (r.sent - r.received) / r.sent)
        return CheckResult(name, Status.WARN,
                           f"{host} {loss}% packet loss ({r.received}/{r.sent} replies)",
                           latency_ms=r.avg_ms,
                           hint="Path works but is losing packets (congestion, weak Wi-Fi?). "
                                "Try a longer run: ping -c 20 <host>")
    if r.unreachable:
        return CheckResult(name, Status.FAIL, f"{host} unreachable (a router reported no route)",
                           hint="A router sent back 'unreachable'. Check: ip route, traceroute <host>")
    return CheckResult(name, Status.WARN, f"{host} no replies ({r.sent} sent)",
                       hint="Many hosts and firewalls drop ping, so this alone doesn't prove the "
                            "host is down. Try: netdiag tcp <host> 443")
