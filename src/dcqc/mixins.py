from abc import ABC, abstractmethod
from typing import Any

SerializedObject = dict[str, Any]


class SerializableMixin(ABC):
    @classmethod
    def from_dict_prepare(cls, dictionary: SerializedObject) -> SerializedObject:
        """Validate and prepare dictionary for deserialization."""
        type_ = dictionary.pop("type")
        if type_ != cls.__name__:
            message = f"Type ({type_}) does not match the class ({cls.__name__})."
            raise ValueError(message)
        return dictionary

    @abstractmethod
    def to_dict(self) -> SerializedObject:
        """"""

    # TODO: Uncomment this once the functions are ready
    # @abstractmethod
    # def from_dict(self):
    #     """"""
