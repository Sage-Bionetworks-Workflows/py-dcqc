import os
from collections.abc import Generator
from pathlib import Path

import pytest

from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.parsers import CsvParser, JsonParser
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import SingleTarget
from dcqc.tests.base_test import BaseTest


def test_that_parsing_a_csv_file_yields_suites(get_data):
    csv_path = get_data("files.csv")
    csv_parser = CsvParser(csv_path)
    result = csv_parser.create_suites()
    assert isinstance(result, Generator)
    result = list(result)
    assert len(result) > 1
    assert all(isinstance(x, SuiteABC) for x in result)


def test_that_parsing_a_csv_file_stages_remote_files(get_data, test_files, mocker):
    csv_path = get_data("files.csv")
    csv_parser = CsvParser(csv_path, stage_files=True)
    mock = mocker.patch.object(csv_parser, "_row_to_file")
    mock.return_value = test_files["remote"]
    files = csv_parser.create_files()
    assert all(file.local_path is not None for _, file in files)


@pytest.fixture
def relative_manifest(tmp_path: Path) -> Path:
    """Write a manifest into a directory that is not the work directory.

    The manifest has three rows. The first row has a relative local URL, the
    second row has an absolute local URL, and the third row has a remote URL.
    The two local files exist.

    Args:
        tmp_path: A temporary directory that pytest gives to each test.

    Returns:
        The path of the manifest.
    """
    manifest_dir = tmp_path / "manifests"
    manifest_dir.mkdir()
    (manifest_dir / "test.txt").write_text("Hello world!\n")
    absolute_path = tmp_path / "absolute.txt"
    absolute_path.write_text("Hello world!\n")
    manifest = manifest_dir / "input.csv"
    manifest.write_text(
        "url,file_type\n"
        "test.txt,TXT\n"
        f"{absolute_path},TXT\n"
        "syn://syn50555279,TXT\n"
    )
    return manifest


def test_that_list_rows_yields_urls_as_written_in_the_manifest(
    relative_manifest: Path,
) -> None:
    """Test that list_rows does not change the URLs in the manifest."""
    # GIVEN a parser for a manifest that is not in the work directory
    csv_parser = CsvParser(relative_manifest)

    # WHEN I list the rows
    urls = [row["url"] for _, row in csv_parser.list_rows()]

    # THEN I expect the relative URL to be the value in the manifest
    assert urls[0] == "test.txt"


def test_that_list_rows_and_files_yields_unchanged_rows(
    relative_manifest: Path,
) -> None:
    """Test that list_rows_and_files gives each row with no changes.

    The row must keep its url column, because CsvUpdater writes the row to the
    output manifest.
    """
    # GIVEN a parser for a manifest that is not in the work directory
    csv_parser = CsvParser(relative_manifest)

    # AND the rows as they are written in the manifest
    raw_rows = [row for _, row in csv_parser.list_rows()]

    # WHEN I list the rows and files
    result = list(csv_parser.list_rows_and_files())

    # THEN I expect the row numbers to start at 1
    assert [index for index, _, _ in result] == [1, 2, 3]

    # AND I expect each row to be the same as the row in the manifest
    assert [row for _, row, _ in result] == raw_rows

    # AND I expect each row to keep its url column
    assert all("url" in row for _, row, _ in result)


@pytest.mark.parametrize(
    "index, expected",
    [
        pytest.param(0, "relative", id="relative-local-url-is-rebased"),
        pytest.param(1, "unchanged", id="absolute-local-url-is-unchanged"),
        pytest.param(2, "unchanged", id="remote-url-is-unchanged"),
    ],
)
def test_that_list_rows_and_files_gives_the_expected_url(
    relative_manifest: Path, index: int, expected: str
) -> None:
    """Test that list_rows_and_files changes only relative local URLs.

    A relative local URL must be relative to the manifest directory. An
    absolute local URL and a remote URL must not change.

    Args:
        relative_manifest: The path of the manifest.
        index: The position of the row in the manifest, which starts at 0.
        expected: Either relative, if the URL must be relative to the
            manifest directory, or unchanged, if the URL must not change.
    """
    # GIVEN a parser for a manifest that is not in the work directory
    csv_parser = CsvParser(relative_manifest)

    # WHEN I list the rows and files
    _, row, file = list(csv_parser.list_rows_and_files())[index]

    # THEN I expect the URL of the file to be the expected URL
    if expected == "relative":
        assert file.url == os.path.relpath(relative_manifest.parent / row["url"])
    else:
        assert file.url == row["url"]


def test_that_create_files_agrees_with_list_rows_and_files(
    relative_manifest: Path,
) -> None:
    """Test that create_files and list_rows_and_files give the same URLs.

    CsvUpdater matches each suite to a row by URL, so the two must agree.
    """
    # GIVEN a parser for a manifest that is not in the work directory
    csv_parser = CsvParser(relative_manifest)

    # WHEN I list the rows and files
    expected = [(i, f.url) for i, _, f in csv_parser.list_rows_and_files()]

    # AND I create the files
    actual = [(i, f.url) for i, f in csv_parser.create_files()]

    # THEN I expect both to give the same row numbers and URLs
    assert actual == expected


def test_that_parsing_a_json_file_must_match_listed_type(get_data):
    json_path = get_data("file.json")
    assert JsonParser.parse_object(json_path, File)
    with pytest.raises(ValueError):
        JsonParser.parse_object(json_path, SingleTarget)


def test_for_an_error_when_parsing_an_unrecognized_type():
    with pytest.raises(ValueError):
        JsonParser.get_class("foobar")


def test_for_an_error_when_parsing_a_dictionary_without_a_type():
    dictionary = {"foo": "bar"}
    with pytest.raises(ValueError):
        JsonParser.from_dict(dictionary)


def test_for_an_error_when_parsing_a_list_of_objects_with_parse_object(get_data):
    json_path = get_data("tests.json")
    with pytest.raises(ValueError):
        JsonParser.parse_object(json_path, SerializableMixin)


def test_for_an_error_when_parsing_a_single_object_with_parse_objects(get_data):
    json_path = get_data("target.json")
    with pytest.raises(ValueError):
        JsonParser.parse_objects(json_path, SerializableMixin)


def test_that_json_parser_can_parse_multiple_objects(get_data):
    json_path = get_data("tests.json")
    result = JsonParser.parse_objects(json_path, BaseTest)
    assert len(result) > 0
    assert isinstance(result[0], BaseTest)
