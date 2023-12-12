import glob
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory, gettempdir
from typing import List

import pytest

from dcqc.file import File, FileType


def create_duplicate_files(file_num) -> List[str]:
    """Create duplicate files (empty txt) for testing.

    Args:
        file_num (int): number of files to create

    Returns:
       file_path_list (List[str]): list of file paths
    """
    file_path_list = [
        os.path.join(gettempdir(), f"dcqc-staged-test{i}/test.txt")
        for i in range(file_num)
    ]

    for file_path in file_path_list:
        parent_dir = os.path.dirname(file_path)
        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
        if not os.path.exists(file_path):
            with open(file_path, "w"):
                pass

    return file_path_list


def remove_staged_files():
    """Removes all staged files and their parent directories
    which follow the 'dcqc-staged-*' pattern.

    To be used at the end of all tests which result in such
    files being created.
    """
    path_str = os.path.join(gettempdir(), "dcqc-staged-" + "*", "test.txt")
    staged_file_strs = glob.glob(path_str)
    for staged_file_str in staged_file_strs:
        directory_path = os.path.dirname(staged_file_str)
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)


def test_for_an_error_if_registering_a_duplicate_file_type():
    with pytest.raises(ValueError):
        FileType("txt", (".foo",))


def test_for_an_error_when_requesting_for_an_unregistered_file_type():
    with pytest.raises(ValueError):
        FileType.get_file_type("foo")


def test_for_an_error_when_retrieving_missing_metadata_on_a_file(test_files):
    test_file = test_files["good_txt"]
    with pytest.raises(KeyError):
        test_file.get_metadata("foo")


def test_that_a_local_file_is_not_moved_when_requesting_a_local_path(test_files):
    test_file = test_files["good_txt"]
    url_before = test_file.url
    local_path = test_file.local_path
    url_after = test_file.url
    assert url_before == url_after
    assert local_path.exists()


def test_for_an_error_when_accessing_local_path_of_an_unstaged_remote_file(test_files):
    remote_file = test_files["remote"]
    with pytest.raises(FileNotFoundError):
        remote_file.local_path


def test_that_a_local_file_is_not_moved_when_staged_without_a_destination(test_files):
    test_file = test_files["good_txt"]
    path_before = test_file.local_path
    path_after = test_file.stage()
    assert path_before == path_after


def test_that_a_local_file_is_symlinked_when_staged_with_a_destination(test_files):
    test_file = test_files["good_txt"]
    with TemporaryDirectory() as tmp_dir:
        original_path = Path(test_file.local_path)
        tmp_dir_path = Path(tmp_dir)
        test_file.stage(tmp_dir_path)
        staged_path = Path(test_file.local_path)
        assert staged_path.is_symlink()
        assert staged_path.resolve() == original_path.resolve()


def test_that_a_local_temporary_path_is_created_when_staging_a_remote_file(test_files):
    remote_file = test_files["remote"]
    staged_path = remote_file.stage()
    assert staged_path.exists()
    assert remote_file.local_path == staged_path
    remove_staged_files()


def test_that_error_is_raised_when_a_file_has_been_staged_multiple_times(test_files):
    create_duplicate_files(2)
    remote_file = test_files["remote"]
    with pytest.raises(FileExistsError):
        remote_file.stage()
    remove_staged_files()


def test_that_file_is_not_staged_when_it_already_has_been_staged(test_files):
    duplicate_file = create_duplicate_files(1)[0]
    remote_file = test_files["remote"]
    destination = remote_file.stage()
    assert destination == Path(duplicate_file)
    remove_staged_files()


def test_that_a_remote_file_is_created_when_staged_with_a_destination(test_files):
    remote_file = test_files["remote"]
    with TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / "test.txt"
        staged_path = remote_file.stage(tmp_path)
        assert staged_path.exists()
        assert staged_path == tmp_path
        assert remote_file.local_path == staged_path


def test_that_a_file_can_be_saved_and_restored_without_changing(test_files):
    file_1 = test_files["good_txt"]
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


def test_that_an_fs_is_created_when_an_fs_path_is_requested(test_files):
    file = test_files["good_txt"]
    assert file._fs_path is None
    file.fs_path
    assert file._fs_path is not None
    assert file._fs is not None


def test_that_file_name_is_cached(test_files):
    file = test_files["remote"]
    assert file._name is None
    attempt_1 = file.name
    assert file._name is not None
    attempt_2 = file.name
    assert attempt_1 is attempt_2


def test_for_an_error_when_staging_a_file_where_one_already_exists(test_files):
    remote_file = test_files["remote"]
    existing_file = test_files["good_txt"]
    with pytest.raises(FileExistsError):
        remote_file.stage(existing_file.local_path)


def test_for_an_error_when_staging_a_file_under_a_nonexistent_directory(test_files):
    remote_file = test_files["remote"]
    invalid_destination = Path("./nonexistent_dir/test.txt")
    with pytest.raises(ValueError):
        remote_file.stage(invalid_destination)


def test_that_an_unset_local_path_is_ignored_during_deserialization(test_files):
    file = test_files["remote"]
    dictionary = file.to_dict()
    file_from_dict = File.from_dict(dictionary)
    with pytest.raises(FileNotFoundError):
        file_from_dict.local_path


def test_that_a_file_cannot_be_made_relative_to_a_nonexistent_directory(test_files):
    file = test_files["good_txt"]
    nonexistent_dir = Path("foobar")
    with pytest.raises(ValueError):
        file.serialize_paths_relative_to(nonexistent_dir)


def test_that_a_file_cannot_be_made_relative_to_a_another_file(test_files):
    file = test_files["good_txt"]
    another_file = test_files["bad_txt"]
    another_file_path = another_file.local_path
    with pytest.raises(ValueError):
        file.serialize_paths_relative_to(another_file_path)


def test_that_paths_are_unchanged_when_not_using_serialize_paths_relative_to():
    path = Path("foobar")
    file = File("test.txt", local_path=path)
    file_dict = file.to_dict()
    assert file_dict["local_path"] == str(path)


def test_that_paths_change_when_using_serialize_paths_relative_to(get_output):
    path = Path("foo")
    relative_to = get_output("relative-to")
    relative_to.mkdir(parents=True, exist_ok=True)
    file = File("test.txt", local_path=path)
    file.serialize_paths_relative_to(relative_to)
    file_dict = file.to_dict()
    assert file_dict["local_path"] != str(path)
