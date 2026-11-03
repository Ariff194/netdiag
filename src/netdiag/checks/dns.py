import random
import socket
import struct
import time

from netdiag.models import CheckResult, Status

QTYPE_A = 1
QCLASS_IN = 1
RCODES = {0: "NOERROR", 1: "FORMERR", 2: "SERVFAIL", 3: "NXDOMAIN", 4: "NOTIMP", 5: "REFUSED"}


class DNSError(Exception):
    """The reply was malformed or was not an answer to our query."""


def encode_name(name: str) -> bytes:
    # "www.example.com" -> b"\x03www\x07example\x03com\x00"
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")  # non-ASCII raises UnicodeEncodeError (a ValueError)
        if not 1 <= len(raw) <= 63:
            raise ValueError(f"invalid label {label!r} in {name!r}")
        out += bytes([len(raw)]) + raw
    return out + b"\x00"


def build_query(name: str, txid: int, qtype: int = QTYPE_A) -> bytes:
    # Header: ID, flags, QDCOUNT, ANCOUNT, NSCOUNT, ARCOUNT (six 16-bit big-endian ints)
    flags = 0x0100  # RD=1: ask the resolver to do the full recursive lookup for us
    header = struct.pack("!HHHHHH", txid, flags, 1, 0, 0, 0)
    return header + encode_name(name) + struct.pack("!HH", qtype, QCLASS_IN)


def read_name(msg: bytes, offset: int) -> tuple[str, int]:
    """Return (name, offset of the byte just after the name where it started)."""
    labels = []
    resume = None  # set when we follow the first compression pointer
    jumps = 0
    while True:
        if offset >= len(msg):
            raise DNSError("name runs past end of message")
        length = msg[offset]
        if length & 0xC0 == 0xC0:
            # Top two bits set: the next 14 bits are an offset to the rest of the name.
            if offset + 1 >= len(msg):
                raise DNSError("truncated compression pointer")
            if resume is None:
                resume = offset + 2  # a pointer is always the end of a name, and is 2 bytes
            offset = ((length & 0x3F) << 8) | msg[offset + 1]
            jumps += 1
            if jumps > 20:
                raise DNSError("compression pointer loop")
            continue
        if length & 0xC0:
            raise DNSError(f"unsupported label type 0x{length:02x}")
        if length == 0:
            offset += 1
            break
        labels.append(msg[offset + 1:offset + 1 + length].decode("ascii", errors="replace"))
        offset += 1 + length
    return ".".join(labels), (resume if resume is not None else offset)


def parse_response(msg: bytes, txid: int) -> tuple[int, bool, list[str]]:
    """Return (rcode, truncated, IPv4 addresses from the answer section)."""
    if len(msg) < 12:
        raise DNSError("reply shorter than a DNS header")
    rid, flags, qdcount, ancount, _nscount, _arcount = struct.unpack("!HHHHHH", msg[:12])
    if rid != txid:
        raise DNSError(f"ID mismatch (sent {txid}, got {rid})")
    if not flags & 0x8000:
        raise DNSError("QR bit not set, so this is not a response")
    truncated = bool(flags & 0x0200)
    rcode = flags & 0x000F

    offset = 12
    for _ in range(qdcount):  # the server echoes our question back; skip over it
        _, offset = read_name(msg, offset)
        offset += 4  # QTYPE + QCLASS

    addresses = []
    for _ in range(ancount):
        _, offset = read_name(msg, offset)
        if offset + 10 > len(msg):
            raise DNSError("truncated answer record")
        rtype, rclass, _ttl, rdlength = struct.unpack("!HHIH", msg[offset:offset + 10])
        offset += 10
        rdata = msg[offset:offset + rdlength]
        if len(rdata) != rdlength:
            raise DNSError("answer data runs past end of message")
        offset += rdlength
        # Skip CNAMEs and anything else; the A records for the final name follow them.
        if rtype == QTYPE_A and rclass == QCLASS_IN and rdlength == 4:
            addresses.append(socket.inet_ntoa(rdata))
    return rcode, truncated, addresses


def system_resolver(path: str = "/etc/resolv.conf") -> str | None:
    try:
        with open(path) as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[0] == "nameserver":
                    return parts[1]
    except OSError:
        pass
    return None


def check_dns(host: str, server: str | None = None, timeout: float = 3.0) -> CheckResult:
    name = "DNS lookup"
    server = server or system_resolver()
    if server is None:
        return CheckResult(name, Status.FAIL, "no nameserver configured",
                           hint="No 'nameserver' line in /etc/resolv.conf. Try: --server 1.1.1.1")
    txid = random.getrandbits(16)
    try:
        query = build_query(host, txid)
    except ValueError as e:
        return CheckResult(name, Status.FAIL, f"invalid hostname: {e}")

    family = socket.AF_INET6 if ":" in server else socket.AF_INET
    start = time.perf_counter()
    try:
        with socket.socket(family, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.sendto(query, (server, 53))
            reply, _ = s.recvfrom(512)  # classic DNS-over-UDP size limit
    except TimeoutError:
        return CheckResult(name, Status.FAIL, f"no reply from {server} within {timeout:g}s",
                           hint="Resolver down or UDP/53 blocked. Try: ping <server>, or --server 1.1.1.1")
    except OSError as e:
        return CheckResult(name, Status.FAIL, f"cannot reach resolver {server}: {e.strerror or e}",
                           hint="No route to the resolver. Check your connection and: ip route")
    ms = (time.perf_counter() - start) * 1000

    try:
        rcode, truncated, addresses = parse_response(reply, txid)
    except DNSError as e:
        return CheckResult(name, Status.FAIL, f"bad reply from {server}: {e}", latency_ms=ms,
                           hint="Resolver sent something that isn't a valid answer. Try another --server")
    if rcode == 3:
        return CheckResult(name, Status.FAIL, f"{host} does not exist (NXDOMAIN)", latency_ms=ms,
                           hint="Check the spelling. Compare with: dig <host> @1.1.1.1")
    if rcode != 0:
        return CheckResult(name, Status.FAIL, f"{server} answered {RCODES.get(rcode, rcode)}",
                           latency_ms=ms,
                           hint="Resolver could not answer. SERVFAIL often means the domain's own "
                                "nameservers are broken. Try another --server")
    if addresses:
        return CheckResult(name, Status.OK, f"{host} -> {', '.join(addresses)} (via {server})",
                           latency_ms=ms)
    if truncated:
        return CheckResult(name, Status.WARN, "reply truncated before any A record", latency_ms=ms,
                           hint="Answer too big for UDP; real resolvers retry over TCP (not implemented)")
    return CheckResult(name, Status.WARN, f"{host} exists but has no A (IPv4) record", latency_ms=ms,
                       hint="Name resolves, but not to IPv4. Maybe IPv6-only? Try: dig AAAA <host>")
