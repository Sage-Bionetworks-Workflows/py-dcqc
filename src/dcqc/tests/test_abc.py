from __future__ import annotations

import shlex
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Type

from dcqc.enums import TestStatus
from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.target import Target


# TODO: Look into the @typing.final decorator
class TestABC(SerializableMixin, ABC):
    # Class attributes
    tier: int
    is_external_test: bool
    is_external_test = False
    only_one_file_targets: bool
    only_one_file_targets = True

    # Instance attributes
    type: str
    target: Target

    def __init__(self, target: Target, skip: bool = False):
        self.type = self.__class__.__name__
        self.target = target
        self._status = TestStatus.SKIP if skip else TestStatus.NONE

        files = self.target.files
        if self.only_one_file_targets and len(files) > 1:
            message = f"Test ({self.type}) expected one file, not multiple ({files})."
            raise ValueError(message)

    def get_status(self) -> TestStatus:
        if self._status == TestStatus.NONE:
            self._status = self.compute_status()
        return self._status

    def _get_single_target_file(self) -> File:
        files = self.target.files
        return files[0]

    @classmethod
    def get_test(cls, test: str) -> Type[TestABC]:
        test_classes = TestABC.__subclasses__()
        registry = {test_class.__name__: test_class for test_class in test_classes}
        if test not in registry:
            test_names = list(registry)
            message = f"Test ({test}) not among available options ({test_names})."
            raise ValueError(message)
        return registry[test]

    @classmethod
    def list_tests(cls) -> list[Type[TestABC]]:
        test_classes = TestABC.__subclasses__()
        return test_classes

    @abstractmethod
    def compute_status(self) -> TestStatus:
        """"""

    def to_dict(self):
        test_dict = {
            "type": self.type,
            "status": self._status.value,
            "target": self.target.to_dict(),
            # "tier": self.tier,
            # "is_external_test": self.is_external_test,
        }
        return test_dict

    # @classmethod
    # def from_dict(cls, dictionary: dict):
    #     # TODO: Restore `_status` if available
    #     pass


@dataclass
class Process:
    container: str
    command_args: Sequence[str]
    cpus: int = 1
    memory: int = 2  # In GB

    def get_command(self):
        return shlex.join(self.command_args)


class ExternalTestMixin(TestABC):
    # Class attributes
    is_external_test = True

    # Class constants
    STDOUT_PATH = Path("std_out.txt")
    STDERR_PATH = Path("std_err.txt")
    EXITCODE_PATH = Path("exit_code.txt")

    def compute_status(self):
        outputs = self._find_process_outputs()
        return self._interpret_process_outputs(outputs)

    @abstractmethod
    def generate_process(self) -> Process:
        """"""

    @classmethod
    def _find_process_outputs(
        cls, search_dir: Optional[Path] = None
    ) -> dict[str, Path]:
        search_dir = search_dir or Path(".")
        outputs = {
            "std_out": search_dir / cls.STDOUT_PATH,
            "std_err": search_dir / cls.STDERR_PATH,
            "exit_code": search_dir / cls.EXITCODE_PATH,
        }

        for path in outputs.values():
            if not path.exists():
                message = f"Expected process output ({path}) does not exist."
                raise FileNotFoundError(message)
        return outputs

    def _interpret_process_outputs(self, outputs: dict[str, Path]) -> TestStatus:
        exit_code = outputs["exit_code"].read_text()
        exit_code = exit_code.strip()
        if exit_code == "0":
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
        return status

    # TODO: Include process in dict (add `to_dict()` to Process class)
    # def to_dict(self):
    #     dictionary = super(ExternalTestMixin, self).to_dict()
    #     process = self.generate_process()
    #     dictionary["process"] = process
    #     return dictionary
