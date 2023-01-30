import pytest

from dcqc.reports import JsonReport


def test_for_error_when_creating_report_if_file_already_exists(get_data, test_files):
    existing_url = get_data("test.txt").as_posix()
    file = test_files["good"]
    report = JsonReport()
    with pytest.raises(FileExistsError):
        report.save(file, existing_url)


def test_that_a_single_object_can_be_reported_on(test_files):
    file = test_files["remote"]
    report_url = "mem://subdir/report.json"
    report = JsonReport()
    report.save(file, report_url, overwrite=True)


def test_for_an_error_when_saving_to_a_file_with_a_parent_being_a_file(test_files):
    file = test_files["good"]
    # Intentionally using the input file in the output path to trigger an error
    subdir_url = file.local_path.as_posix()
    report_url = f"{subdir_url}/report.json"

    report = JsonReport()
    with pytest.raises(NotADirectoryError):
        report.save(file, report_url)
