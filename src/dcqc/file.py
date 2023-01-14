from __future__ import annotations

import os
import re
from collections.abc import Collection, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Optional

from fs.base import FS

from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.utils import open_parent_fs


@dataclass
class FileType:
    # Class attributes
    # A type hint is omitted so this attribute isn't
    # picked up by @dataclass as an instance attribute
    _registry = dict()  # type: ignore

    # Instance attributes
    name: str
    file_extensions: tuple[str, ...]

    def __init__(self, name: str, file_extensions: Collection[str]):
        self.name = name
        self.file_extensions = tuple(file_extensions)
        self.register_file_type(self)

    @classmethod
    def register_file_type(cls, self: FileType) -> None:
        name = self.name.lower()
        if name in cls._registry:
            message = f"File type ({name}) is already registered ({self._registry})."
            raise ValueError(message)
        cls._registry[name] = self

    @classmethod
    def get_file_type(cls, file_type: str) -> FileType:
        file_type = file_type.lower()
        if file_type not in cls._registry:
            types = list(cls._registry)
            message = f"File type ({file_type}) not among available options ({types})."
            raise ValueError(message)
        return cls._registry[file_type]


# TODO: These file types could be moved to an external file
# Instantiated file types are automatically tracked by the FileType class
FileType("*", ())  # To represent all file types
FileType("TXT", (".txt",))
FileType("TIFF", (".tif", ".tiff"))
FileType("OME-TIFF", (".ome.tif", ".ome.tiff"))


@dataclass
class File(SerializableMixin):
    """Construct a File object.

    Args:
        url (str): URL indicating the location of the file.
        metadata (Mapping[str, Any]): File metadata.
        relative_to (Optional[Path]): Used to update any
            local URLs if they are relative to a directory
            other than the current work directory (default).
    """

    url: str
    metadata: dict[str, Any]
    type: str
    local_path: Optional[str]

    LOCAL_REGEX = re.compile(r"((file|osfs)://)?/?[^:]+")

    def __init__(
        self,
        url: str,
        metadata: Mapping[str, Any],
        relative_to: Optional[Path] = None,
        local_path: Optional[str] = None,
    ):
        self.url = self._relativize_url(url, relative_to)
        self.metadata = dict(metadata)
        self.type = self._pop_file_type()

        self._fs: Optional[FS]
        self._fs = None
        self._fs_path: Optional[str]
        self._fs_path = None
        self._name: Optional[str]
        self._name = None

        self.local_path = local_path or self._init_local_path()

    def _relativize_url(self, url: str, relative_to: Optional[Path]) -> str:
        """Update local URLs if relative to a directory other than CWD."""
        relative_to = relative_to or Path.cwd()
        if self.is_url_local(url):
            scheme, separator, resource = url.rpartition("://")
            path = Path(resource)
            if not path.is_absolute():
                resource = os.path.relpath(relative_to / resource)
            url = f"{scheme}{separator}{resource}"
        return url

    def _pop_file_type(self) -> str:
        file_type = self.get_metadata("file_type")
        del self.metadata["file_type"]
        return file_type

    def _init_local_path(self) -> Optional[str]:
        if self.is_url_local():
            local_path = self.fs.getsyspath(self.fs_path)
        else:
            local_path = None
        return local_path

    def _initialize_fs(self) -> tuple[FS, str]:
        """Retrieve and store parent FS and basename."""
        fs, fs_path = open_parent_fs(self.url)
        self._fs_path = fs_path
        self._fs = fs
        return fs, fs_path

    @property
    def fs(self) -> FS:
        fs = self._fs
        if fs is None:
            fs, _ = self._initialize_fs()
        return fs

    @property
    def fs_path(self) -> str:
        fs_path = self._fs_path
        if fs_path is None:
            _, fs_path = self._initialize_fs()
        return fs_path

    @property
    def name(self) -> str:
        name = self._name
        if name is None:
            info = self.fs.getinfo(self.fs_path)
            name = info.name
        return name

    def get_file_type(self) -> FileType:
        return FileType.get_file_type(self.type)

    def get_metadata(self, key: str) -> Any:
        if key not in self.metadata:
            url = self.url
            md = self.metadata
            message = f"File ({url}) does not have '{key}' in its metadata ({md})."
            raise ValueError(message)
        return self.metadata[key]

    def is_url_local(self, url: Optional[str] = None) -> bool:
        url = url or self.url
        return self.LOCAL_REGEX.fullmatch(url) is not None

    def is_file_local(self, url: Optional[str] = None) -> bool:
        return self.local_path is not None

    def get_local_path(self) -> Path:
        if self.local_path is None:
            message = "Local path is unavailable. Use stage() to create a local copy."
            raise ValueError(message)
        return Path(self.local_path)

    def stage(self, destination: Optional[str] = None, overwrite: bool = False) -> Path:
        """Download remote files and copy local files.

        A destination is required for remote files.
        Local files aren't moved if a destination is omitted.

        Args:
            destination (Optional[str]): File or folder path
                where to store the file. Defaults to None.
            overwrite (bool): Whether to ignore existing file
                at the target destination. Defaults to False.

        Raises:
            ValueError: If the parent directory of the
                destination does not exist.
            FileExistsError: If the destination file already
                exists and ``overwrite`` was not enabled.

        Returns:
            Path: The path of the local copy.
        """
        if not destination:
            if self.local_path is not None:
                return self.get_local_path()
            else:
                destination = mkdtemp()

        # By this point, destination is defined (not None)
        destination_path = Path(destination)
        if destination_path.is_dir():
            destination_path = destination_path / self.name
            destination = destination_path.as_posix()

        if not destination_path.parent.exists():
            message = f"Parent folder of destination ({destination}) does not exist."
            raise ValueError(message)

        if destination_path.exists() and not overwrite:
            message = f"Destination ({destination}) already exists. Enable overwrite."
            raise FileExistsError(message)

        if self.is_url_local():
            local_path = self.get_local_path()
            destination_path.symlink_to(local_path)
        else:
            with destination_path.open("wb") as dest_file:
                self.fs.download(self.fs_path, dest_file)

        self.local_path = destination_path.as_posix()
        return destination_path

    def to_dict(self) -> SerializedObject:
        return asdict(self)

    @classmethod
    def from_dict(cls, dictionary: dict) -> File:
        dictionary = deepcopy(dictionary)
        file_type = dictionary.pop("type")
        dictionary["metadata"]["file_type"] = file_type
        file = cls(**dictionary)
        return file
