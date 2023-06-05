from collections.abc import Generator

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
