import fsspec
from fsspec.spec import AbstractFileSystem


def is_url_local(url: str) -> bool:
    """Check whether a URL refers to a local location.

    A URL is considered local if it uses the file:// scheme or contains
    no scheme separator (://), which covers bare absolute and relative paths.
    Any other scheme (s3://, memory://, syn://, etc.) is treated as remote.

    Args:
        url: Local or remote location of a file.

    Returns:
        Whether the URL refers to a local location.
    """
    return bool(url) and (url.startswith("file://") or "://" not in url)


def open_parent_fs(url: str) -> tuple[AbstractFileSystem, str]:
    """Open an fsspec filesystem for the given URL.

    Wraps fsspec.url_to_fs to return a filesystem instance appropriate
    for the URL scheme (local, S3, GCS, etc.) along with the path within
    that filesystem.

    Args:
        url: Local or remote location of a file, e.g. /tmp/file.txt,
            file:///tmp/file.txt, or s3://bucket/key.txt.

    Returns:
        A tuple of (filesystem, path) where filesystem is an
        AbstractFileSystem instance and path is the location of the
        file within that filesystem.
    """
    return fsspec.url_to_fs(url)
