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

from fs.opener import registry

# Import suites to ensure that they are defined and thus discoverable
# It is located here to avoid a circular import
from dcqc.suites import suite_abc
from dcqc.suites import suites

from dcqc.filesystems.openers import SynapseFSOpener
from dcqc.filesystems.synapsefs import SynapseFS

# Set default logging handler to avoid "No handler found" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())
logging.captureWarnings(True)

# Register PyFileSystem SynapseFS opener
registry.install(SynapseFSOpener)
