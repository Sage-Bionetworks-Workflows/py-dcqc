import os
from tempfile import NamedTemporaryFile

import pytest

from dcqc.file import File, FileType


def test_for_an_error_if_registering_a_duplicate_file_type():
    with pytest.raises(ValueError):
        FileType("txt", (".foo",))


def test_for_an_error_when_requesting_for_an_unregistered_file_type():
    with pytest.raises(ValueError):
        FileType.get_file_type("foo")


def test_for_an_error_when_retrieving_missing_metadata_on_a_file(test_files):
    test_file, _ = test_files
    with pytest.raises(ValueError):
        test_file.get_metadata("foo")


@pytest.mark.integration
def test_that_a_remote_file_is_staged_when_requesting_a_local_path():
    url = "syn://syn50555279"
    metadata = {"file_type": "txt"}
    file = File(url, metadata)
    assert not file.is_local()
    file.get_local_path()
    assert file.is_local()


def test_that_a_local_file_is_not_moved_when_requesting_a_local_path(test_files):
    test_file, _ = test_files
    url_before = test_file.url
    local_path = test_file.get_local_path()
    url_after = test_file.url
    assert url_before == url_after
    assert os.path.exists(local_path)


@pytest.mark.integration
def test_that_a_local_file_is_moved_to_the_cwd_when_staged(test_files):
    test_file, _ = test_files
    with NamedTemporaryFile() as tmp_file:
        url_before = test_file.url
        destination = tmp_file.name
        url_after = test_file.stage(destination)
        assert url_before != url_after
        assert os.path.exists(destination)


def test_that_a_file_can_be_saved_and_restored_without_changing(test_files):
    file_1, _ = test_files
    file_1_dict = file_1.to_dict()
    file_2 = File.from_dict(file_1_dict)
    file_2_dict = file_2.to_dict()
    assert file_1 == file_2
    assert file_1_dict == file_2_dict
