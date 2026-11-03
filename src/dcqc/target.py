from __future__ import annotations

from abc import ABC
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Optional, TypeVar, get_args, get_origin

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin, SerializedObject, SubclassRegistryMixin


# TODO: Eventually, there might be target-specific metadata
@dataclass
class BaseTarget(SerializableMixin, SubclassRegistryMixin, ABC):
    """Base class for targets with one or more files.

    A target groups the files that a QC test runs against. All files
    of a target have the same file type. Subclasses set n_files to
    restrict how many files are allowed: SingleTarget accepts exactly
    one file, and PairedTarget accepts exactly two.

    Subclasses are registered for deserialization by name, but only
    once their module has been imported.

    Args:
        files: The list of file objects. Give a list even when the
            target has only one file.
        id: A unique identifier for the target. Defaults to None.

    Attributes:
        n_files: The number of files that the target class accepts.
            None, the default, accepts any number of files, but at
            least one.
        files: The list of file objects.
        id: A unique identifier for the target. Defaults to None.
        type: The name of the target subclass. It is filled in
            automatically and becomes the "type" key when the target
            is serialized.
    """

    n_files: ClassVar[Optional[int]] = None

    files: list[File]
    id: Optional[str] = None
    type: str = field(init=False)

    def __post_init__(self) -> None:
        """Check the files argument and fill in the target type.

        Raises:
            TypeError: If files is not a list.
            ValueError: If validate_files finds a problem with the files.
        """
        if not isinstance(self.files, list):
            message = f"Target files must be a list, not {type(self.files)}."
            raise TypeError(message)
        self.type = self.__class__.__name__
        problems = self.validate_files(self.files)
        if problems:
            raise ValueError(f"{self.type} " + " ".join(problems))

    # While this check makes sense as a pydantic validator,
    # we can into strange issues with the following test after
    # switching to @pydantic.dataclasses.dataclass:
    # test_that_paths_are_unchanged_when_not_using_serialize_paths_relative_to
    @classmethod
    def validate_files(cls, files: list[File]) -> list[str]:
        """Check the files for a target of this class.

        The files must agree with n_files, and they must all have the
        same file type. The file count is checked first. If it is wrong,
        the file types are not checked.

        The method takes a list of files, not a target instance. Thus
        CsvParser can do the check before it stages the files, and add
        the row numbers to each message. __post_init__ uses the same
        check, so the rule is in one place.

        Args:
            files: The files to check.

        Raises:
            ValueError: If a file has an unknown file type.

        Returns:
            The problems that were found, or an empty list. Each message
            starts with "has", so that the caller can put the name of the
            target class or the rows in front of it.
        """
        # The file types are checked only if the file count is correct.
        problem = cls._check_file_count(files) or cls._check_file_types(files)
        return [problem] if problem else []

    @classmethod
    def _check_file_count(cls, files: list[File]) -> Optional[str]:
        """Check the number of files against n_files.

        Args:
            files: The files to check.

        Returns:
            A message that starts with "has", or None if the count is correct.
        """
        count = len(files)
        if count == 0:
            return "has no files. A target must have at least one file."
        if cls.n_files is not None and count != cls.n_files:
            noun = "file" if cls.n_files == 1 else "files"
            return (
                f"has a file count of {count}. A {cls.__name__} must have "
                f"exactly {cls.n_files} {noun}."
            )
        return None

    @classmethod
    def _check_file_types(cls, files: list[File]) -> Optional[str]:
        """Check that all of the files have the same file type.

        Args:
            files: The files to check. The list must not be empty.

        Raises:
            ValueError: If a file has an unknown file type.

        Returns:
            A message that starts with "has", or None if the file types agree.
        """
        file_types = [file.get_file_type() for file in files]
        if any(file_type != file_types[0] for file_type in file_types):
            names = [file_type.name for file_type in file_types]
            return (
                f"has different file types: {names}. The files of a "
                f"{cls.__name__} must have the same file type."
            )
        return None

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

    def get_file_type(self) -> FileType:
        """Retrieve the file type for the target.

        All files of a target have the same file type, because
        __post_init__ checks it. Thus this is the file type of the
        first file.

        Returns:
            The file type object.
        """
        return self.files[0].get_file_type()

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

    n_files: ClassVar[int] = 1

    @property
    def file(self):
        """Single file."""
        return self.files[0]


@dataclass(init=False)
class PairedTarget(BaseTarget):
    """Paired (two-file) target."""

    n_files: ClassVar[int] = 2


Target = TypeVar("Target", bound=BaseTarget)


def get_target_type_argument(cls: type, anchor: type) -> Optional[type[BaseTarget]]:
    """Get the target class that a class gives as the type argument of a base.

    BaseTest and SuiteABC are generic in Target. A subclass gives its
    target class one time, as the type argument of its base class, for
    example InternalBaseTest[SingleTarget] or FileSuite[PairedTarget].
    Base classes are evaluated when the class is defined, so this works
    on every supported Python version, with no eval.

    Only the bases in the class statement of cls are read, not the bases
    of its parents. Only a base whose origin is a subclass of anchor is
    read, so an unrelated generic base, for example SomeMixin[int], is
    ignored. A base whose type argument is still a TypeVar, for example
    SuiteABC[Target], is ignored too.

    Args:
        cls: The new class, from __init_subclass__.
        anchor: The generic root class, BaseTest or SuiteABC. This module
            cannot import them, because they import this module.

    Raises:
        TypeError: If the type argument is not a BaseTarget subclass, for
            example a Union, or if more than one base gives a target class.

    Returns:
        The target class, or None if cls gives no type argument. Then the
        caller keeps the target_cls that cls inherits from its parent.
    """
    target_classes: list[type[BaseTarget]] = []
    for base in cls.__dict__.get("__orig_bases__", ()):
        origin = get_origin(base)
        if not (isinstance(origin, type) and issubclass(origin, anchor)):
            continue
        args = get_args(base)
        if not args or isinstance(args[0], TypeVar):
            continue
        target_cls = args[0]
        if not (isinstance(target_cls, type) and issubclass(target_cls, BaseTarget)):
            message = (
                f"{cls.__name__} must give a BaseTarget subclass as the "
                f"target type, not {target_cls!r}."
            )
            raise TypeError(message)
        target_classes.append(target_cls)
    if len(target_classes) > 1:
        names = [target_cls.__name__ for target_cls in target_classes]
        message = f"{cls.__name__} must give one target type, not {names}."
        raise TypeError(message)
    return target_classes[0] if target_classes else None
