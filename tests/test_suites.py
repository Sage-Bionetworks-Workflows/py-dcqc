from dcqc.suites.suites import FileSuite, OmeTiffSuite, RedundantFileSuite, TiffSuite
from dcqc.tests.test_abc import TestABC


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
