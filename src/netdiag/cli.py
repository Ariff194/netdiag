import argparse

from netdiag.checks.localhost import check_localhost
from netdiag.models import CheckResult


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
    args = parser.parse_args()

    if args.command == "selftest":
        print_result(check_localhost())