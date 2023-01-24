from __future__ import annotations

import os
import re
import shutil
import threading
from collections.abc import Collection, Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile, TemporaryDirectory, mkdtemp
from typing import Any, BinaryIO, Generator, Optional, Type

from fs import ResourceType
from fs.base import FS
from fs.errors import (
    CreateFailed,
    DirectoryExists,
    DirectoryExpected,
    DirectoryNotEmpty,
    FileExists,
    FileExpected,
    RemoveRootError,
    ResourceInvalid,
    ResourceNotFound,
)
from fs.info import Info
from fs.mode import Mode
from fs.permissions import Permissions
from fs.subfs import SubFS
from fs.time import datetime_to_epoch
from synapseclient.client import Synapse
from synapseclient.core.exceptions import SynapseFileNotFoundError, SynapseHTTPError
from synapseclient.core.utils import iso_to_datetime
from synapseclient.entity import Entity, File, Folder, Project, is_container

from dcqc.filesystems.remote_file import RemoteFile

RawInfo = Mapping[str, Mapping[str, object]]


@contextmanager
def synapse_errors(path: str) -> Generator:
    """A context manager for mapping ``synapseclient`` errors to ``fs`` errors."""
    try:
        yield
    except SynapseFileNotFoundError:
        raise ResourceNotFound(path)
    except SynapseHTTPError as err:
        message = err.args[0]
        if "does not exist" in message:
            raise ResourceNotFound(path)
        elif "already exists" in message:
            raise DirectoryExists(message)
        else:
            raise  # Raise original exception as is


class SynapseFS(FS):
    """A file system-like interface for Synapse."""

    NULL_BYTE = b"\x00"

    SYNID_REGEX = re.compile(r"syn[0-9]+")

    SUPPORTED_TYPES: dict[str, Type[Entity]]
    SUPPORTED_TYPES = {
        "file": File,
        "folder": Folder,
        "project": Project,
    }

    DEFAULT_SYNAPSE_ARGS: dict[str, Any]
    DEFAULT_SYNAPSE_ARGS = {
        "silent": True,
    }

    _meta = {
        "case_insensitive": False,
        "invalid_path_chars": "\0",
        "network": True,
        "read_only": False,
        "thread_safe": True,
        "unicode_paths": False,
        "virtual": False,
    }

    def __init__(
        self,
        root: Optional[str] = None,
        auth_token: Optional[str] = None,
        synapse_args: Optional[dict[str, Any]] = None,
    ) -> None:
        """Construct a Synapse filesystem for
        `PyFilesystem <https://pyfilesystem.org>`_

        Args:
            root: Synapse ID for a project or folder.
                Defaults to None (rootless mode).
            auth_token: Synapse personal access token.
                Defaults to None.
            synapse_args: Dictionary of arguments to pass to
                the ``Synapse`` class. Defaults to None.
        """
        super(SynapseFS, self).__init__()
        self.auth_token = auth_token
        self.synapse_args = synapse_args or self.DEFAULT_SYNAPSE_ARGS
        self._local = threading.local()
        self.root = self._resolve_root(root)

    @property
    def synapse(self) -> Synapse:
        """Construct a thread-local Synapse client.

        Returns:
            Synapse: Authenticated Synapse client
        """
        if not hasattr(self._local, "synapse"):
            # Override cache with temporary directory
            self.synapse_args["cache_root_dir"] = mkdtemp()
            synapse = Synapse(**self.synapse_args)
            synapse.login(authToken=self.auth_token)
            self._local.synapse = synapse
        # Clear the Synapse cache to avoid unwanted side effects. More info here:
        # https://github.com/Sage-Bionetworks-Workflows/py-dcqc/pull/3#discussion_r1068443214
        self._local.synapse.cache.purge(after_date=0)
        return self._local.synapse

    def is_synapse_id(self, text: str) -> bool:
        """Check whether the given text is a Synapse ID."""
        return self.SYNID_REGEX.fullmatch(text) is not None

    def _resolve_root(self, root: Optional[str]) -> Optional[str]:
        """Resolve the given root path (if not None) to a Synapse entity ID.

        Args:
            root (Optional[str]): Synapse ID for a project or folder.
                Defaults to None (rootless mode).

        Raises:
            CreateFailed: If the root is not or does not start with a Synapse ID.
            CreateFailed: If the root does not resolve to a project or folder.

        Returns:
            Optional[str]: A single Synapse ID to act as the root.
        """
        if root is None or root == "":
            return None

        root_path = PurePosixPath(root)
        num_root_parts = len(root_path.parts)
        error_message = f"Root ({root}) must be `None` or start with a Synapse ID."

        if num_root_parts == 1:
            if not self.is_synapse_id(root):
                raise CreateFailed(error_message)
        else:  # num_root_parts > 1
            starting_entity, _, path = root.strip("/").partition("/")
            if not self.is_synapse_id(starting_entity):
                raise CreateFailed(error_message)
            root = self._path_to_synapse_id(path, starting_entity)

        # Ensure that the root is not a file
        with synapse_errors(root):
            root_entity = self.synapse.get(root, downloadFile=False)
        if not is_container(root_entity):
            message = f"Root ({root}) must resolve to a project or folder."
            raise CreateFailed(message)

        return root

    def _path_to_synapse_id(
        self, path: str, starting_entity: Optional[str] = None
    ) -> str:
        """Resolve an FS path to a Synapse ID starting from the root.

        The slash-delimited parts of the given FS path can consist
        of folder/file names or Synapse IDs.

        If the SynapseFS instance does not have a root, then the
        given path must start with a Synapse ID.

        Args:
            path (str): Path to a resource on the filesystem
            starting_entity (str): Synapse ID for where to
                start the traversal. Defaults to the root.

        Returns:
            str: Synapse ID for the resolved file or folder

        Raises:
            ValueError: If the path does not start with a
                Synapse ID while SynapseFS is rootless.
            InvalidPath: If ``path`` is not absolute.
            ResourceNotFound: If the ``path`` does not
                resolve to existing entities.
        """
        original_path = path
        starting_entity = starting_entity or self.root

        if starting_entity is None:
            starting_entity, _, path = path.strip("/").partition("/")
            if not self.is_synapse_id(starting_entity):
                message = (
                    f"This SynapseFS is rootless, so the 1st part ({starting_entity}) "
                    f"of every path ({original_path}) must be a Synapse ID."
                )
                raise ValueError(message)

        # Starting with starting_entity, navigate the given path
        # by iterating each slash-delimited part
        current_entity = starting_entity
        for next_part in path.strip("/").split("/"):

            # Don't "move" if next_part refers to the root (which only happens once
            # at the beginning), the current directory, or an empty string
            if next_part in {"/", ".", ""}:
                continue

            # Move to the parent entity if next_part is the ".." symbol
            if next_part == "..":
                current_entity = self._get_parent_id(current_entity)
                continue

            # Otherwise, next_part should be the name or Synapse ID of a file/folder
            children_list = self._get_children(current_entity)
            # Build an "index" of children keyed on Synapse IDs or names
            # depending on whether next_part is a Synapse ID or not
            if self.is_synapse_id(next_part):
                children = {entity["id"]: entity for entity in children_list}
            else:
                children = {entity["name"]: entity for entity in children_list}
            # If next_part exists among the keys, return the associated Synapse ID
            if next_part in children:
                current_entity = children[next_part]["id"]
            else:
                raise ResourceNotFound(path)

        return current_entity

    def _synapse_id_to_entity(
        self,
        synapse_id: str,
        download_file: bool = False,
    ) -> Entity:
        """Retrieve and validate (meta)data for a Synapse entity

        Args:
            synapse_id (str): A Synapse ID
            download_file (bool): Whether to download the associated file(s)

        Returns:
            Entity: The associated Synapse entity

        Raises:
            ResourceNotFound: If ``synapse_id`` does not exist.
            ResourceInvalid: If ``synapse_id`` does not correspond
                 to a supported entity type.
        """
        with synapse_errors(synapse_id):
            entity = self.synapse.get(synapse_id, downloadFile=download_file)
        valid_types = tuple(self.SUPPORTED_TYPES.values())
        if not isinstance(entity, valid_types):
            type_ = type(entity)
            message = f"{synapse_id} ({type_}) is not supported yet ({valid_types})."
            raise ResourceInvalid(message)
        return entity

    def _path_to_entity(self, path: str, download_file: bool = False) -> Entity:
        """Perform the validation and retrieval steps for a Synapse entity.

        Arguments:
            path (str): A path.
            download_file (bool): Whether to download the associated file(s)

        Returns:
            Entity: A Synapse entity (File, Folder, or Project).
        """
        synapse_id = self._path_to_synapse_id(path)
        with synapse_errors(path):
            entity = self._synapse_id_to_entity(synapse_id, download_file)
        return entity

    def _path_to_parent_id(self, path: str) -> str:
        parent_path, _, basename = path.strip("/").rpartition("/")
        if parent_path == "":
            if self.root is not None:
                parent_id = self.root
            elif self.is_synapse_id(basename):
                parent_id = self._get_parent_id(basename)
            else:
                message = f"Path ({path}) must start with a Synapse ID when rootless."
                raise ValueError(message)
        else:
            parent_id = self._path_to_synapse_id(parent_path)
        return parent_id

    def _get_parent_id(self, entity_id: str) -> str:
        with synapse_errors(entity_id):
            entity = self.synapse.get(entity_id, downloadFile=False)
        if isinstance(entity, Project):
            message = f"Project ({entity.id}) has no parent."
            raise ValueError(message)
        parent_id = entity.parentId
        with synapse_errors(parent_id):
            parent = self.synapse.get(parent_id, downloadFile=False)
        return parent.id

    def _get_children(self, entity_id: str) -> list[dict]:
        """Retrieve a list of children for a Synapse entity

        Args:
            entity_id (str): The Synapse ID of a project or folder.

        Returns:
            list[dict]: List of children entities.
        """
        include_types = list(self.SUPPORTED_TYPES.keys())
        with synapse_errors(entity_id):
            children = self.synapse.getChildren(entity_id, includeTypes=include_types)
        return list(children)

    def getinfo(self, path: str, namespaces: Optional[Collection[str]] = None) -> Info:
        """Get information about a resource on a filesystem.

        Arguments:
            path (str): A path to a resource on the filesystem.
            namespaces (list, optional): Info namespaces to query. The
                `"basic"` namespace is alway included in the returned
                info, whatever the value of `namespaces` may be.

        Returns:
            ~fs.info.Info: resource information object.

        Raises:
            ResourceNotFound: If ``path`` does not exist.

        For more information regarding resource information,
            see :ref:`pyfilesystem:info`.

        """
        self.validatepath(path)
        entity = self._path_to_entity(path)

        raw_info = dict()
        namespaces = namespaces or ()
        name = entity.name
        is_dir = is_container(entity)
        is_file = not is_dir
        raw_info["basic"] = {
            "name": name,
            "is_dir": not is_file,  # Folder and projects are both file containers
        }

        if "details" in namespaces:
            size = entity._file_handle.contentSize if is_file else 0
            type_ = ResourceType.file if is_file else ResourceType.directory

            raw_info["details"] = {
                "accessed": None,
                "created": datetime_to_epoch(iso_to_datetime(entity.createdOn)),
                "metadata_changed": datetime_to_epoch(
                    iso_to_datetime(entity.modifiedOn)
                ),
                "modified": datetime_to_epoch(iso_to_datetime(entity.modifiedOn)),
                "size": size,
                "type": type_,
                "_write": [],
            }

        if "synapse" in namespaces:
            creator_id = int(entity.createdBy)
            creator = self.synapse.getUserProfile(creator_id)
            creator_username = creator["userName"]

            modifier_id = int(entity.modifiedBy)
            modifier = self.synapse.getUserProfile(modifier_id)
            modifier_username = modifier["userName"]

            raw_info["synapse"] = {
                "concrete_type": entity.concreteType,
                "short_type": entity.concreteType.split(".")[-1],
                "creator_id": creator_id,
                "creator_username": creator_username,
                "etag": entity.etag,
                "id": entity.id,
                "modifier_id": modifier_id,
                "modifier_username": modifier_username,
                "parent_id": entity.parentId,
                "content_type": None,
                "content_md5": None,
                "version_label": None,
                "version_number": None,
                "_write": [],
            }

            if is_file:
                file_info = {
                    "content_type": entity._file_handle.contentType,
                    "content_md5": entity._file_handle.contentMd5,
                    "version_label": entity.versionLabel,
                    "version_number": entity.versionNumber,
                }
                raw_info["synapse"].update(file_info)

        if "annotations" in namespaces:
            raw_info["annotations"] = entity.annotations

        return Info(raw_info)

    def listdir(self, path: str) -> list[str]:
        """Get a list of the resource names in a directory.

        This method will return a list of the resources in a directory.
        A *resource* is a file, directory, or one of the other types
        defined in `~fs.enums.ResourceType`.

        Arguments:
            path (str): A path to a directory on the filesystem

        Returns:
            list: list of names, relative to ``path``.

        Raises:
            DirectoryExpected: If ``path`` is not a directory.
            ResourceNotFound: If ``path`` does not exist.
        """
        self.validatepath(path)
        entity = self._path_to_entity(path)

        if not is_container(entity):
            synapse_id = entity.id
            type_ = type(entity)
            message = f"{synapse_id} ({type_}) is not a folder or project."
            raise DirectoryExpected(message)

        children = self._get_children(entity.id)
        children_names = [child["name"] for child in children]

        return children_names

    def makedir(
        self,
        path: str,
        permissions: Optional[Permissions] = None,
        recreate: bool = False,
    ) -> SubFS[FS]:
        """Make a directory.

        Arguments:
            path (str): Path to directory from root.
            permissions (~fs.permissions.Permissions, optional): a
                `Permissions` instance, or `None` to use default.
            recreate (bool): Set to `True` to avoid raising an error if
                the directory already exists (defaults to `False`).

        Returns:
            ~fs.subfs.SubFS: a filesystem whose root is the new directory.

        Raises:
            DirectoryExists: If the path already exists.
            ResourceNotFound: If the path is not found.
        """
        self.validatepath(path)

        if path == "/":
            if recreate:
                return SubFS(self, path)
            else:
                message = "Root directory ('/') already exists."
                raise DirectoryExists(message)

        posix_path = PurePosixPath(path)
        folder_name = str(posix_path.name)
        parent = self._path_to_parent_id(path)

        folder = Folder(folder_name, parent)
        with synapse_errors(path):
            self.synapse.store(folder, createOrUpdate=recreate)

        return SubFS(self, folder.name)

    def openbin(
        self, path: str, mode: str = "r", buffering: int = -1, **options: Any
    ) -> BinaryIO:
        """Open a binary file-like object.

        Arguments:
            path (str): A path on the filesystem.
            mode (str): Mode to open file (must be a valid non-text mode,
                defaults to *r*). Since this method only opens binary files,
                the ``b`` in the mode string is implied.
            buffering (int): Buffering policy (-1 to use default buffering,
                0 to disable buffering, or any positive integer to indicate
                a buffer size).
            **options: keyword arguments for any additional information
                required by the filesystem (if any).

        Returns:
            io.IOBase: a *file-like* object.

        Raises:
            FileExpected: If ``path`` exists and is not a file.
            FileExists: If the ``path`` exists, and
                *exclusive mode* is specified (``x`` in the mode).
            ResourceNotFound: If ``path`` does not exist and
                ``mode`` does not imply creating the file, or if any
                ancestor of ``path`` does not exist.
        """
        self.validatepath(path)

        mode_obj = Mode(mode)
        mode_obj.validate_bin()

        posix_path = PurePosixPath(path)
        file_name = str(posix_path.name)

        try:
            info = self.getinfo(path)
            path_exists = True
            is_dir = info.is_dir
        except ResourceNotFound:
            path_exists = False
            is_dir = False

        if path_exists and is_dir:
            raise FileExpected(path)

        if path_exists and mode_obj.exclusive:
            raise FileExists(path)

        if not path_exists:
            if mode_obj.create:
                # Make sure the parent exists
                self._path_to_parent_id(path)
            else:
                raise ResourceNotFound(path)

        # Create temporary directory for housing files
        temp_dir = TemporaryDirectory()
        temp_path = temp_dir.name

        def on_close(remote_file: RemoteFile) -> None:
            """Called when the S3 file closes, to upload data."""
            # If the file is empty, add a null byte to bypass
            # Synapse restriction on empty files
            remote_file.seek(0, os.SEEK_END)
            if remote_file.tell() == 0:
                remote_file.write(self.NULL_BYTE)
            remote_file.raw.close()
            if mode_obj.create or mode_obj.writing:
                parent = self._path_to_parent_id(path)
                old_file_path = Path(remote_file.raw.name)
                new_file_path = old_file_path.parent / file_name
                shutil.move(old_file_path, new_file_path)
                with synapse_errors(path):
                    file = File(str(new_file_path), parent)
                    file = self.synapse.store(file)
            temp_dir.cleanup()

        # The existing file should be downloaded first
        mode_bin = mode_obj.to_platform_bin()
        if path_exists and (mode_obj.reading or mode_obj.appending):
            entity = self._path_to_entity(path)
            with synapse_errors(path):
                entity = self.synapse.get(entity, downloadLocation=temp_path)
            # TODO: Re-enable this if we identify a use case
            # Truncate "empty" files that only contain the null byte
            # with open(entity.path, "r+b") as f:
            #     if f.read(2) == self.NULL_BYTE:
            #         f.truncate(0)
            # Re-open the file using the specified mode
            target_file = open(entity.path, mode_bin, buffering)
        # Otherwise, any existing file will be ignored
        else:
            target_file = NamedTemporaryFile(
                mode_bin, buffering, delete=False, dir=temp_path
            )

        # Set position of file descriptor based on the mode
        if mode_obj.appending:
            target_file.seek(0, os.SEEK_END)
        else:
            target_file.seek(0, os.SEEK_SET)

        return RemoteFile(target_file, file_name, mode_obj, on_close)

    def remove(self, path: str) -> None:
        """Remove a file from the filesystem.

        Arguments:
            path (str): Path of the file to remove.

        Raises:
            FileExpected: If the path is a directory.
            ResourceNotFound: If the path does not exist.
        """
        self.validatepath(path)
        entity = self._path_to_entity(path)

        if is_container(entity):
            synapse_id = entity.id
            type_ = type(entity)
            message = f"{synapse_id} ({type_}) is a folder or project."
            raise FileExpected(message)

        self.synapse.delete(entity)

    def removedir(self, path: str) -> None:
        """Remove a directory from the filesystem.

        Arguments:
            path (str): Path of the directory to remove.

        Raises:
            DirectoryNotEmpty: If the directory is not empty (
                see `~fs.base.FS.removetree` for a way to remove the
                directory contents).
            DirectoryExpected: If the path does not refer to
                a directory.
            ResourceNotFound: If no resource exists at the
                given path.
            RemoveRootError: If an attempt is made to remove
                the root directory (i.e. ``'/'``)
        """
        if path == "/":
            message = "Cannot remove the root folder ('/')."
            raise RemoveRootError(message)

        self.validatepath(path)
        entity = self._path_to_entity(path)

        if not is_container(entity):
            synapse_id = entity.id
            type_ = str(type(entity))
            message = f"{synapse_id} ({type_}) is not a folder or project."
            raise DirectoryExpected(message)

        children = self.listdir(path)
        if len(children) > 0:
            type_ = "Folder" if isinstance(entity, Folder) else "Project"
            synapse_id = entity.id
            message = f"{type_} ({synapse_id}) is not empty ({children})."
            raise DirectoryNotEmpty(message)

        self.synapse.delete(entity)

    def setinfo(self, path: str, info: RawInfo) -> None:
        """Set info on a resource.

        This method is the complement to `~fs.base.FS.getinfo`
        and is used to set info values on a resource.

        Arguments:
            path (str): Path to a resource on the filesystem.
            info (dict): Dictionary of resource info.

        Raises:
            ResourceNotFound: If ``path`` does not exist
                on the filesystem

        The ``info`` dict should be in the same format as the raw
        info returned by ``getinfo(file).raw``.

        Example:
            >>> details_info = {"details": {
            ...     "modified": time.time()
            ... }}
            >>> my_fs.setinfo('file.txt', details_info)
        """
        # A placeholder to raise errors if called with an non-existing path
        self.validatepath(path)
        self._path_to_entity(path)
        # TODO: Implement some writeable info (e.g., annotations)
