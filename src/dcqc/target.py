from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass

from dcqc.file import File
from dcqc.mixins import SerializableMixin


# TODO: Eventually, there might be target-specific metadata
# TODO: Now that Target is much simpler, it might make sense
#       to rename the class to FileSet since it currently
#       really is just a wrapper for a group of files
# TODO: Maybe the Composite pattern would work here?
@dataclass
class Target(SerializableMixin):
    """Construct a multi-file Target.

    Targets ensure support for both single-file
    and multi-file tests.

    Args:
        *files (File): Sequence of files objects.
    """

    type: str
    files: list[File]

    def __init__(self, *files: File):
        self.type = self.__class__.__name__
        self.files = list(files)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, dictionary: dict) -> Target:
        dictionary = deepcopy(dictionary)
        dictionary = cls.from_dict_prepare(dictionary)
        files = [File.from_dict(d) for d in dictionary["files"]]
        target = cls(*files)
        return target
