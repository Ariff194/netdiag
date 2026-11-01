from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str
    latency_ms: float | None = None
    hint: str | None = None