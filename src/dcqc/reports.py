import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Optional, overload

from fs.base import FS
from fs.errors import ResourceNotFound

from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.utils import open_parent_fs


# TODO: Refactor instance methods to class methods
class JsonReport:
    paths_relative_to: Optional[Path]

    def __init__(self, paths_relative_to: Optional[Path] = None) -> None:
        self.paths_relative_to = paths_relative_to
        self._url: Optional[str] = None
        self._fs: Optional[FS] = None
        self._fs_path: Optional[str] = None

    # TODO: Move towards an FS mixin for these functions
    def _init_fs(self, url) -> tuple[FS, str]:
        self._url = url
        self._fs, self._fs_path = open_parent_fs(url)
        return self._fs, self._fs_path

    def _create_parent_directories(self, url: str):
        scheme, separator, resource = url.rpartition("://")
        parent_resource, _, _ = resource.rpartition("/")
        parent_url = f"{scheme}{separator}{parent_resource}"
        fs, fs_path = self._init_fs(parent_url)
        try:
            info = fs.getinfo(fs_path)
        except ResourceNotFound:
            fs.makedirs(fs_path, recreate=True)
            info = fs.getinfo(fs_path)
        if not info.is_dir:
            message = f"Parent URL ({url}) does not refer to a directory."
            raise NotADirectoryError(message)

    def to_file(self, obj: Any, url: str, overwrite: bool):
        fs, fs_path = self._init_fs(url)
        self._create_parent_directories(url)
        if fs.exists(fs_path) and not overwrite:
            message = f"URL ({url}) already exists. Enable `overwrite` to ignore."
            raise FileExistsError(message)
        # TODO: Implement custom serializer that handles Paths
        #       (e.g., relativize them based on output JSON path)
        with fs.open(fs_path, "w") as outfile:
            json.dump(obj, outfile, indent=2)
            outfile.write("\n")

    def _generate_single(self, item: SerializableMixin) -> SerializedObject:
        item.serialize_paths_relative_to(self.paths_relative_to)
        report = item.to_dict()
        return report

    # The overloads are necessary to convey the relationship between
    # the inputs and outputs: single to single, and many to many.
    @overload
    def generate(self, items: SerializableMixin) -> SerializedObject:
        """"""

    @overload
    def generate(self, items: Iterable[SerializableMixin]) -> list[SerializedObject]:
        """"""

    def generate(self, items):
        if isinstance(items, Iterable):
            report = [self._generate_single(item) for item in items]
        else:
            # In this else branch, `items` is actually a single item
            report = self._generate_single(items)
        return report

    @overload
    def save(
        self, items: SerializableMixin, url: str, overwrite: bool = False
    ) -> SerializedObject:
        """"""

    @overload
    def save(
        self, items: Iterable[SerializableMixin], url: str, overwrite: bool = False
    ) -> list[SerializedObject]:
        """"""

    def save(self, items, url: str, overwrite: bool = False):
        report = self.generate(items)
        self.to_file(report, url, overwrite)
        return report

    def save_many(
        self,
        named_items: Mapping[str, SerializableMixin],
        parent_url: str,
        overwrite: bool = False,
    ) -> dict[str, SerializedObject]:
        reports = dict()
        for name, item in named_items.items():
            report = self.generate(item)
            reports[name] = report
            report_url = f"{parent_url}/{name}"
            self.to_file(report, report_url, overwrite)
        return reports
