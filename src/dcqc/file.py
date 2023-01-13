from __future__ import annotations

import os
import re
from collections.abc import Collection, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from dcqc.mixins import SerializableMixin
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
    def register_file_type(cls, self):
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
    url: str
    metadata: dict[str, Any]
    type: str

    LOCAL_REGEX = re.compile(r"((file|osfs)://)?/?[^:]+")

    def __init__(
        self,
        url: str,
        metadata: Mapping[str, Any],
        relative_to: Optional[Path] = None,
    ):
        relative_to = relative_to or Path.cwd()
        if self.is_local(url):
            scheme, separator, resource = url.rpartition("://")
            path = Path(resource)
            if not path.is_absolute():
                resource = os.path.relpath(relative_to / resource)
            url = "".join([scheme, separator, resource])
        self.url = str(url)
        self.metadata = dict(metadata)
        self.type = self._pop_file_type()
        self.file_name = self._get_file_name()
        self._fs = None

    @property
    def fs(self):
        if self._fs is None:
            fname = self.file_name
            fs, bname = open_parent_fs(self.url)
            if bname != fname:
                message = f"Inconsistent file names: FS ({bname}) and File ({fname})."
                raise ValueError(message)
            self._fs = fs
        return self._fs

    def _pop_file_type(self) -> str:
        file_type = self.get_metadata("file_type")
        del self.metadata["file_type"]
        return file_type

    def _get_file_name(self):
        path = PurePosixPath(self.url)
        return path.name

    def get_file_type(self) -> FileType:
        return FileType.get_file_type(self.type)

    def get_metadata(self, key: str) -> Any:
        if key not in self.metadata:
            url = self.url
            md = self.metadata
            message = f"File ({url}) does not have '{key}' in its metadata ({md})."
            raise ValueError(message)
        return self.metadata[key]

    def is_local(self, url: Optional[str] = None):
        url = url or self.url
        return self.LOCAL_REGEX.fullmatch(url) is not None

    # TODO: Create a new instance attribute `self._local_path` for keeping
    #       track of the local path instead of overwriting `self.url`
    def get_local_path(self) -> str:
        if not self.is_local():
            message = f"File ({self.url}) should first be downloaded using stage()."
            raise FileNotFoundError(message)
        local_path = self.url
        if local_path.startswith(("osfs://", "file://")):
            local_path = self.fs.getsyspath(self.file_name)
        return local_path

    def stage(self, destination: Optional[str] = None, overwrite: bool = False) -> str:
        """Download remote files and copy local files.

        A destination is required for remote files.
        Local files aren't moved if a destination is omitted.

        Args:
            destination (Optional[str]): File or folder path
                where to store the file. Defaults to None.
            overwrite (bool): Whether to ignore existing file
                at the target destination. Defaults to False.

        Raises:
            ValueError: If a destination is not specified
                when staging a remote file.
            ValueError: If the parent directory of the
                destination does not exist.
            FileExistsError: If the destination file already
                exists and ``overwrite`` was not enabled.

        Returns:
            str: The updated URL (i.e., location) of the file.
        """
        if not destination:
            if self.is_local():
                return self.url
            else:
                message = f"Destination is required for remote files ({self.url})."
                raise ValueError(message)

        # By this point, destination is defined (not None)
        file_name = self._get_file_name()
        destination_path = Path(destination)
        if destination_path.is_dir():
            destination_path = destination_path / file_name
            destination = destination_path.as_posix()

        if not destination_path.parent.exists():
            message = f"Parent folder of destination ({destination}) does not exist."
            raise ValueError(message)

        if destination_path.exists() and not overwrite:
            message = f"Destination ({destination}) already exists. Enable overwrite."
            raise FileExistsError(message)

        if self.is_local():
            local_path = self.get_local_path()
            destination_path.symlink_to(local_path)
        else:
            with open(destination, "wb") as dest_file:
                self.fs.download(self.file_name, dest_file)

        self.url = destination
        return self.url

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, dictionary: dict) -> File:
        dictionary = deepcopy(dictionary)
        file_type = dictionary.pop("type")
        dictionary["metadata"]["file_type"] = file_type
        file = cls(**dictionary)
        return file
