"""Tests for util functions"""

import pytest
from fsspec.implementations.local import LocalFileSystem
from fsspec.implementations.memory import MemoryFileSystem

from dcqc.utils import is_url_local, open_parent_fs


class TestIsUrlLocal:
    """Tests for is_url_local."""

    @pytest.mark.parametrize(
        "url, expected",
        [
            # file:// scheme is local
            ("file:///absolute/path/to/file.txt", True),
            ("file://localhost/path/to/file.txt", True),
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


class TestOpenParentFs:
    """Tests for open_parent_fs."""

    @pytest.mark.parametrize(
        "url, expected_fs_type, expected_path",
        [
            ("/home/user/some/file.txt", LocalFileSystem, "/home/user/some/file.txt"),
            (
                "file:///home/user/some/file.txt",
                LocalFileSystem,
                "/home/user/some/file.txt",
            ),
            ("memory://some/file.txt", MemoryFileSystem, "/some/file.txt"),
        ],
    )
    def test_returns_correct_fs_and_path(
        self, url: str, expected_fs_type: type, expected_path: str
    ) -> None:
        """Verify the correct filesystem type and path are returned for each URL."""
        fs, path = open_parent_fs(url)
        assert isinstance(fs, expected_fs_type)
        assert path == expected_path
