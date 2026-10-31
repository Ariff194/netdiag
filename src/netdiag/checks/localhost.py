import socket
import time

from netdiag.models import CheckResult, Status


def check_localhost() -> CheckResult:
    name = "Resolve localhost"
    start = time.perf_counter()
    try:
        ip = socket.gethostbyname("localhost")
    except socket.gaierror as e:
        return CheckResult(name, Status.FAIL, str(e),
                           hint="Name resolution is broken locally. Check /etc/hosts.")
    ms = (time.perf_counter() - start) * 1000
    return CheckResult(name, Status.OK, f"localhost -> {ip}", latency_ms=ms)