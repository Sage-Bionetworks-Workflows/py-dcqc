"""Top-level dcqc module."""

# isort: skip_file

from importlib.metadata import PackageNotFoundError, version  # pragma: no cover

try:
    dist_name = __name__
    __version__ = version(dist_name)
except PackageNotFoundError:  # pragma: no cover
    __version__ = "unknown"
finally:
    del version, PackageNotFoundError

import logging

# Import suites to ensure that they are defined and thus discoverable
# It is located here to avoid a circular import
from dcqc import tests
from dcqc.suites import suite_abc
from dcqc.suites import suites

# Set default logging handler to avoid "No handler found" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())
logging.captureWarnings(True)
