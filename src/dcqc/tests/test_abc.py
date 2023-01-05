from abc import ABC, abstractmethod

from dcqc.enums import TestStatus
from dcqc.target import Target


class TestABC(ABC):
    def __init__(self, target: Target):
        self.target = target
        self._status = TestStatus.NONE

    def get_status(self) -> TestStatus:
        self._status = self.compute_status()
        return self._status

    @abstractmethod
    def compute_status(self) -> TestStatus:
        """"""
