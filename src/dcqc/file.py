from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Optional

from fs import open_fs


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


# Instantiated file types are automatically tracked by the FileType class
FileType("*", ())  # To represent all file types
FileType("TXT", (".txt",))
FileType("TIFF", (".tif", ".tiff"))
FileType("OME-TIFF", (".ome.tif", ".ome.tiff"))


@dataclass
class File:
    url: str
    metadata: dict[str, Any]
    type: str

    LOCAL_REGEX = re.compile(r"((file|osfs)://)?/?[^:]+")

    def __init__(self, url: str, metadata: Mapping[str, Any]):
        self.url = str(url)
        self.metadata = dict(metadata)
        self.type = self._pop_file_type()

    def _pop_file_type(self) -> str:
        file_type = self.get_metadata("file_type")
        del self.metadata["file_type"]
        return file_type

    def get_file_type(self) -> FileType:
        return FileType.get_file_type(self.type)

    def get_metadata(self, key: str) -> Any:
        if key not in self.metadata:
            url = self.url
            md = self.metadata
            message = f"File ({url}) does not have '{key}' in its metadata ({md})."
            raise ValueError(message)
        return self.metadata[key]

    def is_local(self):
        return self.LOCAL_REGEX.fullmatch(self.url) is not None

    # TODO: Create a new instance attribute `self._local_path` for keeping
    #       track of the local path instead of overwriting `self.url`
    def get_local_path(self):
        if not self.is_local():
            self.stage()
        _, _, local_path = self.url.rpartition("://")
        return local_path

    def stage(self, destination: Optional[str] = None) -> str:
        # Split off prefix to avoid issues with `rpartition("/")`
        scheme, separator, path = self.url.rpartition("://")
        if separator == "":
            prefix = "osfs://"
        else:
            prefix = scheme + separator

        # Check if there is only one part in the file URL
        # If so, append `../` to open its parent directory
        parent_path, _, base_name = path.rpartition("/")
        if parent_path == "":
            parent_path = f"{base_name}/.."

        parent_url = prefix + parent_path
        fs = open_fs(parent_url)
        destination = destination or fs.getinfo(base_name).name
        with open(destination, "wb") as staged_file:
            fs.download(base_name, staged_file)
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
