from __future__ import annotations

import shlex
from abc import ABC, abstractmethod
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import InitVar, dataclass
from enum import Enum
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Generic, Optional, TypeVar

from dcqc.mixins import SerializableMixin, SerializedObject, SubclassRegistryMixin
from dcqc.target import BaseTarget

Target = TypeVar("Target", bound=BaseTarget)


class TestStatus(Enum):
    NONE = "pending"
    FAIL = "failed"
    PASS = "passed"
    SKIP = "skipped"


# TODO: Look into the @typing.final decorator
class BaseTest(SerializableMixin, SubclassRegistryMixin, ABC, Generic[Target]):
    """Abstract base class for QC tests.

    Args:
        target: Single- or multi-file target.
        skip: Whether to skip this test, resulting
            in ``TestStatus.SKIP`` as status.
            Defaults to False.

    Raises:
        ValueError: If the test expects a single file and
            the given target features multiple files.
    """

    # Class attributes
    tier: ClassVar[int]
    is_external_test: ClassVar[bool]
    is_external_test = False

    # Instance attributes
    type: str
    target: Target

    def __init__(self, target: Target, skip: bool = False):
        self.type = self.__class__.__name__
        self.target = target
        self._status = TestStatus.SKIP if skip else TestStatus.NONE

    def skip(self):
        """Force the test to be skipped."""
        self._status = TestStatus.SKIP

    def get_status(self, compute_ok: bool = True) -> TestStatus:
        """Compute (if applicable) and return the test status."""
        if self._status == TestStatus.NONE and compute_ok:
            self._status = self.compute_status()
        return self._status

    @abstractmethod
    def compute_status(self) -> TestStatus:
        """Compute the status of the test."""

    def to_dict(self) -> SerializedObject:
        test_dict = {
            "type": self.type,
            "tier": self.tier,
            "is_external_test": self.is_external_test,
            "status": self._status.value,
            "target": self.target.to_dict(),
        }
        return test_dict

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> BaseTest:
        """Deserialize a dictionary into a test.

        Args:
            dictionary: A serialized test object.

        Returns:
            The reconstructed test object.
        """
        test_cls_name = dictionary.pop("type")
        test_cls = BaseTest.get_subclass_by_name(test_cls_name)

        target_dict = dictionary["target"]
        target = BaseTarget.from_dict(target_dict)

        test = test_cls(target)

        status = TestStatus(dictionary["status"])
        test._status = status

        return test

    def import_module(self, name: str) -> ModuleType:
        try:
            module = import_module(name)
        except ModuleNotFoundError:
            message = (
                f"{self.type} cannot be computed without the '{name}' package. ",
                "Re-install `dcqc` with the `all` extra: pip install dcqc[all].",
            )
            raise ModuleNotFoundError(message)
        return module

    @classmethod
    def get_base_class(cls):
        """Retrieve base class."""
        return BaseTest


@dataclass
class Process(SerializableMixin):
    container: str
    command_args: InitVar[Sequence[str]]
    cpus: int = 1
    memory: int = 2  # In GB

    _serialized_properties = ["command"]

    def __post_init__(self, command_args: Sequence[str]):
        self._command_args = command_args

    @property
    def command(self) -> str:
        args_strings = [str(arg) for arg in self._command_args]
        return " ".join(args_strings)

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> Process:
        """Deserialize a dictionary into a process.

        Args:
            dictionary: A serialized proces object.

        Returns:
            The reconstructed process object.
        """
        dictionary = deepcopy(dictionary)
        command = dictionary.pop("command")
        command_args = shlex.split(command)
        dictionary["command_args"] = command_args
        process = cls(**dictionary)
        return process


class ExternalTestMixin(BaseTest):
    pass_code: ClassVar[str]
    # Class attributes
    is_external_test = True

    # Class constants
    STDOUT_PATH: ClassVar[Path]
    STDOUT_PATH = Path("std_out.txt")
    STDERR_PATH: ClassVar[Path]
    STDERR_PATH = Path("std_err.txt")
    EXITCODE_PATH: ClassVar[Path]
    EXITCODE_PATH = Path("exit_code.txt")

    def compute_status(self) -> TestStatus:
        """Compute the status of the test."""
        outputs = self._find_process_outputs()
        return self._interpret_process_outputs(outputs)

    @abstractmethod
    def generate_process(self) -> Process:
        """Generate the process that needs to be run."""

    @classmethod
    def _find_process_outputs(
        cls, search_dir: Optional[Path] = None
    ) -> dict[str, Path]:
        """Locate the output files from the executed process."""
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
        """Interpret the process output files to yield a test status."""
        exit_code = outputs["exit_code"].read_text()
        exit_code = exit_code.strip()
        if exit_code == self.pass_code:
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
        return status

    # TODO: make changes to this package or the nextflow
    # workflow so that file mounting is handled cleaner
    @staticmethod
    def _short_string_path(path: Path, substring: str) -> str:
        # chech if substring is in path
        if substring not in path.as_posix():
            raise ValueError(f"{substring} not in {path}")
        # get index where staged folder is
        index = next(i for i, item in enumerate(path.parts) if substring in item)
        # shorten path starting from staged folder
        short_path = Path(*path.parts[index:])
        # wrap path string in quotes
        quote_path = str(short_path)
        return f"'{quote_path}'"

    # TODO: Include process in serialized test dictionary
    # def to_dict(self):
    #     dictionary = super(ExternalTestMixin, self).to_dict()
    #     process = self.generate_process()
    #     dictionary["process"] = process.to_dict()
    #     return dictionary


class InternalBaseTest(BaseTest):
    """Base class for all internal tests."""


class ExternalBaseTest(ExternalTestMixin, BaseTest):
    """Base class for all external tests."""
