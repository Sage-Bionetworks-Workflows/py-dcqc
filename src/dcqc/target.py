from __future__ import annotations

from collections.abc import Collection
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Optional

from dcqc.file import File
from dcqc.utils import validate_from_dict


@dataclass
class Target:
    type: str
    files: list[File]

    def __init__(self, *file_args: File, files: Optional[Collection[File]] = None):
        self.type = self.__class__.__name__
        files = files or list()
        all_files = list(file_args) + list(files)
        self.files = all_files

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, dictionary: dict) -> Target:
        dictionary = deepcopy(dictionary)
        dictionary = validate_from_dict(cls, dictionary)
        files = [File.from_dict(d) for d in dictionary["files"]]
        target = cls(*files)
        return target
