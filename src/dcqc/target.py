from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Iterator, Optional

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin, SerializedObject


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

    def __hash__(self):
        return hash(tuple(self.files))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def get_file_type(self) -> FileType:
        """Retrieve the file type for the target.

        This function currently only supports targets
        composed of a single file.

        Raises:
            NotImplementedError: If the target has
                more or less than one file.

        Returns:
            The file type object.
        """
        num_files = len(self.files)
        if num_files == 1:
            file = self.files[0]
            file_type = file.get_file_type()
        else:
            message = f"Target has {num_files} files, which isn't supported yet."
            raise NotImplementedError(message)
        return file_type

    @wraps(File.stage)
    def stage(
        self,
        destination: Optional[Path] = None,
        overwrite: bool = False,
    ) -> Iterator[Path]:
        for file in self.files:
            yield file.stage(destination, overwrite)

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> Target:
        """Deserialize a dictionary into a target.

        Args:
            dictionary: A serialized target object.

        Returns:
            The reconstructed target object.
        """
        dictionary = deepcopy(dictionary)
        dictionary = cls.from_dict_prepare(dictionary)
        files = [File.from_dict(d) for d in dictionary["files"]]
        target = cls(*files)
        return target
