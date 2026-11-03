import argparse

from netdiag.checks.dns import check_dns
from netdiag.checks.http import check_http, parse_url
from netdiag.checks.localhost import check_localhost
from netdiag.checks.tcp import check_tcp
from netdiag.models import CheckResult, Status


def print_result(r: CheckResult) -> None:
    latency = f" ({r.latency_ms:.1f} ms)" if r.latency_ms is not None else ""
    print(f"[{r.status.value:<4}] {r.name:<20} {r.detail}{latency}")
    if r.hint:
        print(f"       Hint: {r.hint}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="netdiag",
                                     description="Diagnose network problems layer by layer.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest", help="Check that netdiag itself works")
    
    tcp_p = sub.add_parser("tcp", help="Test a TCP connection to HOST PORT")
    tcp_p.add_argument("host")
    tcp_p.add_argument("port", type=int)
    tcp_p.add_argument("--timeout", type=float, default=3.0)

    http_p = sub.add_parser("http", help="Check a URL layer by layer (TCP, then HTTP)")
    http_p.add_argument("url")
    http_p.add_argument("--timeout", type=float, default=5.0)

    dns_p = sub.add_parser("dns", help="Resolve HOST using netdiag's own DNS client")
    dns_p.add_argument("host")
    dns_p.add_argument("--server",
                      help="DNS server IP (default: first nameserver in /etc/resolv.conf)")
    dns_p.add_argument("--timeout", type=float, default=3.0)

    args = parser.parse_args()

    if args.command == "selftest":
        print_result(check_localhost())
    elif args.command == "tcp":
        print_result(check_tcp(args.host, args.port, args.timeout))
    elif args.command == "http":
        try:
            scheme, host, port, path = parse_url(args.url)
        except ValueError as e:
            parser.error(str(e))
        tcp = check_tcp(host, port, args.timeout)
        print_result(tcp)
        if tcp.status is Status.OK:
            print_result(check_http(scheme, host, port, path, args.timeout))
        else:
            print_result(CheckResult("HTTP GET", Status.SKIP, "skipped: TCP connect failed"))
    elif args.command == "dns":
        print_result(check_dns(args.host, args.server, args.timeout))