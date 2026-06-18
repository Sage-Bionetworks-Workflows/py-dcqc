def is_url_local(url: str) -> bool:
    """Check whether a URL refers to a local location.

    A URL is considered local if it uses the file:// scheme or contains
    no scheme separator (://), which covers bare absolute and relative paths.
    Any other scheme (s3://, memory://, syn://, etc.) is treated as remote.

    Note: this classifier does not distinguish between file:// authority
    forms. A file:// URL with a non-empty authority (e.g. file://host/path)
    is reported as local here, but only the empty-authority form file:///path
    can be resolved to a correct on-disk path. Host-bearing forms are rejected
    at File construction (see File._validate_url), so they should not reach
    this function in practice.

    Args:
        url: Local or remote location of a file.

    Returns:
        Whether the URL refers to a local location.
    """
    return bool(url) and (url.startswith("file://") or "://" not in url)
