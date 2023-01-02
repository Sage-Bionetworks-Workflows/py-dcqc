from __future__ import annotations

import os
import re
import shutil
import threading
from collections.abc import Collection
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING, Any, BinaryIO, Optional
from warnings import warn

from fs import ResourceType
from fs.base import FS
from fs.errors import (
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

if TYPE_CHECKING:
    from fs.info import RawInfo


@contextmanager
def synapse_errors(path):
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
        elif "File size must be at least one byte" in message:
            message = (
                "File was empty during an attempted upload to Synapse. "
                "Synapse doesn't support empty files, so upload was skipped."
            )
            warn(message)
        else:
            raise  # Raise original exception as is


class SynapseFS(FS):
    """Construct a Synapse filesystem for
    `PyFilesystem <https://pyfilesystem.org>`_

    Args:
        root (str): Synapse ID for a project or folder.
        auth_token (str, optional): Synapse personal access token.
            Defaults to None.
        synapse_args (dict, optional): Dictionary of
            arguments to pass to the ``Synapse()`` class.
            Defaults to None.
    """

    DELIMITER = "/"
    CWD_SYMBOL = "."
    PARENT_DIR = ".."

    NULL_BYTE = b"\x00"

    SYNID_REGEX = re.compile(r"syn[0-9]+")

    SUPPORTED_TYPES = {
        "file": File,
        "folder": Folder,
        "project": Project,
    }

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
        root: str,
        auth_token: Optional[str] = None,
        synapse_args: Optional[dict] = None,
    ) -> None:
        self.root = root
        self.auth_token = auth_token
        self.synapse_args = synapse_args or self.DEFAULT_SYNAPSE_ARGS
        self._local = threading.local()
        super(SynapseFS, self).__init__()

    @property
    def synapse(self) -> Synapse:
        """Construct a thread-local Synapse client.

        Returns:
            Synapse: Authenticated Synapse client
        """
        if not hasattr(self._local, "synapse"):
            synapse = Synapse(**self.synapse_args)
            synapse.login(authToken=self.auth_token)
            self._local.synapse = synapse
        # Clear the Synapse cache to ensure up-to-date
        self._local.synapse.cache.purge(after_date=0)
        return self._local.synapse

    def _path_to_synapse_id(self, path: str) -> str:
        """Convert an FS path to a Synapse ID

        Args:
            path (str): Path to a resource on the filesystem

        Returns:
            str: Synapse ID for a file, folder, or project

        Raises:
            fs.errors.InvalidPath: If ``path`` is not absolute.
            fs.errors.ResourceNotFound: If the ``path`` does
                not resolve to existing entities.
        """
        self.validatepath(path)

        delim = self.DELIMITER
        if not path.startswith(delim):
            message = (
                f"Path ({path}) should be absolute (i.e., starting with a '{delim}'). "
                f"The leading '{delim}' refers to the root Synapse project or folder. "
                "Otherwise, the current working directory is assumed to be the root."
            )
            warn(message)

        posix_path = PurePosixPath(path)
        current_entity = self.root
        visited_parts = []
        for part in posix_path.parts:
            if part == self.DELIMITER or part == self.CWD_SYMBOL:
                continue
            if part == self.PARENT_DIR:
                visited_parts.pop()
                continue
            visited_parts.append(part)
            children_list = self._get_children(current_entity)
            children = {entity["name"]: entity for entity in children_list}
            if part in children:
                current_entity = children[part]["id"]
            else:
                visited_path = self.DELIMITER + self.DELIMITER.join(visited_parts)
                message = f"This Synapse entity ({visited_path}) does not exist."
                raise ResourceNotFound(path)

        return current_entity

    def _synapse_id_to_entity(self, synapse_id: str, download_file=False) -> Entity:
        """Retrieve and validate (meta)data for a Synapse entity

        Args:
            synapse_id (str): A Synapse ID
            download_file (bool): Whether to download the associated file(s)

        Returns:
            Entity: The associated Synapse entity

        Raises:
            fs.errors.ResourceNotFound: If ``synapse_id`` does not exist.
            fs.errors.ResourceInvalid: If ``synapse_id`` does not correspond
                 to a supported entity type.
        """
        entity = self.synapse.get(synapse_id, downloadFile=download_file)
        valid_types = list(self.SUPPORTED_TYPES.values())
        if not any(isinstance(entity, type_) for type_ in valid_types):
            type_ = type(entity)
            message = f"{synapse_id} ({type_}) is not supported yet ({valid_types})."
            raise ResourceInvalid(message)
        return entity

    def _path_to_entity(self, path: str, download_file=False) -> Entity:
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

    def _get_children(self, entity: str) -> list[dict]:
        """_summary_

        Args:
            entity (str): _description_

        Returns:
            list[dict]: _description_
        """
        include_types = list(self.SUPPORTED_TYPES.keys())
        children = self.synapse.getChildren(entity, includeTypes=include_types)
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
            fs.errors.ResourceNotFound: If ``path`` does not exist.

        For more information regarding resource information, see :ref:`info`.

        """
        raw_info = dict()
        namespaces = namespaces or ()
        entity = self._path_to_entity(path)

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
            fs.errors.DirectoryExpected: If ``path`` is not a directory.
            fs.errors.ResourceNotFound: If ``path`` does not exist.
        """
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
            fs.errors.DirectoryExists: If the path already exists.
            fs.errors.ResourceNotFound: If the path is not found.
        """
        if path == self.DELIMITER:
            if recreate:
                return SubFS(self, path)
            else:
                message = f"Root directory ('{self.DELIMITER}') already exists."
                raise DirectoryExists(message)

        posix_path = PurePosixPath(path)
        parent_path = str(posix_path.parent)
        folder_name = str(posix_path.name)
        parent = self._path_to_entity(parent_path)

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
            fs.errors.FileExpected: If ``path`` exists and is not a file.
            fs.errors.FileExists: If the ``path`` exists, and
                *exclusive mode* is specified (``x`` in the mode).
            fs.errors.ResourceNotFound: If ``path`` does not exist and
                ``mode`` does not imply creating the file, or if any
                ancestor of ``path`` does not exist.
        """
        self.validatepath(path)

        mode_obj = Mode(mode)
        mode_obj.validate_bin()

        posix_path = PurePosixPath(path)
        parent_path = str(posix_path.parent)
        file_name = str(posix_path.name)
        parent = self._path_to_entity(parent_path)

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

        if not path_exists and not mode_obj.create:
            raise ResourceNotFound(path)

        # Create temporary directory for housing files
        temp_dir = TemporaryDirectory()
        temp_path = temp_dir.name

        def on_close(remote_file):
            """Called when the S3 file closes, to upload data."""
            # If the file is empty, add a null byte to bypass
            # Synapse restriction on empty files
            remote_file.seek(0, os.SEEK_END)
            if remote_file.tell() == 0:
                remote_file.write(self.NULL_BYTE)
            remote_file.raw.close()
            if mode_obj.create or mode_obj.writing:
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
            # Truncate "empty" files that only contain the null byte
            with open(entity.path, "r+b") as f:
                if f.read(2) == self.NULL_BYTE:
                    f.truncate(0)
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

    def remove(self, path: str):
        """Remove a file from the filesystem.

        Arguments:
            path (str): Path of the file to remove.

        Raises:
            fs.errors.FileExpected: If the path is a directory.
            fs.errors.ResourceNotFound: If the path does not exist.
        """
        entity = self._path_to_entity(path)

        if is_container(entity):
            synapse_id = entity.id
            type_ = type(entity)
            message = f"{synapse_id} ({type_}) is a folder or project."
            raise FileExpected(message)

        self.synapse.delete(entity)

    def removedir(self, path: str):
        """Remove a directory from the filesystem.

        Arguments:
            path (str): Path of the directory to remove.

        Raises:
            fs.errors.DirectoryNotEmpty: If the directory is not empty (
                see `~fs.base.FS.removetree` for a way to remove the
                directory contents).
            fs.errors.DirectoryExpected: If the path does not refer to
                a directory.
            fs.errors.ResourceNotFound: If no resource exists at the
                given path.
            fs.errors.RemoveRootError: If an attempt is made to remove
                the root directory (i.e. ``'/'``)
        """
        if path == self.DELIMITER:
            message = f"Cannot remove the root folder ('{self.DELIMITER}')."
            raise RemoveRootError(message)

        entity = self._path_to_entity(path)

        if not is_container(entity):
            synapse_id = entity.id
            type_ = type(entity)
            message = f"{synapse_id} ({type_}) is not a folder or project."
            raise DirectoryExpected(message)

        children = self.listdir(path)
        if len(children) > 0:
            type_ = "Folder" if isinstance(entity, Folder) else "Project"
            synapse_id = entity.id
            message = f"{type_} ({synapse_id}) is not empty ({children})."
            raise DirectoryNotEmpty(message)

        self.synapse.delete(entity)

    def setinfo(self, path: str, info: RawInfo):
        """Set info on a resource.

        This method is the complement to `~fs.base.FS.getinfo`
        and is used to set info values on a resource.

        Arguments:
            path (str): Path to a resource on the filesystem.
            info (dict): Dictionary of resource info.

        Raises:
            fs.errors.ResourceNotFound: If ``path`` does not exist
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
        self._path_to_entity(path)
        # TODO: Implement some writeable info (e.g., annotations)
