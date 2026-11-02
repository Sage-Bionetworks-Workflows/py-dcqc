import hashlib
from pathlib import Path

from dcqc.target import BaseTarget
from dcqc.tests.base_test import InternalBaseTest, TestStatus, TestTier


class Md5ChecksumTest(InternalBaseTest[BaseTarget]):
    """Tests if a file has the expected MD5 checksum."""

    tier = TestTier.FILE_INTEGRITY

    def compute_status(self) -> TestStatus:
<<<<<<< HEAD
        """Check the MD5 checksum of every file against its metadata.

        All files are checked, also after a file fails, so that the metrics
        hold the computed checksum of every file that does not match. The
        metrics map the URL of each such file to its computed checksum, under the
        md5_checksum key.

        Returns:
            TestStatus.PASS if all checksums match, otherwise TestStatus.FAIL.
        """
        mismatches: dict[str, str] = {}
        for file in self.target.files:
            path = file.stage()
            expected_md5 = file.get_metadata("md5_checksum")
            actual_md5 = self._compute_md5_checksum(path)
            if expected_md5 != actual_md5:
                mismatches[file.url] = actual_md5
        if not mismatches:
            return TestStatus.PASS
        self.status_reason = "Computed MD5 checksum does not match provided value"
        self.metrics["md5_checksum"] = mismatches
        return TestStatus.FAIL
=======
        path = self.target.file.stage()
        expected_md5 = self.target.file.get_metadata("md5_checksum")
        actual_md5 = self._compute_md5_checksum(path)
        if expected_md5 == actual_md5:
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
            self.status_reason = "Computed MD5 checksum does not match provided value"
            self.metrics["md5_checksum"] = actual_md5
        return status
>>>>>>> DPE-1821

    def _compute_md5_checksum(self, path: Path) -> str:
        hash_md5 = hashlib.md5()
        with path.open("rb") as infile:
            for chunk in iter(lambda: infile.read(4096), b""):
                hash_md5.update(chunk)
        actual_md5 = hash_md5.hexdigest()
        return actual_md5
