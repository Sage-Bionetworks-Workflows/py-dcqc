from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass

from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.utils import validate_from_dict


# TODO: Eventually, there might be target-specific metadata
# TODO: Now that Target is much simpler, it might make sense
#       to rename the class to FileSet since it currently
#       really is just a wrapper for a group of files
# TODO: Maybe the Composite pattern would work here?
@dataclass
class Target(SerializableMixin):
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
        dictionary = validate_from_dict(cls, dictionary)
        files = [File.from_dict(d) for d in dictionary["files"]]
        target = cls(*files)
        return target
