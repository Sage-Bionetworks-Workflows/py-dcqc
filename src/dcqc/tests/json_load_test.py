import json
from pathlib import Path

from dcqc.target import BaseTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus


class JsonLoadTest(InternalBaseTest):
    tier = 2
    target: BaseTarget

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.target.files:
            path = file.stage()
            if not self._can_be_loaded(path):
                status = TestStatus.FAIL
                break
        return status

    def _can_be_loaded(self, path: Path) -> bool:
        success = True
        with path.open("r") as infile:
            try:
                json.load(infile)
            except Exception:
                success = False
        return success
