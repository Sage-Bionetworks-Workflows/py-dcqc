"""Tests for util functions"""

import pytest

from dcqc.utils import is_url_local


class TestIsUrlLocal:
    """Tests for is_url_local."""

    @pytest.mark.parametrize(
        "url, expected",
        [
            # file:// scheme is local (empty-authority form only)
            ("file:///absolute/path/to/file.txt", True),
            # bare absolute paths (no scheme) are local
            ("/absolute/path/to/file.txt", True),
            # bare relative paths (no scheme) are local
            ("relative/path/to/file.txt", True),
            ("file.txt", True),
            # remote schemes are not local
            ("s3://bucket/key.txt", False),
            ("syn://syn12345678", False),
            ("memory://some/path", False),
            ("gs://bucket/key.txt", False),
            ("http://example.com/file.txt", False),
            ("https://example.com/file.txt", False),
            # osfs:// was treated as local by the old regex but is a
            # PyFilesystem-specific scheme no longer used with fsspec
            ("osfs:///some/path", False),
            # empty string is not a valid URL
            ("", False),
        ],
    )
    def test_url(self, url: str, expected: bool) -> None:
        """Verify local vs. remote classification across URL schemes and bare paths."""
        assert is_url_local(url) == expected
