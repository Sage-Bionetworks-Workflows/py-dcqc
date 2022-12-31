import pytest

from dcqc.uri import URI


def test_for_error_if_uri_scheme_is_missing():
    with pytest.raises(ValueError):
        URI("/path/to/file.txt")
