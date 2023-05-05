import hashlib
import json
from pathlib import Path

from dcqc.tests.test_abc import ExternalTestMixin, Process, TestABC, TestStatus


class FileExtensionTest(TestABC):
    tier = 1
    only_one_file_targets = False

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.get_files(staged=False):
            file_type = file.get_file_type()
            file_extensions = file_type.file_extensions
            if not file.name.endswith(file_extensions):
                status = TestStatus.FAIL
                break
        return status


class Md5ChecksumTest(TestABC):
    tier = 1
    only_one_file_targets = False

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.get_files():
            expected_md5 = file.get_metadata("md5_checksum")
            actual_md5 = self._compute_md5_checksum(file.local_path)
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


class JsonLoadTest(TestABC):
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


class JsonLdLoadTest(TestABC):
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
        rdflib = self.import_module("rdflib")
        graph = rdflib.Graph()

        success = True
        with path.open("r") as infile:
            try:
                graph.parse(infile, format="json-ld")
            except Exception:
                success = False
        return success


class LibTiffInfoTest(ExternalTestMixin, TestABC):
    tier = 2

    def generate_process(self) -> Process:
        file = self.get_file()
        command_args = ["tiffinfo", file.local_path.as_posix()]
        process = Process(
            container="quay.io/sagebionetworks/libtiff:2.0",
            command_args=command_args,
        )
        return process


class BioFormatsInfoTest(ExternalTestMixin, TestABC):
    tier = 2

    def generate_process(self) -> Process:
        file = self.get_file()
        command_args = [
            "/opt/bftools/showinf",
            "-nopix",
            "-novalid",
            "-nocore",
            file.local_path.as_posix(),
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process


class OmeXmlSchemaTest(ExternalTestMixin, TestABC):
    tier = 2

    def generate_process(self) -> Process:
        file = self.get_file()
        command_args = [
            "/opt/bftools/xmlvalid",
            file.local_path.as_posix(),
        ]
        process = Process(
            container="quay.io/sagebionetworks/bftools:latest",
            command_args=command_args,
        )
        return process


class GrepDateTest(ExternalTestMixin, TestABC):
    tier = 4

    def generate_process(self) -> Process:
        file = self.get_file()
        path = file.local_path.as_posix()
        command_args = [
            "!" "grep",  # negate exit status
            "-E",  # extended regular expression
            "-i",  # case insensitive
            "-a",  # treat input as text
            "-q",  # suppress output
            "'date|time'",  # match date or time
            path,
        ]
        process = Process(
            container="quay.io/biocontainers/coreutils:8.30--h14c3975_1000",
            command_args=command_args,
        )
        return process


class TiffTag306DateTimeTest(ExternalTestMixin, TestABC):
    tier = 4

    def generate_process(self) -> Process:
        file = self.get_file()
        path = file.local_path.as_posix()
        command_args = [
            "!",  # negate exit status
            "tifftools",
            "dump",
            path,
            "|",
            "grep",  # pipe the output
            "-a",  # treat input as text
            "-q",  # suppress output
            r"'DateTime 306 \(0x132\) ASCII'",  # match the DateTime 306 tag
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/tifftools:latest",
            command_args=command_args,
        )
        return process
