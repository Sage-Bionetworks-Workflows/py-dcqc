import pytest

from dcqc.file import FileType
from dcqc.suites.suite_abc import SuiteABC
from dcqc.suites.suites import FileSuite, OmeTiffSuite, TiffSuite
from dcqc.tests.test_abc import TestABC, TestStatus
from dcqc.tests.tests import (
    FileExtensionTest,
    GrepDateTest,
    LibTiffInfoTest,
    TiffTag306DateTimeTest,
)

FileType("None", ())
FileType("Unpaired", ())


class RedundantFileSuite(TiffSuite):
    file_type = FileType.get_file_type("None")
    del_tests = (LibTiffInfoTest, GrepDateTest, TiffTag306DateTimeTest)


class DummyTest(TestABC):
    def compute_status(self) -> TestStatus:
        return TestStatus.NONE


def test_that_a_file_suite_results_in_multiple_tests():
    tests = FileSuite.list_test_classes()
    assert len(tests) > 0
    assert all(issubclass(test, TestABC) for test in tests)


def test_that_deleting_a_just_added_test_results_in_the_same_test_list():
    tests_1 = FileSuite.list_test_classes()
    tests_2 = RedundantFileSuite.list_test_classes()
    assert set(tests_1) == set(tests_2)


def test_that_the_ome_tiff_suite_has_a_superset_of_the_tiff_suite_tests():
    tiff_tests = TiffSuite.list_test_classes()
    ome_tiff_tests = OmeTiffSuite.list_test_classes()
    assert set(ome_tiff_tests) > set(tiff_tests)


def test_that_a_test_suite_can_be_retrieved_by_name():
    actual = SuiteABC.get_subclass_by_name("OmeTiffSuite")
    assert actual is OmeTiffSuite


def test_for_an_error_when_retrieving_a_nonexistent_test_suite_by_name():
    with pytest.raises(ValueError):
        SuiteABC.get_subclass_by_name("FooBarSuite")


def test_that_a_test_suite_can_be_retrieved_by_file_type_class():
    file_type = FileType.get_file_type("OME-TIFF")
    actual = SuiteABC.get_subclass_by_file_type(file_type)
    assert actual is OmeTiffSuite


def test_that_a_test_suite_can_be_retrieved_by_file_type_str():
    actual = SuiteABC.get_subclass_by_file_type("OME-TIFF")
    assert actual is OmeTiffSuite


def test_that_the_generic_file_suite_is_retrieved_for_a_random_file_type():
    actual = SuiteABC.get_subclass_by_file_type("Foo-Bar")
    assert actual is FileSuite


def test_that_the_generic_file_suite_is_retrieved_for_an_unpaired_file_type():
    actual = SuiteABC.get_subclass_by_file_type("Unpaired")
    assert actual is FileSuite


def test_that_the_default_required_tests_are_only_tiers_1_and_2(test_suites):
    suite = test_suites["jsonld"]
    assert all(test.tier <= 2 for test in suite.tests)


def test_that_skipped_tests_are_skipped_when_building_suite_from_tests(test_suites):
    suite = test_suites["tiff"]
    tests = suite.tests
    new_suite = SuiteABC.from_tests(tests, skipped_tests=["LibTiffInfoTest"])
    skipped_test_before = suite.tests_by_name["LibTiffInfoTest"]
    skipped_test_after = new_suite.tests_by_name["LibTiffInfoTest"]
    assert skipped_test_before.get_status(compute_ok=False) != TestStatus.SKIP
    assert skipped_test_after.get_status(compute_ok=False) == TestStatus.SKIP


def test_for_an_error_when_building_suite_from_tests_with_diff_targets(test_targets):
    target_1 = test_targets["good"]
    target_2 = test_targets["bad"]
    test_1 = FileExtensionTest(target_1)
    test_2 = FileExtensionTest(target_2)
    tests = [test_1, test_2]
    with pytest.raises(ValueError):
        SuiteABC.from_tests(tests)


def test_that_a_suite_will_not_consider_unrequired_tests(test_targets):
    target = test_targets["bad"]
    required_tests = []
    skipped_tests = ["LibTiffInfoTest", "GrepDateTest", "TiffTag306DateTimeTest"]
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)
    suite_status = suite.compute_status()
    assert suite_status == TestStatus.PASS


def test_that_a_suite_will_consider_required_tests_when_failing(test_targets):
    target = test_targets["bad"]
    required_tests = ["FileExtensionTest"]
    skipped_tests = ["LibTiffInfoTest", "GrepDateTest", "TiffTag306DateTimeTest"]
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)
    suite_status = suite.compute_status()
    assert suite_status == TestStatus.FAIL


def test_that_a_suite_will_consider_required_tests_when_passing(test_targets):
    target = test_targets["good"]
    required_tests = ["Md5ChecksumTest"]
    suite = SuiteABC.from_target(target, required_tests)
    suite_status = suite.compute_status()
    assert suite_status == TestStatus.PASS
