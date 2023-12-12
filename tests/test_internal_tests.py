import pytest

from dcqc import tests
from dcqc.target import PairedTarget
from dcqc.tests import BaseTest, TestStatus


def test_that_the_file_extension_test_works_on_correct_files(test_targets):
    target = test_targets["good_txt"]
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_file_extension_test_works_on_correct_remote_file(test_targets):
    target = test_targets["remote"]
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_a_tiff_file_with_good_extensions_is_passed(test_targets):
    target = test_targets["tiff"]
    test = tests.FileExtensionTest(target)
    assert test.get_status() == TestStatus.PASS


def test_that_the_file_extension_test_works_on_incorrect_files(test_targets):
    target = test_targets["bad_txt"]
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_md5_checksum_test_works_on_a_correct_file(test_targets):
    target = test_targets["good_txt"]
    test = tests.Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_md5_checksum_test_works_on_incorrect_files(test_targets):
    target = test_targets["bad_txt"]
    test = tests.Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_json_load_test_works_on_a_correct_file(test_targets):
    target = test_targets["jsonld"]
    test = tests.JsonLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_json_load_test_works_on_incorrect_files(test_targets):
    target = test_targets["good_txt"]
    test = tests.JsonLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_jsonld_load_test_works_on_a_correct_file(test_targets):
    target = test_targets["jsonld"]
    test = tests.JsonLdLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_jsonld_load_test_works_on_incorrect_files(test_targets):
    target = test_targets["good_txt"]
    test = tests.JsonLdLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_md5_checksum_test_can_be_retrieved_by_name():
    test = BaseTest.get_subclass_by_name("Md5ChecksumTest")
    assert test is tests.Md5ChecksumTest


def test_for_an_error_when_retrieving_a_random_test_by_name():
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


def test_that_paired_fastq_parity_test_correctly_passes_identical_fastq_files(
    test_files,
):
    fastq1 = test_files["fastq1"]
    target = PairedTarget([fastq1, fastq1])
    test = tests.PairedFastqParityTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_paired_fastq_parity_test_correctly_fails_different_fastq_files(
    test_files,
):
    fastq1 = test_files["fastq1"]
    fastq2 = test_files["fastq2"]
    target = PairedTarget([fastq1, fastq2])
    test = tests.PairedFastqParityTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_paired_fastq_parity_test_correctly_handles_compressed_fastq_files(
    test_files,
):
    fastq2 = test_files["fastq2"]
    target = PairedTarget([fastq2, fastq2])
    test = tests.PairedFastqParityTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS
