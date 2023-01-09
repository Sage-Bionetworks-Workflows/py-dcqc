import pytest

from dcqc.reports import JsonReport


def test_for_error_when_creating_report_if_file_already_exists(get_data):
    existing_path = get_data("test.txt").as_posix()
    with pytest.raises(FileExistsError):
        JsonReport(existing_path)
