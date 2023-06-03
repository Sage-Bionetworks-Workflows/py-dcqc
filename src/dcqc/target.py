from __future__ import annotations

from abc import ABC
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin, SerializedObject, SubclassRegistryMixin


# TODO: Eventually, there might be target-specific metadata
# TODO: Now that Target is much simpler, it might make sense
#       to rename the class to FileSet since it currently
#       really is just a wrapper for a group of files
# TODO: Maybe the Composite pattern would work here?
@dataclass
class BaseTarget(SerializableMixin, SubclassRegistryMixin, ABC):
    """Construct a multi-file Target.

    Targets ensure support for both single-file
    and multi-file tests.

    Args:
        *files: Sequence of files objects.
        id: A unique identifier for the target.
            Defaults to None.
    """

    files: list[File]
    id: Optional[str]
    type: str

    def __init__(self, *files: File, id: Optional[str] = None):
        self.type = self.__class__.__name__
        self.files = list(files)
        self.id = id
        self.__post_init__()

    def __post_init__(self):
        """Placeholder __post_init__ method."""

    def stage(
        self, destination: Optional[Path] = None, overwrite: bool = False
    ) -> list[Path]:
        """Create local copy of local or remote file.

        A destination is not required for remote files; it
        defaults to a temporary directory.
        Local files aren't moved if a destination is omitted.

        Args:
            destination: File or folder where to store the file.
                Defaults to None.
            overwrite: Whether to ignore existing file at the
                target destination. Defaults to False.

        Raises:
            ValueError: If the parent directory of the
                destination does not exist.
            FileExistsError: If the destination file already
                exists and ``overwrite`` was not enabled.

        Returns:
            The path of the local copy.
        """
        paths = list()
        for file in self.files:
            path = file.stage(destination, overwrite)
            paths.append(path)
        return paths

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> BaseTarget:
        """Deserialize a dictionary into a target.

        Args:
            dictionary: A serialized target object.

        Returns:
            The reconstructed target object.
        """
        target_cls_name = dictionary["type"]
        target_cls = BaseTarget.get_subclass_by_name(target_cls_name)
        dictionary = deepcopy(dictionary)
        dictionary = target_cls.from_dict_prepare(dictionary)
        files = [File.from_dict(d) for d in dictionary["files"]]
        id = dictionary["id"]
        target = target_cls(*files, id=id)
        return target

    @classmethod
    def get_base_class(cls):
        """Retrieve base class."""
        return BaseTarget


@dataclass(init=False)
class SingleTarget(BaseTarget):
    """Single-file target."""

    def __post_init__(self):
        """Run validation checks after initialization."""
        self.ensure_single_file()

    def ensure_single_file(self):
        """Ensure that target is only initialized with a single file.

        Args:
            value: List of files.

        Returns:
            List of files.
        """
        if len(self.files) != 1:
            raise ValueError("Target is restricted to single files")

    @property
    def file(self):
        """Single file."""
        return self.files[0]

    def get_file_type(self) -> FileType:
        """Retrieve the file type for the target.

        Returns:
            The file type object.
        """
        return self.file.get_file_type()
