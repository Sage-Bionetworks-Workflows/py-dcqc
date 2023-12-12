import os
import shlex
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import docker
from dcqc import tests
from dcqc.target import SingleTarget
from dcqc.tests import BaseTest, ExternalTestMixin, Process, TestStatus


def test_that_all_external_tests_inherit_from_the_mixin_first():
    tests_list = BaseTest.list_subclasses()
    for test in tests_list:
        if issubclass(test, ExternalTestMixin):
            mro = test.__mro__
            mixin_index = mro.index(ExternalTestMixin)
            abc_index = mro.index(BaseTest)
            assert mixin_index < abc_index


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


# TODO Make changes to fully support Docker-enabled tests in macOS once it is possile
def docker_enabled_test(func):
    """Marks Docker-enabled tests to only run in Linux environments."""
    return pytest.mark.skipif(
        "linux" not in sys.platform.lower(),
        reason="Docker-enabled tests only run in Linux",
    )(func)


class DockerExecutor:
    """Class for executing a command in a docker container."""

    def __init__(self, image: str, command: str, file_path: str):
        """Initialize the class."""
        self.image = image
        self.command = self.format_command_for_sh(command)
        self.local_path = file_path
        self.container_path = os.path.join("/", file_path.split("/")[-1])

    def format_command_for_sh(self, command):
        """Format the command for sh -c.
        Standardizes command execution across containers."""
        escaped_command = shlex.quote(command)
        formatted_command = f"sh -c {escaped_command}"
        return formatted_command

    def execute(self):
        """Execute the command in a docker container."""
        client = docker.from_env()
        container = client.containers.run(
            image=self.image,
            command=self.command,
            detach=True,
            stdout=True,
            stderr=True,
            volumes={self.local_path: {"bind": self.container_path, "mode": "ro"}},
            working_dir="/",
        )
        self.exit_code = str(container.wait()["StatusCode"])
        self.std_out = container.logs(stdout=True, stderr=False).decode("utf-8")
        self.std_err = container.logs(stdout=False, stderr=True).decode("utf-8")


def test_that_the_libtiff_info_test_command_is_produced(test_targets):
    target = test_targets["good_tiff"]
    test = tests.LibTiffInfoTest(target)
    process = test.generate_process()
    assert "tiffinfo" in process.command


@docker_enabled_test
def test_that_the_libtiff_info_test_exit_code_is_0_when_it_should_be(test_files):
    tiff_file = test_files["good_tiff"]
    target = SingleTarget(tiff_file)
    test = tests.LibTiffInfoTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "0"


@docker_enabled_test
def test_that_the_libtiff_info_test_exit_code_is_1_when_it_should_be(test_files):
    tiff_file = test_files["wrong_file_type_and_md5_txt"]
    target = SingleTarget(tiff_file)
    test = tests.LibTiffInfoTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "1"


def test_that_the_libtiff_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 0 is pass, 1 is fail
    tiff_file = test_files["good_tiff"]
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


def test_that_the_bioformats_info_test_command_is_produced(test_targets):
    target = test_targets["good_tiff"]
    test = tests.BioFormatsInfoTest(target)
    process = test.generate_process()
    assert "showinf" in process.command


@docker_enabled_test
def test_that_the_bioformats_info_test_exit_code_is_0_when_it_should_be(test_files):
    one_tiff_file = test_files["good_ome_tiff"]
    target = SingleTarget(one_tiff_file)
    test = tests.BioFormatsInfoTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "0"


@docker_enabled_test
def test_that_the_bioformats_info_test_exit_code_is_1_when_it_should_be(test_files):
    one_tiff_file = test_files["good_txt"]
    target = SingleTarget(one_tiff_file)
    test = tests.BioFormatsInfoTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "1"


def test_that_the_bioformats_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 0 is pass, 1 is fail
    tiff_file = test_files["good_tiff"]
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
    target = test_targets["good_tiff"]
    test = tests.OmeXmlSchemaTest(target)
    process = test.generate_process()
    assert "xmlvalid" in process.command


@docker_enabled_test
def test_that_the_ome_xml_schema_test_exit_code_is_0_when_it_should_be(test_files):
    tiff_file = test_files["good_ome_tiff"]
    target = SingleTarget(tiff_file)
    test = tests.OmeXmlSchemaTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "0"


@docker_enabled_test
def test_that_the_ome_xml_schema_test_exit_code_is_1_when_it_should_be(test_files):
    tiff_file = test_files["good_txt"]
    target = SingleTarget(tiff_file)
    test = tests.OmeXmlSchemaTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "1"


def test_that_the_ome_xml_info_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 0 is pass, 1 is fail
    tiff_file = test_files["good_tiff"]
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


def test_that_the_grep_date_test_command_is_produced(test_targets):
    target = test_targets["good_tiff"]
    test = tests.GrepDateTest(target)
    process = test.generate_process()
    assert "grep" in process.command


@docker_enabled_test
def test_that_the_grep_date_test_exit_code_is_0_when_it_should_be(test_files):
    date_file = test_files["date_string_txt"]
    target = SingleTarget(date_file)
    test = tests.GrepDateTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "0"


@docker_enabled_test
def test_that_the_grep_date_test_exit_code_is_1_when_it_should_be(test_files):
    tiff_file = test_files["good_txt"]
    target = SingleTarget(tiff_file)
    test = tests.GrepDateTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "1"


def test_that_the_grep_date_test_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 1 is pass, 0 is fail
    tiff_file = test_files["good_tiff"]
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


def test_that_the_tifftag306datetimetest_command_is_produced(test_targets):
    target = test_targets["good_tiff"]
    test = tests.TiffTag306DateTimeTest(target)
    process = test.generate_process()
    assert "jq" in process.command


@docker_enabled_test
def test_that_the_tifftag306datetimetest_exit_code_is_1_when_it_should_be(test_files):
    tiff_file = test_files["good_tiff"]
    target = SingleTarget(tiff_file)
    test = tests.TiffTag306DateTimeTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "1"


@docker_enabled_test
def test_that_the_tifftag306datetimetest_exit_code_is_0_when_it_should_be(test_files):
    tiff_file = test_files["dirty_datetime_tiff"]
    target = SingleTarget(tiff_file)
    test = tests.TiffTag306DateTimeTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "0"


def test_that_the_tifftag306datetimetest_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 1 is pass, 0 is fail
    tiff_file = test_files["good_tiff"]
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
    target = test_targets["good_tiff"]
    test = tests.TiffDateTimeTest(target)
    process = test.generate_process()
    assert "grep" in process.command


@docker_enabled_test
def test_that_the_tiffdatetimetest_exit_code_is_1_when_it_should_be(test_files):
    tiff_file = test_files["good_tiff"]
    target = SingleTarget(tiff_file)
    test = tests.TiffDateTimeTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "1"


@docker_enabled_test
def test_that_the_tiffdatetimetest_exit_code_is_0_when_it_should_be(test_files):
    tiff_file = test_files["date_in_tag_tiff"]
    target = SingleTarget(tiff_file)
    test = tests.TiffDateTimeTest(target)
    process = test.generate_process()
    executor = DockerExecutor(process.container, process.command, target.file.url)
    executor.execute()
    assert executor.exit_code == "0"


def test_that_the_tiffdatetimetest_correctly_interprets_exit_code_0_and_1(
    test_files, mocker
):
    # 1 is pass, 0 is fail
    tiff_file = test_files["good_tiff"]
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
