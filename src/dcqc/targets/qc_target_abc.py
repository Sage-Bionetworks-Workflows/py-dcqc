from abc import ABC
from collections.abc import Mapping
from typing import Optional
from warnings import warn

from dcqc.uri import URI


class QcTargetABC(ABC):
    # Class properties
    used_uris: set[URI]
    used_indices: set[int]
    next_index: int

    # Instance properties
    uri: URI
    metadata: dict
    index: int

    def __init__(
        self,
        uri: str | URI,
        metadata: Optional[Mapping] = None,
        index: Optional[int] = None,
    ):
        self.type = self.__class__.__name__
        if isinstance(uri, str):
            uri = URI(uri)
        self.uri = self._process_uri(uri)
        metadata = metadata or dict()
        self.metadata = dict(metadata)  # Cast Mapping to dict
        self.index = self._process_index(index)

    def _process_uri(self, uri: URI):
        self._check_uri(uri)
        self.used_uris.add(uri)
        return uri

    def _check_uri(self, uri: URI):
        if uri in self.used_uris:
            warn(f"URI '{uri}' already used. URIs should probably be unique.")

    def _process_index(self, index: Optional[int]):
        if index is None:
            index = self._get_next_index()
        self._check_index(index)
        self.used_indices.add(index)
        return index

    def _check_index(self, index: int):
        if index < 0:
            raise ValueError(f"Index '{index}' should be a non-negative integer.")
        if index in self.used_indices:
            raise ValueError(f"Index '{index}' already used. Indices must be unique.")

    def _get_next_index(self) -> int:
        while self.next_index in self.used_indices:
            self.next_index += 1
        return self.next_index

    @classmethod
    def reset_memory(cls):
        cls.used_uris = set()
        cls.used_indices = set()
        cls.next_index = 0

    def to_dict(self, expanded=True):
        target_dict = {
            "type": self.type,
            "uri": self.uri,
            "metadata": self.metadata,
            "index": self.index,
        }
        return target_dict

    @classmethod
    def from_dict(cls, dictionary):
        if dictionary["type"] != cls.__name__:
            raise ValueError(
                f"The type ({dictionary}) doesn't match the class ({cls.__name__})."
            )
        target = cls(dictionary["uri"], dictionary["metadata"], dictionary["index"])
        return target


QcTargetABC.reset_memory()
