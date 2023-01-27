"""Represent local and remote files and their metadata.

See module dcqc.target for the multi-file target class.

Classes:

    FileType: For collecting file type-specific information.
    File: For bundling file location and metadata as well as
    operations for retrieving file contents.
"""

from __future__ import annotations

import os
from collections.abc import Collection, Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, ClassVar, Optional
from warnings import warn

from fs.base import FS

from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.utils import is_url_local, open_parent_fs


@dataclass
class FileType:
    """Bundle information for a given file type."""

    _registry: ClassVar[dict[str, FileType]]
    _registry = dict()

    name: str
    file_extensions: tuple[str, ...]
    edam_iri: Optional[str]

    def __init__(
        self,
        name: str,
        file_extensions: Collection[str],
        edam_iri: Optional[str] = None,
    ):
        """Construct a FileType object.

        Args:
            name: File type name.
            file_extensions: Valid file extensions.
            edam_iri: EDAM format ontology identifier.
        """
        self.name = name
        self.file_extensions = tuple(file_extensions)
        self.edam_iri = edam_iri
        self.register_file_type()

    def register_file_type(self) -> None:
        """Register instantiated file type for later retrieval.

        Raises:
            ValueError: If the file type's name has already
                been registered previously.
        """
        name = self.name.lower()
        if name in self._registry:
            message = f"File type ({name}) is already registered ({self._registry})."
            raise ValueError(message)
        self._registry[name] = self

    @classmethod
    def get_file_type(cls, file_type: str) -> FileType:
        """Retrieve file type object based on its name.

        Args:
            file_type: File type name.

        Raises:
            ValueError: If the given file type name has
                not been registered previously.

        Returns:
            The file type object with the given name.
        """
        file_type = file_type.lower()
        if file_type not in cls._registry:
            types = list(cls._registry)
            message = f"File type ({file_type}) not among available options ({types})."
            raise ValueError(message)
        return cls._registry[file_type]


# TODO: These file types could be moved to an external file
# Instantiated file types are automatically tracked by the FileType class
FileType("*", (), "format_1915")  # To represent all file types
FileType("TXT", (".txt",), "format_1964")
FileType("JSON", (".json",), "format_3464")
FileType("JSON-LD", (".jsonld",), "format_3749")
FileType("TIFF", (".tif", ".tiff"), "format_3591")
FileType("OME-TIFF", (".ome.tif", ".ome.tiff"), "format_3727")


@dataclass
class File(SerializableMixin):
    """Construct a File object.

    Args:
        url: Local or remote location of a file.
        metadata: File metadata.
        relative_to: Used to update any local URLs if they
            are relative to a directory other than the
            current work directory (default).
    """

    url: str
    metadata: dict[str, Any]
    type: str
    local_path: Optional[Path]

    def __init__(
        self,
        url: str,
        metadata: Optional[Mapping[str, Any]] = None,
        relative_to: Optional[Path] = None,
        local_path: Optional[Path] = None,
    ):
        self.url = self._relativize_url(url, relative_to)
        metadata = metadata or dict()
        self.metadata = dict(metadata)
        self.type = self._pop_file_type()

        self._fs: Optional[FS]
        self._fs = None
        self._fs_path: Optional[str]
        self._fs_path = None
        self._name: Optional[str]
        self._name = None

        self.local_path = local_path or self._init_local_path()

    def __hash__(self):
        return hash((self.url, self.type, tuple(self.metadata.items())))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def _relativize_url(self, url: str, relative_to: Optional[Path]) -> str:
        """Update local URLs if relative to a directory other than CWD.

        Args:
            url: Local or remote location of a file.
            relative_to: Used to update any local URLs if they
                are relative to a directory other than the
                current work directory (default).

        Returns:
            The relativized URL.
        """
        if self.is_url_local(url):
            relative_to = relative_to or Path.cwd()
            scheme, separator, resource = url.rpartition("://")
            path = Path(resource)
            if not path.is_absolute():
                resource = os.path.relpath(relative_to / resource)
            url = f"{scheme}{separator}{resource}"
        elif not self.is_url_local(url) and relative_to is not None:
            message = f"URL ({url}) is remote. Ignoring relative_to ({relative_to})."
            warn(message)
        return url

    def _pop_file_type(self) -> str:
        """Extract and remove file type from metadata.

        This function defaults to the generic file type
        ("*") if the key is absent from the metadata.

        Returns:
            The name of the file type in the metadata.
        """
        file_type = self.metadata.pop("file_type", "*")
        return file_type

    def _init_local_path(self) -> Optional[Path]:
        """Initialize local path depending on URL

        Returns:
            The local path, if applicable.
        """
        if self.is_url_local():
            local_path_str = self.fs.getsyspath(self.fs_path)
            local_path = Path(local_path_str)
            # Use relative paths for portability (e.g., in Nextflow)
            local_path = local_path.relative_to(Path.cwd())
        else:
            local_path = None
        return local_path

    def _init_fs(self) -> tuple[FS, str]:
        """Initialize file system to access URL.

        All queries with this file system should use
        `self._fs_path` as the path, not `self.url`.

        Returns:
            A file system + basename pair.
        """
        fs, fs_path = open_parent_fs(self.url)
        self._fs_path = fs_path
        self._fs = fs
        return fs, fs_path

    @property
    def fs(self) -> FS:
        """The file system that can access the URL."""
        fs = self._fs
        if fs is None:
            fs, _ = self._init_fs()
        return fs

    @property
    def fs_path(self) -> str:
        """The path that can be used with the file system."""
        fs_path = self._fs_path
        if fs_path is None:
            _, fs_path = self._init_fs()
        return fs_path

    @property
    def name(self) -> str:
        """The file name according to the file system."""
        name = self._name
        if name is None:
            info = self.fs.getinfo(self.fs_path)
            name = info.name
        return name

    def get_file_type(self) -> FileType:
        """Retrieve the relevant file type object.

        Returns:
            FileType: File type object
        """
        return FileType.get_file_type(self.type)

    def get_metadata(self, key: str) -> Any:
        """Retrieve file metadata using a key.

        Args:
            key: Metadata key name.

        Raises:
            KeyError: If the metadata key doesn't exist.

        Returns:
            The metadata value associated with the given key.
        """
        if key not in self.metadata:
            url = self.url
            md = self.metadata
            message = f"File ({url}) does not have '{key}' in its metadata ({md})."
            raise KeyError(message)
        return self.metadata[key]

    def is_url_local(self, url: Optional[str] = None) -> bool:
        """Check whether a URL refers to a local location.

        Args:
            url: Local or remote location of a file.
                Defaults to URL associated with file.

        Returns:
            Whether the URL refers to a local location.
        """
        url = url or self.url
        return is_url_local(url)

    def is_file_local(self) -> bool:
        """Check if the file (or a copy) is available locally.

        Unlike :func:`~dcqc.file.File.is_url_local`, this method
        considers if a locally staged copy is available regardless
        of whether the URL is local or remote.

        To retrieve the location of the local copy, you can use
        :func:`~dcqc.file.File.get_local_path`.

        Returns:
            Whether the file has a copy available locally.
        """
        return self.local_path is not None

    def get_local_path(self) -> Path:
        """Retrieve the path of a local copy, if applicable.

        Raises:
            FileNotFoundError: If there is no local copy available.

        Returns:
            The path to the local copy.
        """
        if self.local_path is None:
            message = "Local path is unavailable. Use stage() to create a local copy."
            raise FileNotFoundError(message)
        return Path(self.local_path)

    def stage(
        self,
        destination: Optional[Path] = None,
        overwrite: bool = False,
    ) -> Path:
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
        if not destination:
            if self.local_path is not None:
                return self.get_local_path()
            else:
                destination_str = mkdtemp()
                destination = Path(destination_str)

        # By this point, destination is defined (not None)
        if destination.is_dir():
            destination = destination / self.name

        if not destination.parent.exists():
            dest = str(destination)
            message = f"Parent folder of destination ({dest}) does not exist."
            raise ValueError(message)

        if destination.exists() and not overwrite:
            dest = str(destination)
            message = f"Destination ({dest}) already exists. Enable overwrite."
            raise FileExistsError(message)

        # By this point, the file either doesn't exist or overwrite is enabled
        destination.unlink(missing_ok=True)

        if self.is_url_local():
            local_path = self.get_local_path()
            destination.symlink_to(local_path.resolve())
        else:
            with destination.open("wb") as dest_file:
                self.fs.download(self.fs_path, dest_file)

        self.local_path = destination
        return destination

    @wraps(SerializableMixin.to_dict)
    def to_dict(self) -> SerializedObject:
        dictionary = super(File, self).to_dict()
        # Including the file name in the output for better readability for
        # unstaged remote files with cryptic URLs (e.g., syn://syn98765432)
        dictionary["name"] = self.name
        return dictionary

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> File:
        """Deserialize a dictionary into a file.

        Args:
            dictionary: A serialized file object.

        Returns:
            The reconstructed file object.
        """
        dictionary = deepcopy(dictionary)

        file_type = dictionary.pop("type")
        dictionary["metadata"]["file_type"] = file_type

        if dictionary["local_path"] is not None:
            dictionary["local_path"] = Path(dictionary["local_path"])

        # Ignore serialized name since it's a dynamically-computed property
        dictionary.pop("name", None)

        return cls(**dictionary)
