from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dcqc import tests
from dcqc.target import PairedTarget, SingleTarget
from dcqc.tests import BaseTest, ExternalTestMixin, Process, TestStatus


def test_that_the_file_extension_test_works_on_correct_files(test_targets):
    target = test_targets["good"]
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
    target = test_targets["bad"]
    test = tests.FileExtensionTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_md5_checksum_test_works_on_a_correct_file(test_targets):
    target = test_targets["good"]
    test = tests.Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_md5_checksum_test_works_on_incorrect_files(test_targets):
    target = test_targets["bad"]
    test = tests.Md5ChecksumTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_json_load_test_works_on_a_correct_file(test_targets):
    target = test_targets["jsonld"]
    test = tests.JsonLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_json_load_test_works_on_incorrect_files(test_targets):
    target = test_targets["good"]
    test = tests.JsonLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_the_jsonld_load_test_works_on_a_correct_file(test_targets):
    target = test_targets["jsonld"]
    test = tests.JsonLdLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.PASS


def test_that_the_jsonld_load_test_works_on_incorrect_files(test_targets):
    target = test_targets["good"]
    test = tests.JsonLdLoadTest(target)
    test_status = test.get_status()
    assert test_status == TestStatus.FAIL


def test_that_all_external_tests_inherit_from_the_mixin_first():
    tests = BaseTest.list_subclasses()
    for test in tests:
        if issubclass(test, ExternalTestMixin):
            mro = test.__mro__
            mixin_index = mro.index(ExternalTestMixin)
            abc_index = mro.index(BaseTest)
            assert mixin_index < abc_index


def test_that_the_libtiff_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 0 is pass, 1 is fail
    tiff_file = test_files["tiff"]
    target = SingleTarget(tiff_file)
    with TemporaryDirectory() as tmp_dir:
        path_0 = Path(tmp_dir, "code_0.txt")
        path_1 = Path(tmp_dir, "code_1.txt")
        path_0.write_text("0")
        path_1.write_text("1")
        pass_outputs = {"std_out": path_1, "std_err": path_1, "exit_code": path_0}
        fail_outputs = {"std_out": path_0, "std_err": path_0, "exit_code": path_1}

        test = tests.LibTiffInfoTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=pass_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.LibTiffInfoTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=fail_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL


def test_that_the_libtiff_info_test_command_is_produced(test_targets):
    target = test_targets["tiff"]
    test = tests.LibTiffInfoTest(target)
    process = test.generate_process()
    assert "tiffinfo" in process.command


def test_that_the_bioformats_info_test_command_is_produced(test_targets):
    target = test_targets["tiff"]
    test = tests.BioFormatsInfoTest(target)
    process = test.generate_process()
    assert "showinf" in process.command


def test_that_the_bioformats_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 0 is pass, 1 is fail
    tiff_file = test_files["tiff"]
    target = SingleTarget(tiff_file)
    with TemporaryDirectory() as tmp_dir:
        path_0 = Path(tmp_dir, "code_0.txt")
        path_1 = Path(tmp_dir, "code_1.txt")
        path_0.write_text("0")
        path_1.write_text("1")
        pass_outputs = {"std_out": path_1, "std_err": path_1, "exit_code": path_0}
        fail_outputs = {"std_out": path_0, "std_err": path_0, "exit_code": path_1}

        test = tests.BioFormatsInfoTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=pass_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.BioFormatsInfoTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=fail_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL


def test_that_the_ome_xml_schema_test_command_is_produced(test_targets):
    target = test_targets["tiff"]
    test = tests.OmeXmlSchemaTest(target)
    process = test.generate_process()
    assert "xmlvalid" in process.command


def test_that_the_ome_xml_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 0 is pass, 1 is fail
    tiff_file = test_files["tiff"]
    target = SingleTarget(tiff_file)
    with TemporaryDirectory() as tmp_dir:
        path_0 = Path(tmp_dir, "code_0.txt")
        path_1 = Path(tmp_dir, "code_1.txt")
        path_0.write_text("0")
        path_1.write_text("1")
        pass_outputs = {"std_out": path_1, "std_err": path_1, "exit_code": path_0}
        fail_outputs = {"std_out": path_0, "std_err": path_0, "exit_code": path_1}

        test = tests.OmeXmlSchemaTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=pass_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.OmeXmlSchemaTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=fail_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL


def test_that_the_md5_checksum_test_can_be_retrieved_by_name():
    test = BaseTest.get_subclass_by_name("Md5ChecksumTest")
    assert test is tests.Md5ChecksumTest


def test_for_an_error_when_retrieving_a_random_test_by_name():
    with pytest.raises(ValueError):
        BaseTest.get_subclass_by_name("FooBar")


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


def test_for_error_when_importing_unavailable_module(test_targets):
    target = test_targets["good"]
    test = tests.FileExtensionTest(target)
    with pytest.raises(ModuleNotFoundError):
        test.import_module("foobar")


def test_that_an_existing_module_can_be_imported(test_targets):
    target = test_targets["good"]
    test = tests.FileExtensionTest(target)
    imported = test.import_module("pytest")
    assert imported is pytest


def test_that_a_process_can_be_serialized_and_deserialized():
    process = Process("foo:bar", ["python"])
    process_dict = process.to_dict()
    process_from_dict = Process.from_dict(process_dict)
    assert process_dict == process_from_dict.to_dict()


def test_that_the_grep_date_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 1 is pass, 0 is fail
    tiff_file = test_files["tiff"]
    target = SingleTarget(tiff_file)
    with TemporaryDirectory() as tmp_dir:
        path_0 = Path(tmp_dir, "code_0.txt")
        path_1 = Path(tmp_dir, "code_1.txt")
        path_0.write_text("0")
        path_1.write_text("1")
        fail_outputs = {"std_out": path_1, "std_err": path_1, "exit_code": path_0}
        pass_outputs = {"std_out": path_0, "std_err": path_0, "exit_code": path_1}

        test = tests.GrepDateTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=pass_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.GrepDateTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=fail_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL


def test_that_the_grep_date_test_command_is_produced(test_targets):
    target = test_targets["tiff"]
    test = tests.GrepDateTest(target)
    process = test.generate_process()
    assert "grep" in process.command


def test_that_the_tifftag306datetimetest_command_is_produced(test_targets):
    target = test_targets["tiff"]
    test = tests.TiffTag306DateTimeTest(target)
    process = test.generate_process()
    assert "grep" in process.command


def test_that_the_tifftag306datetimetest_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 1 is pass, 0 is fail
    tiff_file = test_files["tiff"]
    target = SingleTarget(tiff_file)
    with TemporaryDirectory() as tmp_dir:
        path_0 = Path(tmp_dir, "code_0.txt")
        path_1 = Path(tmp_dir, "code_1.txt")
        path_0.write_text("0")
        path_1.write_text("1")
        fail_outputs = {"std_out": path_1, "std_err": path_1, "exit_code": path_0}
        pass_outputs = {"std_out": path_0, "std_err": path_0, "exit_code": path_1}

        test = tests.TiffTag306DateTimeTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=pass_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.TiffTag306DateTimeTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=fail_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL


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


def test_that_short_string_path_correctly_shortens_file_paths():
    substring = "test-substring"
    long_path = f"path/needs/to/be/shortened/{substring}/file.txt"
    expected_short_path = f"'{substring}/file.txt'"
    short_path = ExternalTestMixin._short_string_path(Path(long_path), substring)
    assert short_path == expected_short_path


def test_that_short_string_path_raises_valueerror_if_substring_not_in_path():
    substring = "test-substring"
    long_path = "path/needs/to/be/shortened/fail/file.txt"
    with pytest.raises(ValueError):
        ExternalTestMixin._short_string_path(Path(long_path), substring)
