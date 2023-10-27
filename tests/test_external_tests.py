from pathlib import Path
from tempfile import TemporaryDirectory

import docker
import pytest

from dcqc import tests
from dcqc.target import PairedTarget, SingleTarget
from dcqc.tests import BaseTest, ExternalTestMixin, Process, TestStatus


class DockerExecutor:
    def __init__(self, image, command, file_path):
        self.image = image
        self.command = command
        self.file_path = file_path

    def execute(self):
        client = docker.from_env()
        container = client.containers.run(
            image=self.image,
            command=self.command,
            detach=True,
            stdout=True,
            stderr=True,
            volumes={self.file_path: {"bind": self.file_path, "mode": "ro"}},
        )
        self.exit_code = str(container.wait()["StatusCode"])
        self.std_out = container.logs(stdout=True, stderr=False).decode("utf-8")
        self.std_err = container.logs(stdout=False, stderr=True).decode("utf-8")


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
    assert "jq" in process.command


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


def test_that_the_tiffdatetimetest_command_is_produced(test_targets):
    target = test_targets["tiff"]
    test = tests.TiffDateTimeTest(target)
    process = test.generate_process()
    assert "grep" in process.command


def test_that_the_tiffdatetimetest_correctly_interprets_exit_code_0_and_1(
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

        test = tests.TiffDateTimeTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=pass_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.PASS

        test = tests.TiffDateTimeTest(target)
        mocker.patch.object(test, "_find_process_outputs", return_value=fail_outputs)
        test_status = test.get_status()
        assert test_status == TestStatus.FAIL
