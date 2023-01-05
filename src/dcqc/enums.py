from enum import Enum


class TestStatus(Enum):
    NONE = "pending"
    FAIL = "failed"
    PASS = "passed"
    SKIP = "skipped"
