import hashlib
from pathlib import Path

from dcqc.target import BaseTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus


class Md5ChecksumTest(InternalBaseTest):
    tier = 1
    target: BaseTarget

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.target.files:
            path = file.stage()
            expected_md5 = file.get_metadata("md5_checksum")
            actual_md5 = self._compute_md5_checksum(path)
            if expected_md5 != actual_md5:
                status = TestStatus.FAIL
                break
        return status

    def _compute_md5_checksum(self, path: Path) -> str:
        hash_md5 = hashlib.md5()
        with path.open("rb") as infile:
            for chunk in iter(lambda: infile.read(4096), b""):
                hash_md5.update(chunk)
        actual_md5 = hash_md5.hexdigest()
        return actual_md5
