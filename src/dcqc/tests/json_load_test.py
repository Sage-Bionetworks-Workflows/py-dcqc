import json
from pathlib import Path

from dcqc.target import SingleTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus, TestTier


class JsonLoadTest(InternalBaseTest):
    """Tests if a file can be loaded as JSON."""

    tier = TestTier.INTERNAL_CONFORMANCE
    target: SingleTarget

    def compute_status(self) -> TestStatus:
        path = self.target.file.stage()
        if self._can_be_loaded(path):
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
            self.status_reason = "File content is unable to be loaded as JSON"
        return status

    def _can_be_loaded(self, path: Path) -> bool:
        success = True
        with path.open("r") as infile:
            try:
                json.load(infile)
            except Exception:
                success = False
        return success
