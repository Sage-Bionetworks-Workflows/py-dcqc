import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dcqc.file import File, FileType


def test_for_an_error_if_registering_a_duplicate_file_type():
    with pytest.raises(ValueError):
        FileType("txt", (".foo",))


def test_for_an_error_when_requesting_for_an_unregistered_file_type():
    with pytest.raises(ValueError):
        FileType.get_file_type("foo")


def test_for_an_error_when_retrieving_missing_metadata_on_a_file(test_files):
    test_file = test_files["good"]
    with pytest.raises(KeyError):
        test_file.get_metadata("foo")


def test_that_a_local_file_is_not_moved_when_requesting_a_local_path(test_files):
    test_file = test_files["good"]
    url_before = test_file.url
    local_path = test_file.get_local_path()
    url_after = test_file.url
    assert url_before == url_after
    assert os.path.exists(local_path)


@pytest.mark.integration
def test_for_an_error_when_getting_local_path_for_an_unstaged_remote_file(test_files):
    file = test_files["synapse"]
    with pytest.raises(FileNotFoundError):
        file.get_local_path()


@pytest.mark.integration
def test_that_a_local_file_is_not_moved_when_staged_without_a_destination(test_files):
    test_file = test_files["good"]
    path_before = test_file.get_local_path()
    path_after = test_file.stage()
    assert path_before == path_after


@pytest.mark.integration
def test_that_a_local_file_is_symlinked_when_staged_with_a_destination(test_files):
    test_file = test_files["good"]
    with TemporaryDirectory() as tmp_dir:
        original_path = Path(test_file.get_local_path())
        tmp_dir_path = Path(tmp_dir)
        test_file.stage(tmp_dir_path)
        staged_path = Path(test_file.get_local_path())
        assert staged_path.is_symlink()
        assert staged_path.resolve() == original_path.resolve()


@pytest.mark.integration
def test_that_a_local_temporary_path_is_created_when_staging_a_remote_file(test_files):
    file = test_files["synapse"]
    file.stage()
    assert file.get_local_path() is not None


@pytest.mark.integration
def test_that_a_remote_file_is_created_when_staged_with_a_destination(test_files):
    test_file = test_files["synapse"]
    with TemporaryDirectory() as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        test_file.stage(tmp_dir_path)
        local_path = test_file.get_local_path()
        assert local_path.exists()
        assert not local_path.is_symlink()


def test_that_a_file_can_be_saved_and_restored_without_changing(test_files):
    file_1 = test_files["good"]
    file_1_dict = file_1.to_dict()
    file_2 = File.from_dict(file_1_dict)
    file_2_dict = file_2.to_dict()
    assert file_1 == file_2
    assert file_1_dict == file_2_dict


def test_that_an_absolute_local_url_is_unchanged_when_using_relative_to(get_data):
    test_path = get_data("test.txt")
    test_url = test_path.resolve().as_posix()
    metadata = {"file_type": "TXT"}
    file = File(test_url, metadata, relative_to=Path.cwd())
    assert file.url == test_url
