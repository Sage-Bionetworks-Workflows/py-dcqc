from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import asdict, fields, is_dataclass
from pathlib import Path, PurePath
from typing import Any, Optional, TypeVar, cast

SerializedObject = dict[str, Any]

T = TypeVar("T", bound="SerializableMixin")


class SerializableMixin(ABC):
    @classmethod
    def from_dict_prepare(cls, dictionary: SerializedObject) -> SerializedObject:
        """Validate and prepare dictionary for deserialization."""
        type_ = dictionary.pop("type")
        if type_ != cls.__name__:
            message = f"Type ({type_}) does not match the class ({cls.__name__})."
            raise ValueError(message)
        return dictionary

    # TODO: Move this logic to JsonReport as a JSONEncoder subclass
    def serialize_paths_relative_to(self, location: Optional[Path]):
        if location is not None and not location.exists() and location.is_dir():
            message = f"Location ({location}) is not an existing directory."
            raise ValueError(message)
        self._serialize_paths_relative_to = location

    def serialize_path(self, path: PurePath) -> str:
        # This is useful for portability between steps in Nextflow
        if getattr(self, "_serialize_paths_relative_to", None):
            path_str = os.path.relpath(path, self._serialize_paths_relative_to)
        else:
            path_str = str(path)
        return path_str

    def serialize_value(self, value: Any) -> Any:
        """Ensure that all values are JSON-serializable.

        Args:
            value: Any value.

        Returns:
            An equivalent JSON-serializable value.
        """
        result: Any
        if isinstance(value, (str, bytes)):
            result = value
        elif isinstance(value, PurePath):
            result = self.serialize_path(value)
        elif isinstance(value, SerializableMixin):
            result = value.to_dict()
        elif is_dataclass(value):
            result = asdict(value)
        elif isinstance(value, Mapping):
            result = {key: self.serialize_value(val) for key, val in value.items()}
        elif isinstance(value, Iterable):
            result = [self.serialize_value(item) for item in value]
        else:
            result = value
        return result

    def dict_factory(self, iterable: list[tuple[str, Any]]) -> dict[str, Any]:
        """Generate dictionary from dataclass.

        Unlike the built-in version, this function will
        handle Path objects. This assumes that the OS
        will not change between the serialization and
        deserialization steps.

        Args:
            iterable: List of attribute name-value pairs.

        Returns:
            Dictionary of JSON-serializable attributes.
        """
        kwargs = {}
        for key, value in iterable:
            kwargs[key] = self.serialize_value(value)
        return dict(**kwargs)

    def to_dict(self) -> SerializedObject:
        """Serialize the file to a dictionary.

        Inspired by dataclasses.asdict().

        Returns:
            A file serialized as a dictionary.
        """
        result = []
        for f in fields(self):
            value = self.serialize_value(getattr(self, f.name))
            result.append((f.name, value))
        return self.dict_factory(result)

    @classmethod
    @abstractmethod
    def from_dict(cls, dictionary: SerializedObject) -> SerializableMixin:
        """Deserialize a dictionary into a SerializableMixin object.

        Args:
            dictionary: A serialized object.

        Returns:
            The reconstructed object.
        """

    def copy(self: T) -> T:
        """Create a copy of a serializable object.

        Returns:
            A copied object.
        """
        dictionary = self.to_dict()
        copy = self.from_dict(dictionary)
        # Required to prevent this mypy error:
        # Incompatible return value type (got "SerializableMixin", expected "T")
        copy = cast(T, copy)
        return copy
