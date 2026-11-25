from typing import Generic, TypeVar
from unittest.mock import patch

import pytest

from dcqc.file import File, FileType
from dcqc.suites.suite_abc import SuiteABC, SuiteStatus
from dcqc.suites.suites import FastqSuite, FileSuite, OmeTiffSuite, TiffSuite
from dcqc.target import BaseTarget, PairedTarget, SingleTarget
from dcqc.tests import (
    BaseTest,
    FileExtensionTest,
    LibTiffInfoTest,
    Md5ChecksumTest,
    PairedFastqParityTest,
    TestStatus,
    TiffDateTimeTest,
    TiffTag306DateTimeTest,
)
from dcqc.tests.base_test import ExternalBaseTest, InternalBaseTest

BoxValue = TypeVar("BoxValue")

FileType("None", ())
FileType("Unpaired", ())


class RedundantFileSuite(TiffSuite):
    file_type = FileType.get_file_type("None")
    del_tests = (LibTiffInfoTest, TiffDateTimeTest, TiffTag306DateTimeTest)


class DummyTest(BaseTest):
    def compute_status(self) -> TestStatus:
        return TestStatus.NONE


def test_that_a_file_suite_results_in_multiple_tests():
    tests = FileSuite.list_test_classes()
    assert len(tests) > 0
    assert all(issubclass(test, BaseTest) for test in tests)


def test_that_the_test_classes_are_sorted_by_name():
    tests = OmeTiffSuite.list_test_classes()
    test_names = [test.__name__ for test in tests]
    assert test_names == sorted(test_names)


def test_that_deleting_a_just_added_test_results_in_the_same_test_list():
    tests_1 = FileSuite.list_test_classes()
    tests_2 = RedundantFileSuite.list_test_classes()
    assert set(tests_1) == set(tests_2)


def test_that_the_ome_tiff_suite_has_a_superset_of_the_tiff_suite_tests():
    tiff_tests = TiffSuite.list_test_classes()
    ome_tiff_tests = OmeTiffSuite.list_test_classes()
    assert set(ome_tiff_tests) > set(tiff_tests)


def test_for_an_error_when_a_suite_is_given_a_type_argument() -> None:
    # GIVEN a suite class that is not generic
    # WHEN I define a suite with a type argument
    # THEN a TypeError is raised
    with pytest.raises(TypeError):

        class SubscriptedSuite(FileSuite[PairedTarget]):  # type: ignore
            file_type = FileType.get_file_type("None")


def test_that_the_default_test_target_class_is_base_target() -> None:
    # GIVEN the base test class and a test without a type argument
    # WHEN I get their target classes
    # THEN both are BaseTarget
    assert BaseTest.target_cls is BaseTarget
    assert DummyTest.target_cls is BaseTarget


def test_that_the_test_target_class_is_set_from_the_type_argument() -> None:
    # GIVEN tests with different type arguments
    # WHEN I get their target classes
    # THEN each one is the target class of its type argument
    assert LibTiffInfoTest.target_cls is SingleTarget
    assert PairedFastqParityTest.target_cls is PairedTarget
    assert FileExtensionTest.target_cls is BaseTarget


def test_that_a_test_subclass_inherits_the_target_class_of_its_parent() -> None:
    # GIVEN a subclass of a PairedTarget test with no type argument
    class ChildTest(PairedFastqParityTest):
        pass

    # WHEN I get its target class
    # THEN it is the PairedTarget class of its parent
    assert ChildTest.target_cls is PairedTarget


def test_for_an_error_when_the_test_type_argument_is_not_a_target_class() -> None:
    # GIVEN a test whose type argument is a union of two target classes
    # WHEN I define the test
    # THEN an error tells that it must give a BaseTarget subclass
    with pytest.raises(TypeError, match="must give a BaseTarget subclass"):

        class UnionTest(BaseTest[SingleTarget | PairedTarget]):  # type: ignore
            def compute_status(self) -> TestStatus:
                return TestStatus.NONE


def test_that_a_test_that_fails_its_check_is_not_registered() -> None:
    # GIVEN a test whose type argument is not a target class
    # WHEN I define the test
    with pytest.raises(TypeError, match="must give a BaseTarget subclass"):

        class UnregisteredTest(BaseTest[int]):  # type: ignore
            def compute_status(self) -> TestStatus:
                return TestStatus.NONE

    # THEN the test is not registered
    test_names = [test.__name__ for test in BaseTest.list_subclasses()]
    assert "UnregisteredTest" not in test_names


class GenericBox(Generic[BoxValue]):
    pass


def test_that_an_unrelated_generic_base_is_ignored() -> None:
    # GIVEN a test with a generic base that is not a test and a PairedTarget base
    class BoxedTest(GenericBox[int], InternalBaseTest[PairedTarget]):
        def compute_status(self) -> TestStatus:
            return TestStatus.NONE

    # WHEN I get its target class
    # THEN it is PairedTarget
    assert BoxedTest.target_cls is PairedTarget


def test_for_an_error_when_two_bases_give_a_target_class() -> None:
    # GIVEN a test with two bases that give different target classes
    # WHEN I define the test
    # THEN an error tells that it must give one target type
    with pytest.raises(TypeError, match="must give one target type"):

        class TwiceTest(  # type: ignore
            InternalBaseTest[SingleTarget], ExternalBaseTest[PairedTarget]
        ):
            def compute_status(self) -> TestStatus:
                return TestStatus.NONE


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
    suite = test_suites["good_jsonld"]
    assert all(test.tier.value <= 2 for test in suite.tests)


def test_that_skipped_tests_are_skipped_when_building_suite_from_tests(test_suites):
    suite = test_suites["good_tiff"]
    tests = suite.tests
    new_suite = SuiteABC.from_tests(tests, skipped_tests=["LibTiffInfoTest"])
    skipped_test_before = suite.tests_by_name["LibTiffInfoTest"]
    skipped_test_after = new_suite.tests_by_name["LibTiffInfoTest"]
    assert skipped_test_before.get_status(compute_ok=False) != TestStatus.SKIP
    assert skipped_test_after.get_status(compute_ok=False) == TestStatus.SKIP


def test_for_an_error_when_building_suite_from_tests_with_diff_targets(test_targets):
    target_1 = test_targets["good_txt"]
    target_2 = test_targets["wrong_file_type_and_md5_txt"]
    test_1 = FileExtensionTest(target_1)
    test_2 = FileExtensionTest(target_2)
    tests = [test_1, test_2]
    with pytest.raises(ValueError):
        SuiteABC.from_tests(tests)


def test_that_a_fastq_suite_is_built_from_a_paired_target(
    test_files: dict[str, File],
) -> None:
    # GIVEN a paired target of two FASTQ files
    files = [test_files["good_fastq"], test_files["good_compressed_fastq"]]
    # WHEN I build a suite from the target
    suite = SuiteABC.from_target(PairedTarget(files))
    # THEN the suite is a FASTQ suite with exactly the expected tests
    assert isinstance(suite, FastqSuite)
    assert {test.type for test in suite.tests} == {
        "FileExtensionTest",
        "Md5ChecksumTest",
        "PairedFastqParityTest",
    }


def test_that_a_fastq_suite_is_built_from_tests_with_a_paired_target(
    test_files: dict[str, File],
) -> None:
    # GIVEN the tests of a FASTQ suite with a paired target
    files = [test_files["good_fastq"], test_files["good_compressed_fastq"]]
    suite = SuiteABC.from_target(PairedTarget(files))
    # WHEN I build a suite from the tests
    new_suite = SuiteABC.from_tests(suite.tests)
    # THEN the new suite is a FASTQ suite with the same target
    assert isinstance(new_suite, FastqSuite)
    assert new_suite.target == suite.target


def test_that_the_tests_for_a_single_fastq_target_leave_out_the_paired_test(
    test_targets: dict[str, SingleTarget],
) -> None:
    # GIVEN a single target of a FASTQ file
    target = test_targets["good_fastq"]
    # WHEN I list the test classes of the FASTQ suite for the target
    test_classes = FastqSuite.list_test_classes_for_target(target)
    # THEN only the tests that accept any target are listed
    assert test_classes == (FileExtensionTest, Md5ChecksumTest)


def test_that_the_tests_for_a_paired_fastq_target_include_the_paired_test(
    test_files: dict[str, File],
) -> None:
    # GIVEN a paired target of two FASTQ files
    files = [test_files["good_fastq"], test_files["good_compressed_fastq"]]
    target = PairedTarget(files)
    # WHEN I list the test classes of the FASTQ suite for the target
    test_classes = FastqSuite.list_test_classes_for_target(target)
    # THEN all the tests of the suite are listed
    assert test_classes == FastqSuite.list_test_classes()
    assert PairedFastqParityTest in test_classes


def test_that_a_fastq_suite_from_a_single_target_has_no_paired_test(
    test_targets: dict[str, SingleTarget],
) -> None:
    # GIVEN a single target of a FASTQ file
    target = test_targets["good_fastq"]
    # WHEN I build a suite from the target
    suite = SuiteABC.from_target(target)
    # THEN the suite is a FASTQ suite with only the tests for any target
    assert isinstance(suite, FastqSuite)
    test_names = {test.type for test in suite.tests}
    assert test_names == {"FileExtensionTest", "Md5ChecksumTest"}
    # AND the paired test is not required
    assert "PairedFastqParityTest" not in suite.required_tests


def test_that_a_required_test_that_does_not_accept_the_target_is_ignored(
    test_targets: dict[str, SingleTarget],
) -> None:
    # GIVEN a single target of a FASTQ file
    target = test_targets["good_fastq"]
    # WHEN I build a suite that requires and skips the paired test
    required_tests = ["PairedFastqParityTest", "Md5ChecksumTest"]
    skipped_tests = ["PairedFastqParityTest"]
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)
    # THEN the suite does not keep the paired test in either list
    assert suite.required_tests == {"Md5ChecksumTest"}
    assert suite.skipped_tests == set()


def test_that_a_tiff_suite_from_a_paired_target_has_only_the_tests_for_any_target(
    test_files: dict[str, File],
) -> None:
    # GIVEN a paired target of two TIFF files
    files = [test_files["good_tiff"], test_files["date_in_tag_tiff"]]
    target = PairedTarget(files)
    # WHEN I build a suite from the target
    suite = SuiteABC.from_target(target)
    # THEN the suite is a TIFF suite without the SingleTarget tests
    assert isinstance(suite, TiffSuite)
    test_names = {test.type for test in suite.tests}
    assert test_names == {"FileExtensionTest", "Md5ChecksumTest"}


def test_that_a_fastq_suite_from_a_single_target_survives_serialization(
    test_targets: dict[str, SingleTarget],
) -> None:
    # GIVEN a FASTQ suite with a single target. The FASTQ test file has no
    # md5_checksum, so Md5ChecksumTest is skipped.
    target = test_targets["good_fastq"]
    suite = SuiteABC.from_target(target, skipped_tests=["Md5ChecksumTest"])
    # WHEN I serialize and deserialize the suite
    suite_from_dict = SuiteABC.from_dict(suite.to_dict())
    # THEN it has the same tests and required tests
    assert isinstance(suite_from_dict, FastqSuite)
    assert {test.type for test in suite_from_dict.tests} == {
        test.type for test in suite.tests
    }
    assert suite_from_dict.required_tests == suite.required_tests
    assert suite_from_dict.skipped_tests == {"Md5ChecksumTest"}


def test_that_a_suite_will_consider_non_required_failed_tests(test_targets):
    target = test_targets["wrong_file_type_and_md5_txt"]
    required_tests = []
    skipped_tests = ["LibTiffInfoTest", "TiffDateTimeTest", "TiffTag306DateTimeTest"]
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)
    suite_status = suite.compute_status()
    assert suite_status == SuiteStatus.AMBER


def test_that_a_suite_will_consider_required_tests_when_failing(test_targets):
    target = test_targets["wrong_file_type_and_md5_txt"]
    required_tests = ["FileExtensionTest"]
    skipped_tests = ["LibTiffInfoTest", "TiffDateTimeTest", "TiffTag306DateTimeTest"]
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)
    suite_status = suite.compute_status()
    assert suite_status == SuiteStatus.RED


def test_that_a_suite_will_consider_required_tests_when_passing(test_targets):
    target = test_targets["good_txt"]
    required_tests = ["Md5ChecksumTest"]
    suite = SuiteABC.from_target(target, required_tests)
    suite_status = suite.compute_status()
    assert suite_status == SuiteStatus.GREEN


def test_that_status_is_computed_if_not_already_assigned(test_targets):
    with patch.object(
        SuiteABC, "compute_status", return_value=SuiteStatus.GREEN
    ) as patch_compute_status:
        target = test_targets["good_txt"]
        required_tests = ["Md5ChecksumTest"]
        suite = SuiteABC.from_target(target, required_tests)
        suite._status = SuiteStatus.NONE
        suite_status = suite.get_status()
        assert suite_status == SuiteStatus.GREEN
        patch_compute_status.assert_called_once()


def test_that_test_metrics_survive_suite_serialization(test_targets):
    target = test_targets["good_txt"]
    suite = SuiteABC.from_target(target)
    # Test order is not deterministic, so look up the test by type
    test = next(test for test in suite.tests if test.type == "Md5ChecksumTest")
    test.metrics = {"metric1": 1, "metric2": "A"}
    suite_dict = suite.to_dict()
    test_dicts = {test_dict["type"]: test_dict for test_dict in suite_dict["tests"]}
    assert test_dicts["Md5ChecksumTest"]["metrics"] == {"metric1": 1, "metric2": "A"}
    suite_from_dict = SuiteABC.from_dict(suite_dict)
    tests = {test.type: test for test in suite_from_dict.tests}
    assert tests["Md5ChecksumTest"].metrics == {"metric1": 1, "metric2": "A"}
