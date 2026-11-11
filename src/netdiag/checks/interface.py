import fcntl
import socket
import struct
from pathlib import Path

from netdiag.checks.gateway import default_route
from netdiag.models import CheckResult, Status

SYS_NET = Path("/sys/class/net")
IFF_UP = 0x1          # switched on by the admin (ip link set <iface> up)
SIOCGIFADDR = 0x8915  # ioctl request: "give me this interface's IPv4 address"


def ipv4_address(iface: str) -> str | None:
    """Ask the kernel for an interface's IPv4 address with ioctl(SIOCGIFADDR)."""
    # struct ifreq = 16-byte interface name + a union; the kernel fills in a sockaddr_in.
    req = struct.pack("256s", iface.encode()[:15])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            res = fcntl.ioctl(s.fileno(), SIOCGIFADDR, req)
        except OSError:  # EADDRNOTAVAIL: interface has no IPv4 address
            return None
    # sockaddr_in starts at byte 16: family (2 bytes), port (2 bytes), address (4 bytes)
    return socket.inet_ntoa(res[20:24])


def _has_carrier(iface: str) -> bool:
    # sysfs "flags" only holds admin-set flags; the kernel's link state (RUNNING) lives in
    # "carrier": 1 = link, 0 = no link. Reading it fails if the interface is down.
    try:
        return (SYS_NET / iface / "carrier").read_text().strip() == "1"
    except OSError:
        return False


def _inspect(iface: str) -> tuple[str | None, str, str | None]:
    """Return (address or None, detail, hint) for one interface."""
    flags = int((SYS_NET / iface / "flags").read_text(), 16)
    if not flags & IFF_UP:
        return None, f"{iface} is down", f"Bring it up: sudo ip link set {iface} up"
    if not _has_carrier(iface):
        return None, f"{iface} is up but has no link", "Check the cable or Wi-Fi connection"
    addr = ipv4_address(iface)
    if addr is None:
        return None, f"{iface} has no IPv4 address", \
            "Link works but no address was assigned (DHCP failed?). Check: ip addr"
    return addr, f"{iface} up, {addr}", None


def check_interface() -> CheckResult:
    name = "Interface"
    try:
        ifaces = sorted(p.name for p in SYS_NET.iterdir() if p.name != "lo")
    except OSError:
        return CheckResult(name, Status.SKIP, "cannot read /sys/class/net (not Linux?)")
    if not ifaces:
        return CheckResult(name, Status.FAIL, "no network interfaces besides loopback",
                           hint="No network adapter found. On WSL: run 'wsl --shutdown' in "
                                "Windows and reopen")

    # Prefer the interface the default route uses; without one, any working interface will do.
    route = default_route()
    candidates = [route[0]] if route and route[0] in ifaces else ifaces
    first_problem = None
    for iface in candidates:
        addr, detail, hint = _inspect(iface)
        if addr:
            return CheckResult(name, Status.OK, detail)
        first_problem = first_problem or (detail, hint)
    return CheckResult(name, Status.FAIL, first_problem[0], hint=first_problem[1])
