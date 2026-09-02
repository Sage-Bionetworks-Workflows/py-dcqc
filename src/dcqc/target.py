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

    A target groups the files that a QC test runs against.
    Subclasses restrict how many files are allowed: SingleTarget
    accepts exactly one file, and PairedTarget accepts exactly two.

    Subclasses are registered for deserialization by name, but only
    once their module has been imported.

    Args:
        file_or_files: A single file, or a list of files. A single
            file is wrapped in a list.
        id: A unique identifier for the target. Defaults to None.

    Attributes:
        files: The list of file objects.
        id: A unique identifier for the target. Defaults to None.
        type: The name of the target subclass. It is filled in
            automatically and becomes the "type" key when the target
            is serialized.
    """

    file_or_files: InitVar[File | list[File]]
    id: Optional[str] = None
    files: list[File] = field(init=False)
    type: str = field(init=False)

    def __post_init__(self, file_or_files: File | list[File]):
        """Store the files as a list and fill in the target type.

        Args:
            file_or_files: A single file, or a list of files. A single
                file is wrapped in a list.
        """
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
        """Create a local copy of every file in the target.

        A destination is not required for remote files; it
        defaults to a temporary directory.
        Local files aren't moved if a destination is omitted.

        Args:
            destination: File or folder where to store the files.
                Defaults to None.
            overwrite: Whether to ignore existing file at the
                target destination. Defaults to False.

        Raises:
            ValueError: If the parent directory of the
                destination does not exist.
            FileExistsError: If the destination file already
                exists and overwrite was not enabled.

        Returns:
            The paths of the local copies, in the same order as the
            files attribute.
        """
        paths = list()
        for file in self.files:
            path = file.stage(destination, overwrite)
            paths.append(path)
        return paths

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> BaseTarget:
        """Deserialize a dictionary into a target.

        The "type" value names the target subclass, whose module must
        already be imported for the lookup to find it. The dictionary
        is copied first, so the argument is not modified.

        Args:
            dictionary: A serialized target object. It must have the
                keys "type", "files" and "id".

        Raises:
            ValueError: If the "type" value does not name a registered
                subclass, or does not match the subclass it selects.

        Returns:
            The reconstructed target object.
        """
        target_cls_name = dictionary["type"]
        target_cls = BaseTarget.get_subclass_by_name(target_cls_name)
        dictionary = deepcopy(dictionary)
        dictionary = target_cls.from_dict_prepare(dictionary)
        files = [File.from_dict(d) for d in dictionary["files"]]
        id = dictionary["id"]
        target = target_cls(files, id=id)
        return target

    @classmethod
    def get_base_class(cls):
        """Retrieve the class that anchors the subclass registry.

        Returns:
            The BaseTarget class. A lookup by name always resolves
            through it, and never through cls, so BaseTarget itself is
            not part of the registry.
        """
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
