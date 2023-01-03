from dcqc.suites.file_suite import FileSuite
from dcqc.tests.test_abc import TestABC


def test_that_a_file_qc_suite_results_in_multiple_tests(get_data):
    path = get_data("test.txt")
    suite = FileSuite(path)
    tests = suite.list_tests()
    assert len(tests) > 0

    first_test = tests[0]
    assert isinstance(first_test, TestABC)
