import json
from pathlib import Path

from dcqc.tests.base import BaseTest, TestStatus


class JsonLoadTest(BaseTest):
    tier = 2
    only_one_file_targets = False

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.get_files():
            if not self._can_be_loaded(file.local_path):
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
