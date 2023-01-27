import hashlib
import json

from dcqc.file import File
from dcqc.tests.test_abc import ExternalTestMixin, Process, TestABC, TestStatus


class FileExtensionTest(TestABC):
    tier = 1
    only_one_file_targets = False

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.target.files:
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
        for file in self.target.files:
            expected_md5 = file.get_metadata("md5_checksum")
            actual_md5 = self._compute_md5_checksum(file)
            if expected_md5 != actual_md5:
                status = TestStatus.FAIL
                break
        return status

    def _compute_md5_checksum(self, file: File) -> str:
        local_path = file.get_local_path()
        hash_md5 = hashlib.md5()
        with local_path.open("rb") as infile:
            for chunk in iter(lambda: infile.read(4096), b""):
                hash_md5.update(chunk)
        actual_md5 = hash_md5.hexdigest()
        return actual_md5


class JsonLoadTest(TestABC):
    tier = 2
    only_one_file_targets = False

    def compute_status(self) -> TestStatus:
        status = TestStatus.PASS
        for file in self.target.files:
            if not self._can_be_loaded(file):
                status = TestStatus.FAIL
                break
        return status

    def _can_be_loaded(self, file: File) -> bool:
        success = True
        local_path = file.get_local_path()
        with local_path.open("r") as infile:
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
        for file in self.target.files:
            if not self._can_be_loaded(file):
                status = TestStatus.FAIL
                break
        return status

    def _can_be_loaded(self, file: File) -> bool:
        rdflib = self.import_module("rdflib")
        graph = rdflib.Graph()

        success = True
        local_path = file.get_local_path()
        with local_path.open("r") as infile:
            try:
                graph.parse(infile, format="json-ld")
            except Exception:
                success = False
        return success


class LibTiffInfoTest(ExternalTestMixin, TestABC):
    tier = 2

    def generate_process(self) -> Process:
        file = self._get_single_target_file()
        path = file.get_local_path().as_posix()
        command_args = ["tiffinfo", path]
        process = Process(
            container="quay.io/brunograndephd/libtiff:2.0",
            command_args=command_args,
        )
        return process


class BioFormatsInfoTest(ExternalTestMixin, TestABC):
    tier = 2

    def generate_process(self) -> Process:
        file = self._get_single_target_file()
        path = file.get_local_path().as_posix()
        command_args = [
            "/opt/bftools/showinf",
            "-nopix",
            "-novalid",
            "-nocore",
            path,
        ]
        process = Process(
            container="openmicroscopy/bftools:latest",
            command_args=command_args,
        )
        return process


class OmeXmlSchemaTest(ExternalTestMixin, TestABC):
    tier = 2

    def generate_process(self) -> Process:
        file = self._get_single_target_file()
        path = file.get_local_path().as_posix()
        command_args = [
            "/opt/bftools/xmlvalid",
            path,
        ]
        process = Process(
            container="openmicroscopy/bftools:latest",
            command_args=command_args,
        )
        return process
