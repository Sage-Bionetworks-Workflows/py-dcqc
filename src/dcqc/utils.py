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
