import socket
import struct
from pathlib import Path

from netdiag.checks.ping import run_ping
from netdiag.models import CheckResult, Status

ROUTE_FILE = Path("/proc/net/route")
RTF_UP = 0x1
RTF_GATEWAY = 0x2


def default_route() -> tuple[str, str] | None:
    """Return (interface, gateway IP) of the IPv4 default route, or None if there isn't one.

    /proc/net/route columns: Iface Destination Gateway Flags RefCnt Use Metric Mask ...
    Addresses are hex in the CPU's byte order (little-endian on x86), e.g. 011015AC = 172.21.16.1.
    """
    try:
        lines = ROUTE_FILE.read_text().splitlines()[1:]  # skip the header line
    except OSError:
        return None
    best = None  # (metric, iface, gateway)
    for line in lines:
        f = line.split()
        if len(f) < 7:
            continue
        iface, dest, gw, flags, metric = f[0], f[1], f[2], int(f[3], 16), int(f[6])
        # Default route = destination 0.0.0.0, route is up, and it goes via a gateway.
        if dest == "00000000" and flags & RTF_UP and flags & RTF_GATEWAY:
            if best is None or metric < best[0]:  # lowest metric wins, like the kernel
                best = (metric, iface, socket.inet_ntoa(struct.pack("=I", int(gw, 16))))
    return (best[1], best[2]) if best else None


def check_gateway(timeout: float = 2.0) -> CheckResult:
    name = "Gateway"
    route = default_route()
    if route is None:
        return CheckResult(name, Status.FAIL, "no default route",
                           hint="Nothing outside the local network is reachable without a default "
                                "gateway. Check: ip route (DHCP may have failed)")
    iface, gw = route
    try:
        r = run_ping(gw, count=2, timeout=timeout)
    except FileNotFoundError:
        return CheckResult(name, Status.SKIP, f"default gateway {gw} via {iface}; ping not found",
                           hint="Install it: sudo apt install iputils-ping")

    if r.error:
        return CheckResult(name, Status.FAIL, f"cannot ping gateway {gw} via {iface}: {r.error}")
    if r.received == r.sent:
        return CheckResult(name, Status.OK, f"{gw} via {iface} replied", latency_ms=r.avg_ms)
    if r.received > 0:
        return CheckResult(name, Status.WARN,
                           f"{gw} via {iface} lost {r.sent - r.received}/{r.sent} pings",
                           latency_ms=r.avg_ms,
                           hint="Losing packets on the local network: check Wi-Fi signal or cable")
    return CheckResult(name, Status.WARN, f"{gw} via {iface} did not reply to ping",
                       hint="Some routers ignore ping. If the later checks also fail, the problem "
                            "is probably your local network or router")
