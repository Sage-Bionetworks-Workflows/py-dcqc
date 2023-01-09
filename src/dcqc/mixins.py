from abc import ABC, abstractmethod
from typing import Union

SerializedObject = dict[str, Union[str, int]]


class SerializableMixin(ABC):
    @abstractmethod
    def to_dict(self) -> SerializedObject:
        """"""

    # TODO: Uncomment this once the functions are ready
    # @abstractmethod
    # def from_dict(self):
    #     """"""
