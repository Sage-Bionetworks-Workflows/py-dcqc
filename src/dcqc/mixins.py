from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import PurePath
from typing import Any, TypeVar, cast

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

    @staticmethod
    def dict_factory(iterable: list[tuple[str, Any]]) -> dict[str, Any]:
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
        # Ensure that all values are JSON-serializable
        kwargs = {}
        for key, value in iterable:
            if isinstance(value, PurePath):
                kwargs[key] = str(value)
            else:
                kwargs[key] = value

        return dict(**kwargs)

    def to_dict(self) -> SerializedObject:
        """Serialize the file to a dictionary.

        Returns:
            A file serialized as a dictionary.
        """
        return asdict(self, dict_factory=self.dict_factory)

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
