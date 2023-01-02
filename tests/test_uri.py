import pytest

from dcqc.uri import URI


def test_for_error_if_uri_scheme_is_missing():
    with pytest.raises(ValueError):
        URI("/path/to/file.txt")


def test_that_identical_uris_are_equal():
    uri_1 = URI("foo://bar")
    uri_2 = URI("foo://bar")
    assert uri_1 == uri_2


def test_that_uri_is_equal_to_equivalent_string():
    uri = URI("foo://bar")
    string = "foo://bar"
    assert uri == string


def test_that_uri_is_not_equal_to_a_non_string_value():
    uri = URI("foo://bar")
    integer = 123
    assert uri != integer
