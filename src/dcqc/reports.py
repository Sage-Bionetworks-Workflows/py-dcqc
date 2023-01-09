import json
from collections.abc import Iterator
from typing import Any, Optional

from fs.base import FS

from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.utils import open_parent_fs


class JsonReport:
    url: str

    def __init__(self, url: str, overwrite: bool = False) -> None:
        self.url = url
        self._fs, self._path = open_parent_fs(url)
        if self._fs.exists(self._path) and not overwrite:
            message = f"URL ({url}) already exists. Set `overwrite=True` to ignore."
            raise FileExistsError(message)

    def _get_fs(self) -> FS:
        return self._fs

    def to_file(self, obj: Any):
        with self._fs.open(self._path, "w") as outfile:
            json.dump(obj, outfile, indent=2)

    def generate(
        self,
        *items_: SerializableMixin,
        items: Optional[Iterator[SerializableMixin]] = None,
    ) -> list[SerializedObject]:
        all_items = items or list(items_)
        report = [item.to_dict() for item in all_items]
        return report

    def save(
        self,
        *items_: SerializableMixin,
        items: Optional[Iterator[SerializableMixin]] = None,
    ) -> list[SerializedObject]:
        report = self.generate(*items_, items=items)
        self.to_file(report)
        return report
