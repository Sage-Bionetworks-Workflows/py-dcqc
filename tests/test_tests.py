from dcqc.enums import TestStatus
from dcqc.target import Target
from dcqc.tests.tests import FileExtensionTest, Md5ChecksumTest


def test_that_the_file_extension_test_works_on_correct_files(test_files):
    good_file, _ = test_files
    target = Target(good_file)
    test = FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_file_extension_test_works_on_incorrect_files(test_files):
    good_file, bad_file = test_files
    target = Target(good_file, bad_file)
    test = FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_md5_checksum_test_works_on_correct_files(test_files):
    good_file, _ = test_files
    target = Target(good_file)
    test = Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_md5_checksum_test_works_on_incorrect_files(test_files):
    good_file, bad_file = test_files
    target = Target(good_file, bad_file)
    test = Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL
