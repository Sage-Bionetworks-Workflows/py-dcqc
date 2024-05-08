import pytest

from dcqc import tests
from dcqc.target import PairedTarget
from dcqc.tests import BaseTest, TestStatus


def test_that_the_a_test_can_be_correctly_retrieved_by_name():
    test = BaseTest.get_subclass_by_name("Md5ChecksumTest")
    assert test is tests.Md5ChecksumTest


def test_for_an_error_when_retrieving_a_test_that_does_not_exist_by_name():
    with pytest.raises(ValueError):
        BaseTest.get_subclass_by_name("FooBar")


def test_for_error_when_importing_unavailable_module(test_targets):
    target = test_targets["good_txt"]
    test = tests.FileExtensionTest(target)
    with pytest.raises(ModuleNotFoundError):
        test.import_module("foobar")


def test_that_an_existing_module_can_be_imported(test_targets):
    target = test_targets["good_txt"]
    test = tests.FileExtensionTest(target)
    imported = test.import_module("pytest")
    assert imported is pytest


class TestFileExtensionTest:
    @pytest.fixture(scope="function", autouse=True)
    def setup_method(self, test_targets):
        self.good_txt_target = test_targets["good_txt"]
        self.good_txt_test = tests.FileExtensionTest(self.good_txt_target)
        self.good_tiff_target = test_targets["good_tiff"]
        self.good_tiff_test = tests.FileExtensionTest(self.good_tiff_target)
        self.remote_file_target = test_targets["remote"]
        self.remote_file_test = tests.FileExtensionTest(self.remote_file_target)
        self.bad_txt_target = test_targets["wrong_file_type_and_md5_txt"]
        self.bad_txt_test = tests.FileExtensionTest(self.bad_txt_target)

    def test_that_the_file_extension_test_works_on_correct_files(self):
        assert self.good_txt_test.get_status() == TestStatus.PASS

    def test_that_the_file_extension_test_works_on_correct_remote_file(self):
        assert self.remote_file_test.get_status() == TestStatus.PASS

    def test_that_a_tiff_file_with_good_extensions_is_passed(self):
        assert self.good_tiff_test.get_status() == TestStatus.PASS

    def test_that_the_file_extension_test_works_on_incorrect_files(self):
        assert self.bad_txt_test.get_status() == TestStatus.FAIL
        assert self.bad_txt_test.failure_reason == (
            "File extension does not match one of: "
            f"{self.bad_txt_target.get_file_type().file_extensions}"
        )


class Md5ChecksumTest:
    @pytest.fixture(scope="function", autouse=True)
    def setup_method(self, test_targets):
        self.good_txt_target = test_targets["good_txt"]
        self.good_txt_test = tests.Md5ChecksumTest(self.good_txt_target)
        self.bad_txt_target = test_targets["wrong_file_type_and_md5_txt"]
        self.bad_txt_test = tests.Md5ChecksumTest(self.bad_txt_target)

    def test_that_the_md5_checksum_test_works_on_a_correct_file(self):
        assert self.good_txt_test.get_status() == TestStatus.PASS

    def test_that_the_md5_checksum_test_works_on_incorrect_files(self):
        assert self.bad_txt_test.get_status() == TestStatus.FAIL
        assert (
            self.bad_txt_test.failure_reason
            == "Computed MD5 checksum does not match provided value"
        )


class TestJsonLoadTest:
    @pytest.fixture(scope="function", autouse=True)
    def setup_method(self, test_targets):
        self.good_jsonld_target = test_targets["good_jsonld"]
        self.good_jsonld_test = tests.JsonLoadTest(self.good_jsonld_target)
        self.good_txt_target = test_targets["good_txt"]
        self.good_txt_test = tests.JsonLoadTest(self.good_txt_target)

    def test_that_the_json_load_test_works_on_a_correct_file(self):
        assert self.good_jsonld_test.get_status() == TestStatus.PASS

    def test_that_the_json_load_test_works_on_incorrect_files(self):
        assert self.good_txt_test.get_status() == TestStatus.FAIL
        assert (
            self.good_txt_test.failure_reason
            == "File content is unable to be loaded as JSON"
        )


class TestJsonLdLoadTest:
    @pytest.fixture(scope="function", autouse=True)
    def setup_method(self, test_targets):
        self.good_jsonld_target = test_targets["good_jsonld"]
        self.good_jsonld_test = tests.JsonLdLoadTest(self.good_jsonld_target)
        self.good_txt_target = test_targets["good_txt"]
        self.good_txt_test = tests.JsonLdLoadTest(self.good_txt_target)

    def test_that_the_jsonld_load_test_works_on_a_correct_file(self):
        assert self.good_jsonld_test.get_status() == TestStatus.PASS

    def test_that_the_jsonld_load_test_works_on_incorrect_files(self):
        assert self.good_txt_test.get_status() == TestStatus.FAIL
        assert (
            self.good_txt_test.failure_reason
            == "File content is unable to be loaded as JSON-LD"
        )


class TestPairedFastqParityTest:
    @pytest.fixture(scope="function", autouse=True)
    def setup_method(self, test_files):
        self.fastq1_file = test_files["good_fastq"]
        self.fastq2_file = test_files["good_compressed_fastq"]
        self.good_txt_file = test_files["good_txt"]
        self.good_paired_target = PairedTarget([self.fastq1_file, self.fastq1_file])
        self.good_paired_test = tests.PairedFastqParityTest(self.good_paired_target)
        self.bad_paired_target = PairedTarget([self.fastq1_file, self.fastq2_file])
        self.bad_paired_test = tests.PairedFastqParityTest(self.bad_paired_target)
        self.good_compressed_paired_target = PairedTarget(
            [self.fastq2_file, self.fastq2_file]
        )
        self.good_compressed_paired_test = tests.PairedFastqParityTest(
            self.good_compressed_paired_target
        )
        self.good_txt_target = PairedTarget([self.good_txt_file, self.good_txt_file])
        self.good_txt_test = tests.PairedFastqParityTest(self.good_txt_target)

    def test_that_paired_fastq_parity_test_correctly_passes_identical_fastq_files(
        self,
    ):
        assert self.good_paired_test.get_status() == TestStatus.PASS

    def test_that_paired_fastq_parity_test_correctly_handles_compressed_fastq_files(
        self,
    ):
        assert self.good_compressed_paired_test.get_status() == TestStatus.PASS

    def test_that_paired_fastq_parity_test_correctly_fails_different_fastq_files(
        self,
    ):
        assert self.bad_paired_test.get_status() == TestStatus.FAIL
        assert (
            self.bad_paired_test.failure_reason
            == "FASTQ files do not have the same number of lines"
        )
