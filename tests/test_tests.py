from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dcqc.target import Target
from dcqc.tests import tests
from dcqc.tests.test_abc import ExternalTestMixin, TestABC, TestStatus


def test_that_the_file_extension_test_works_on_correct_files(test_files):
    good_file = test_files["good"]
    target = Target(good_file)
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


@pytest.mark.integration
def test_that_the_file_extension_test_works_on_correct_remote_file(test_files):
    good_file = test_files["synapse"]
    target = Target(good_file)
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


# @pytest.mark.integration
# def test_that_a_tiff_file_with_good_extensions_is_passed():
#     file = File("syn://syn50944306", {"file_type": "TIFF"})
#     target = Target(file)
#     test = tests.FileExtensionTest(target)
#     assert test.get_status() == TestStatus.PASS


def test_that_the_file_extension_test_works_on_incorrect_files(test_files):
    good_file = test_files["good"]
    bad_file = test_files["bad"]
    target = Target(good_file, bad_file)
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_md5_checksum_test_works_on_a_correct_file(test_files):
    good_file = test_files["good"]
    target = Target(good_file)
    test = tests.Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_md5_checksum_test_works_on_incorrect_files(test_files):
    good_file = test_files["good"]
    bad_file = test_files["bad"]
    target = Target(good_file, bad_file)
    test = tests.Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_all_external_tests_inherit_from_the_mixin_first():
    tests = TestABC.list_subclasses()
    for test in tests:
        if issubclass(test, ExternalTestMixin):
            mro = test.__mro__
            mixin_index = mro.index(ExternalTestMixin)
            abc_index = mro.index(TestABC)
            assert mixin_index < abc_index


def test_that_the_libtiff_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    tiff_file = test_files["tiff"]
    target = Target(tiff_file)
    with TemporaryDirectory() as tmp_dir:
        path_0 = Path(tmp_dir, "code_0.txt")
        path_1 = Path(tmp_dir, "code_1.txt")
        path_0.write_text("0")
        path_1.write_text("1")
        good_outputs = {"std_out": path_1, "std_err": path_1, "exit_code": path_0}
        bad_outputs = {"std_out": path_0, "std_err": path_0, "exit_code": path_1}

        test = tests.LibTiffInfoTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=good_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.LibTiffInfoTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=bad_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL


def test_that_the_libtiff_info_test_command_is_produced(test_files):
    tiff_file = test_files["tiff"]
    target = Target(tiff_file)
    test = tests.LibTiffInfoTest(target)
    process = test.generate_process()
    assert "tiffinfo" in process.get_command()


def test_that_the_bioformats_info_test_command_is_produced(test_files):
    tiff_file = test_files["tiff"]
    target = Target(tiff_file)
    test = tests.BioFormatsInfoTest(target)
    process = test.generate_process()
    assert "showinf" in process.get_command()


def test_that_the_ome_xml_schema_test_command_is_produced(test_files):
    tiff_file = test_files["tiff"]
    target = Target(tiff_file)
    test = tests.OmeXmlSchemaTest(target)
    process = test.generate_process()
    assert "xmlvalid" in process.get_command()


def test_that_the_md5_checksum_test_can_be_retrieved_by_name():
    test = TestABC.get_subclass_by_name("Md5ChecksumTest")
    assert test is tests.Md5ChecksumTest


def test_for_an_error_when_retrieving_a_random_test_by_name():
    with pytest.raises(ValueError):
        TestABC.get_subclass_by_name("FooBar")


def test_for_an_error_when_a_libtiff_info_test_is_given_multiple_files(test_files):
    tiff_file = test_files["tiff"]
    target = Target(tiff_file, tiff_file)

    assert not tests.Md5ChecksumTest.only_one_file_targets
    tests.Md5ChecksumTest(target)

    assert tests.LibTiffInfoTest.only_one_file_targets
    with pytest.raises(ValueError):
        tests.LibTiffInfoTest(target)


def test_that_process_output_files_can_be_found(get_data):
    std_out = get_data("tiffinfo/std_out.txt")
    std_err = get_data("tiffinfo/std_err.txt")
    exit_code = get_data("tiffinfo/exit_code.txt")
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        (tmp_path / std_out.name).symlink_to(std_out)
        (tmp_path / std_err.name).symlink_to(std_err)

        with pytest.raises(FileNotFoundError):
            ExternalTestMixin._find_process_outputs(tmp_path)

        (tmp_path / exit_code.name).symlink_to(exit_code)
        ExternalTestMixin._find_process_outputs(tmp_path)
