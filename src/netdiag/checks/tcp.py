import errno
import socket
import time

from netdiag.models import CheckResult, Status


def check_tcp(host: str, port: int, timeout: float = 3.0) -> CheckResult:
    name = "TCP connect"
    target = f"{host}:{port}"
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass  # handshake succeeded; we close immediately
    except OSError as e:
        ms = (time.perf_counter() - start) * 1000
        detail, hint = _classify(e, target, timeout)
        return CheckResult(name, Status.FAIL, detail, latency_ms=ms, hint=hint)
    ms = (time.perf_counter() - start) * 1000
    return CheckResult(name, Status.OK, f"{target} accepted connection", latency_ms=ms)


def _classify(e: OSError, target: str, timeout: float) -> tuple[str, str | None]:
    # Order matters: these are all subclasses of OSError, so check specific ones first.
    if isinstance(e, socket.gaierror): #getaddrinfo error
        return (f"cannot resolve host in {target}",
                "DNS lookup failed. Check the spelling, then try: dig <host>")
    if isinstance(e, ConnectionRefusedError):
        return (f"{target} refused (got RST)",
                "Host is up but nothing is listening on that port. Service down or wrong port?")
    if isinstance(e, TimeoutError):
        return (f"{target} no reply within {timeout:g}s",
                "Packets silently dropped (firewall?) or host is down. Try: ping, traceroute")
    if e.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH):
        return (f"{target} unreachable ({e.strerror})",
                "No route to that network/host. Check your connection and: ip route")
    return (f"{target} error: {e}", None)