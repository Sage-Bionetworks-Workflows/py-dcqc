from typing import Generic, TypeVar
from unittest.mock import patch

import pytest

from dcqc.file import FileType
from dcqc.suites.suite_abc import SuiteABC, SuiteStatus
from dcqc.suites.suites import FastqSuite, FileSuite, OmeTiffSuite, TiffSuite
from dcqc.target import BaseTarget, PairedTarget, SingleTarget
from dcqc.tests import (
    BaseTest,
    FileExtensionTest,
    LibTiffInfoTest,
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


def test_that_every_suite_test_accepts_the_suite_target_class():
    # GIVEN every registered suite
    # WHEN I check its tests against its target class
    # THEN no error is raised
    for suite_cls in SuiteABC.list_subclasses():
        suite_cls.ensure_tests_match_target_cls()


def test_that_the_default_suite_target_class_is_single_target():
    # GIVEN the base suite class
    # WHEN I get its target class
    # THEN it is SingleTarget
    assert SuiteABC.target_cls is SingleTarget


def test_for_an_error_when_a_suite_test_does_not_accept_the_target_class():
    # GIVEN a SingleTarget suite that adds a PairedTarget test
    # WHEN I define the suite
    # THEN an error tells that the test requires PairedTarget
    with pytest.raises(TypeError, match="requires PairedTarget"):

        class MismatchedSuite(FileSuite):
            file_type = FileType.get_file_type("None")
            add_tests = (PairedFastqParityTest,)


def test_for_an_error_when_a_suite_target_class_does_not_suit_its_tests():
    # GIVEN a PairedTarget suite that adds a SingleTarget test
    # WHEN I define the suite
    # THEN an error tells that the test requires SingleTarget
    with pytest.raises(TypeError, match="requires SingleTarget"):

        class MismatchedSuite(FileSuite):
            target_cls = PairedTarget
            file_type = FileType.get_file_type("None")
            add_tests = (LibTiffInfoTest,)


def test_that_the_fastq_suite_target_class_is_paired_target():
    # GIVEN the FASTQ suite
    # WHEN I get its target class
    # THEN it is PairedTarget
    assert FastqSuite.target_cls is PairedTarget


def test_that_a_suite_without_a_target_class_inherits_the_target_class():
    # GIVEN suites that do not set a target class
    # WHEN I get their target classes
    # THEN each one has the SingleTarget class of its parent
    assert FileSuite.target_cls is SingleTarget
    assert TiffSuite.target_cls is SingleTarget
    assert OmeTiffSuite.target_cls is SingleTarget


def test_for_an_error_when_the_suite_target_class_is_not_a_target_class():
    # GIVEN a suite whose target class is a union of two target classes
    # WHEN I define the suite
    # THEN an error tells that target_cls must be a BaseTarget subclass
    with pytest.raises(TypeError, match="must set target_cls to a BaseTarget"):

        class UnionSuite(FileSuite):
            target_cls = SingleTarget | PairedTarget  # type: ignore
            file_type = FileType.get_file_type("None")


def test_for_an_error_when_a_suite_is_given_a_type_argument():
    # GIVEN a suite class that is not generic
    # WHEN I define a suite with a type argument
    # THEN a TypeError is raised
    with pytest.raises(TypeError):

        class SubscriptedSuite(FileSuite[PairedTarget]):  # type: ignore
            file_type = FileType.get_file_type("None")


def test_that_the_default_test_target_class_is_base_target():
    # GIVEN the base test class and a test without a type argument
    # WHEN I get their target classes
    # THEN both are BaseTarget
    assert BaseTest.target_cls is BaseTarget
    assert DummyTest.target_cls is BaseTarget


def test_that_the_test_target_class_is_set_from_the_type_argument():
    # GIVEN tests with different type arguments
    # WHEN I get their target classes
    # THEN each one is the target class of its type argument
    assert LibTiffInfoTest.target_cls is SingleTarget
    assert PairedFastqParityTest.target_cls is PairedTarget
    assert FileExtensionTest.target_cls is BaseTarget


def test_that_a_test_subclass_inherits_the_target_class_of_its_parent():
    # GIVEN a subclass of a PairedTarget test with no type argument
    class ChildTest(PairedFastqParityTest):
        pass

    # WHEN I get its target class
    # THEN it is the PairedTarget class of its parent
    assert ChildTest.target_cls is PairedTarget


def test_for_an_error_when_the_test_type_argument_is_not_a_target_class():
    # GIVEN a test whose type argument is a union of two target classes
    # WHEN I define the test
    # THEN an error tells that it must give a BaseTarget subclass
    with pytest.raises(TypeError, match="must give a BaseTarget subclass"):

        class UnionTest(BaseTest[SingleTarget | PairedTarget]):  # type: ignore
            def compute_status(self) -> TestStatus:
                return TestStatus.NONE


def test_that_a_suite_that_fails_its_check_is_not_registered():
    # GIVEN a suite that adds a test that does not accept its target class
    # WHEN I define the suite
    with pytest.raises(TypeError, match="requires PairedTarget"):

        class UnregisteredSuite(FileSuite):
            file_type = FileType.get_file_type("Unpaired")
            add_tests = (PairedFastqParityTest,)

    # THEN the suite is not registered and its file type gets the generic suite
    suite_names = [suite.__name__ for suite in SuiteABC.list_subclasses()]
    assert "UnregisteredSuite" not in suite_names
    assert SuiteABC.get_subclass_by_file_type("Unpaired") is FileSuite


def test_that_a_test_that_fails_its_check_is_not_registered():
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


def test_that_an_unrelated_generic_base_is_ignored():
    # GIVEN a test with a generic base that is not a test and a PairedTarget base
    class BoxedTest(GenericBox[int], InternalBaseTest[PairedTarget]):
        def compute_status(self) -> TestStatus:
            return TestStatus.NONE

    # WHEN I get its target class
    # THEN it is PairedTarget
    assert BoxedTest.target_cls is PairedTarget


def test_for_an_error_when_two_bases_give_a_target_class():
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


def test_that_a_fastq_suite_is_built_from_a_paired_target(test_files):
    # GIVEN a paired target of two FASTQ files
    files = [test_files["good_fastq"], test_files["good_compressed_fastq"]]
    # WHEN I build a suite from the target
    suite = SuiteABC.from_target(PairedTarget(files))
    # THEN the suite is a FASTQ suite
    assert isinstance(suite, FastqSuite)


def test_that_a_fastq_suite_is_built_from_tests_with_a_paired_target(test_files):
    # GIVEN the tests of a FASTQ suite with a paired target
    files = [test_files["good_fastq"], test_files["good_compressed_fastq"]]
    suite = SuiteABC.from_target(PairedTarget(files))
    # WHEN I build a suite from the tests
    new_suite = SuiteABC.from_tests(suite.tests)
    # THEN the new suite is a FASTQ suite with the same target
    assert isinstance(new_suite, FastqSuite)
    assert new_suite.target == suite.target


def test_for_an_error_when_building_a_fastq_suite_from_a_single_target(test_targets):
    # GIVEN a single target of a FASTQ file
    target = test_targets["good_fastq"]
    url = target.files[0].url
    # WHEN I build a suite from the target
    # THEN an error tells the URL and that the suite requires a PairedTarget
    with pytest.raises(ValueError, match="requires a PairedTarget") as error:
        SuiteABC.from_target(target)
    assert url in str(error.value)
    # from_target also runs for qc-file, which has no CSV manifest
    assert "dcqc_grouping" not in str(error.value)


def test_for_an_error_when_building_a_tiff_suite_from_a_paired_target(test_files):
    # GIVEN a paired target of two TIFF files
    files = [test_files["good_tiff"], test_files["date_in_tag_tiff"]]
    target = PairedTarget(files)
    # WHEN I build a suite from the target
    # THEN an error tells that the suite requires a SingleTarget
    with pytest.raises(ValueError, match="requires a SingleTarget"):
        SuiteABC.from_target(target)


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


class ChildSingleTarget(SingleTarget):
    pass


class TestEnsureAcceptsTargetCls:
    """Tests for SuiteABC.ensure_accepts_target_cls.

    The method takes classes and URLs, not a target instance. Thus these
    tests make no File objects, and the URLs are only strings for the error
    message. No file is staged.
    """

    def test_that_a_single_target_is_accepted_for_a_tiff(self) -> None:
        """Make sure that TiffSuite accepts a SingleTarget."""
        # GIVEN TiffSuite and the TIFF file type
        file_type = FileType.get_file_type("TIFF")

        # WHEN a SingleTarget is checked
        # THEN no error is raised
        TiffSuite.ensure_accepts_target_cls(SingleTarget, file_type, ["a.tif"])

    def test_that_a_paired_target_is_accepted_for_a_fastq(self) -> None:
        """Make sure that FastqSuite accepts a PairedTarget."""
        # GIVEN FastqSuite and the FASTQ file type
        file_type = FileType.get_file_type("FASTQ")

        # WHEN a PairedTarget is checked
        # THEN no error is raised
        urls = ["a.fastq", "b.fastq"]
        FastqSuite.ensure_accepts_target_cls(PairedTarget, file_type, urls)

    def test_for_an_error_when_the_target_cls_is_a_parent_of_the_accepted_cls(
        self,
    ) -> None:
        """Make sure that a parent of the accepted target class is not accepted."""
        # GIVEN TiffSuite and the TIFF file type
        file_type = FileType.get_file_type("TIFF")

        # WHEN BaseTarget, the parent of SingleTarget, is checked
        # THEN an error is raised
        with pytest.raises(ValueError, match="requires a SingleTarget"):
            TiffSuite.ensure_accepts_target_cls(BaseTarget, file_type, ["a.tif"])

    def test_for_an_error_when_a_tiff_is_a_paired_target(self) -> None:
        """Make sure that the error for a grouped TIFF gives all the facts.

        The message must give the URLs, the two target classes, the suite
        class and the file type. It must not tell about the dcqc_grouping
        column, because some callers have no CSV manifest.
        """
        # GIVEN TiffSuite and the TIFF file type
        file_type = FileType.get_file_type("TIFF")

        # WHEN a PairedTarget is checked
        with pytest.raises(ValueError) as error:
            urls = ["a.tif", "b.tif"]
            TiffSuite.ensure_accepts_target_cls(PairedTarget, file_type, urls)

        # THEN the message is complete
        assert str(error.value) == (
            "Target (a.tif, b.tif) is a PairedTarget, but TiffSuite for file "
            "type 'TIFF' requires a SingleTarget."
        )

    def test_for_an_error_when_a_fastq_is_a_single_target(self) -> None:
        """Make sure that the error for an ungrouped FASTQ gives all the facts.

        The message must give the URL, the two target classes, the suite
        class and the file type. It must not tell about the dcqc_grouping
        column, because some callers have no CSV manifest.
        """
        # GIVEN FastqSuite and the FASTQ file type
        file_type = FileType.get_file_type("FASTQ")

        # WHEN a SingleTarget is checked
        with pytest.raises(ValueError) as error:
            FastqSuite.ensure_accepts_target_cls(SingleTarget, file_type, ["a.fastq"])

        # THEN the message is complete
        assert str(error.value) == (
            "Target (a.fastq) is a SingleTarget, but FastqSuite for file "
            "type 'FASTQ' requires a PairedTarget."
        )

    def test_for_an_error_when_a_file_type_without_a_suite_is_a_paired_target(
        self,
    ) -> None:
        """Make sure that the error for a file type with no suite is correct.

        No suite claims the Unpaired file type, so FileSuite is selected.
        FileSuite accepts only a SingleTarget. The message must give the
        file type of the target, not the file type of FileSuite.
        """
        # GIVEN the Unpaired file type, which selects FileSuite
        file_type = FileType.get_file_type("Unpaired")
        suite_cls = SuiteABC.get_subclass_by_file_type(file_type)

        # WHEN a PairedTarget is checked
        # THEN the error names FileSuite and the Unpaired file type
        message = "but FileSuite for file type 'Unpaired'"
        with pytest.raises(ValueError, match=message):
            suite_cls.ensure_accepts_target_cls(PairedTarget, file_type, ["a", "b"])
