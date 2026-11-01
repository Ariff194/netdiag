import http.client
import ssl
import time
from urllib.parse import urlsplit

from netdiag.models import CheckResult, Status


def parse_url(url: str) -> tuple[str, str, int, str]:
    if "://" not in url:
        url = "http://" + url
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError(f"unsupported scheme: {parts.scheme}")
    if not parts.hostname:
        raise ValueError(f"no host in URL: {url}")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return parts.scheme, parts.hostname, port, path


def check_http(scheme: str, host: str, port: int, path: str,
               timeout: float = 5.0) -> CheckResult:
    name = "HTTP GET"
    conn_cls = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(host, port, timeout=timeout)
    start = time.perf_counter()
    try:
        conn.request("GET", path, headers={"User-Agent": "netdiag/0.1"})
        resp = conn.getresponse()
    except ssl.SSLError as e:  # must come before OSError (it's a subclass)
        return CheckResult(name, Status.FAIL, f"TLS failed: {e.reason or e}",
                           hint="TCP worked but the TLS handshake didn't. Check the cert or https vs http.")
    except TimeoutError:
        return CheckResult(name, Status.FAIL, f"no HTTP response within {timeout:g}s",
                           hint="Connected, but the server never answered. Server overloaded or stuck?")
    except (OSError, http.client.HTTPException) as e:
        return CheckResult(name, Status.FAIL, f"error: {e}")
    finally:
        conn.close()
    ms = (time.perf_counter() - start) * 1000

    detail = f"{resp.status} {resp.reason}"
    if resp.status < 400:
        return CheckResult(name, Status.OK, detail, latency_ms=ms)
    return CheckResult(name, Status.WARN, detail, latency_ms=ms,
                       hint="The network path is fine; the server answered with an error. "
                            "Check the URL or the app, not the network.")