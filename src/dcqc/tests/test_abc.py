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
from typing import ClassVar, Optional, Type

from dcqc.file import File
from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.target import Target


class TestStatus(Enum):
    NONE = "pending"
    FAIL = "failed"
    PASS = "passed"
    SKIP = "skipped"


# TODO: Look into the @typing.final decorator
class TestABC(SerializableMixin, ABC):
    """Abstract base class for QC tests.

    Args:
        target (Target): Single- or multi-file target.
        skip (bool, optional): Whether to skip this test,
            resulting in ``TestStatus.SKIP`` as status.
            Defaults to False.

    Raises:
        ValueError: If the test expects a single file and
            the given target features multiple files.
    """

    # Class attributes
    tier: ClassVar[int]
    is_external_test: ClassVar[bool]
    is_external_test = False
    only_one_file_targets: ClassVar[bool]
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

    def skip(self):
        """Force the test to be skipped."""
        self._status = TestStatus.SKIP

    def get_status(self, compute_ok: bool = True) -> TestStatus:
        """Compute (if applicable) and return the test status."""
        if self._status == TestStatus.NONE and compute_ok:
            self._status = self.compute_status()
        return self._status

    def get_files(self, staged: bool = True) -> list[File]:
        """Get and stage files for target.

        Args:
            staged: Whether to make sure that the files are staged.
            Defaults to True.

        Returns:
            Staged target files.
        """
        files = []
        for file in self.target.files:
            if staged:
                file.stage()
            files.append(file)
        return files

    def get_file(self, staged: bool = True) -> File:
        """Get and stage file for single-file target.

        Args:
            staged: Whether to make sure that the files are staged.
            Defaults to True.

        Raises:
            ValueError: If the target has multiple files.

        Returns:
            Staged target file.
        """
        files = self.get_files(staged)
        if len(files) != 1:
            message = "This method only supports single-file targets."
            raise ValueError(message)
        return files[0]

    @classmethod
    def get_subclass_by_name(cls, test: str) -> Type[TestABC]:
        """Retrieve subclass by name."""
        test_classes = TestABC.__subclasses__()
        registry = {test_class.__name__: test_class for test_class in test_classes}
        if test not in registry:
            test_names = list(registry)
            message = f"Test ({test}) not among available options ({test_names})."
            raise ValueError(message)
        return registry[test]

    @classmethod
    def list_subclasses(cls) -> list[Type[TestABC]]:
        """List all subclasses."""
        test_classes = TestABC.__subclasses__()
        return test_classes

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
    def from_dict(cls, dictionary: SerializedObject) -> TestABC:
        """Deserialize a dictionary into a test.

        Args:
            dictionary: A serialized test object.

        Returns:
            The reconstructed test object.
        """
        test_cls_name = dictionary.pop("type")
        test_cls = cls.get_subclass_by_name(test_cls_name)

        target_dict = dictionary["target"]
        target = Target.from_dict(target_dict)

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
        return shlex.join(self._command_args)

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


class ExternalTestMixin(TestABC):
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
        if exit_code == "0":
            status = TestStatus.PASS
        else:
            status = TestStatus.FAIL
        return status

    # TODO: Include process in serialized test dictionary
    # def to_dict(self):
    #     dictionary = super(ExternalTestMixin, self).to_dict()
    #     process = self.generate_process()
    #     dictionary["process"] = process.to_dict()
    #     return dictionary
