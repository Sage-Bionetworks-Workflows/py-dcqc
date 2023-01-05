from enum import Enum


class TestStatus(Enum):
    NONE = "pending"
    FAIL = "failed"
    PASS = "passed"
    SKIP = "skipped"

    # def __bool__(self):
    #     true_values = {"passed", "skipped"}
    #     return self.value in true_values
