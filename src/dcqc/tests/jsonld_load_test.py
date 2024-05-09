from pathlib import Path

from dcqc.target import SingleTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus


class JsonLdLoadTest(InternalBaseTest):
    """Tests if a file can be loaded as JSON-LD."""

    tier = 2
    target: SingleTarget

    def compute_status(self) -> TestStatus:
        path = self.target.file.stage()
        if self._can_be_loaded(path):
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
            self.status_reason = "File content is unable to be loaded as JSON-LD"
        return status

    def _can_be_loaded(self, path: Path) -> bool:
        rdflib = self.import_module("rdflib")
        graph = rdflib.Graph()

        success = True
        with path.open("r") as infile:
            try:
                graph.parse(infile, format="json-ld")
            except Exception:
                success = False
        return success
