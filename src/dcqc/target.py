from __future__ import annotations

from abc import ABC
from copy import deepcopy
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import Optional

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin, SerializedObject, SubclassRegistryMixin


# TODO: Eventually, there might be target-specific metadata
@dataclass
class BaseTarget(SerializableMixin, SubclassRegistryMixin, ABC):
    """Base class for targets with one or more files.

    Attributes:
        files: List of files objects.
        id: A unique identifier for the target. Defaults to None.
        type: The target type/subclass.
    """

    file_or_files: InitVar[File | list[File]]
    id: Optional[str] = None
    files: list[File] = field(init=False)
    type: str = field(init=False)

    def __post_init__(self, file_or_files: File | list[File]):
        """Ensure list of files and fill in Target type."""
        self.type = self.__class__.__name__
        if isinstance(file_or_files, File):
            self.files = [file_or_files]
        else:
            self.files = file_or_files

    def stage(
        self,
        destination: Optional[Path] = None,
        overwrite: bool = False,
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

    def __post_init__(self, file_or_files: File | list[File]):
        """Run validation checks after initialization."""
        super().__post_init__(file_or_files)
        self.ensure_single_file()

    # While this function makes sense as a pydantic validator,
    # we can into strange issues with the following test after
    # switching to @pydantic.dataclasses.dataclass:
    # test_that_paths_are_unchanged_when_not_using_serialize_paths_relative_to
    def ensure_single_file(self):
        """Ensure that target is only initialized with a single file."""
        if len(self.files) != 1:
            raise ValueError("SingleTarget is restricted to single files")

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


@dataclass(init=False)
class PairedTarget(BaseTarget):
    """Paired (two-file) target."""

    def __post_init__(self, file_or_files: File | list[File]):
        """Run validation checks after initialization."""
        super().__post_init__(file_or_files)
        self.ensure_two_files()

    def ensure_two_files(self):
        """Ensure that target is only initialized with two files."""
        if len(self.files) != 2:
            raise ValueError("PairedTarget is restricted to two files")
