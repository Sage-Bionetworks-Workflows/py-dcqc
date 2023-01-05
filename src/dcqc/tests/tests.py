import hashlib

from dcqc.enums import TestStatus
from dcqc.file import File
from dcqc.tests.test_abc import TestABC


class FileExtensionTest(TestABC):
    def compute_status(self):
        status = TestStatus.PASS
        for file in self.target.files:
            file_type = file.get_file_type()
            file_extensions = file_type.file_extensions
            if not file.url.endswith(file_extensions):
                status = TestStatus.FAIL
                break
        return status


class Md5ChecksumTest(TestABC):
    def compute_status(self):
        status = TestStatus.PASS
        for file in self.target.files:
            expected_md5 = file.get_metadata("md5_checksum")
            actual_md5 = self._compute_md5_checksum(file)
            if expected_md5 != actual_md5:
                status = TestStatus.FAIL
                break
        return status

    def _compute_md5_checksum(self, file: File):
        local_path = file.get_local_path()
        hash_md5 = hashlib.md5()
        with open(local_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        actual_md5 = hash_md5.hexdigest()
        return actual_md5


class LibTiffInfoTest(TestABC):
    pass


class OmeXmlSchemaTest(TestABC):
    pass


class BioFormatsInfoTest(TestABC):
    pass
