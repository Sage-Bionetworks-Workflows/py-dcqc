from __future__ import annotations

from abc import ABC
from collections.abc import Collection
from itertools import chain
from typing import ClassVar, Optional, Type, Union

from dcqc.enums import TestStatus
from dcqc.file import FileType
from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.target import Target
from dcqc.tests.test_abc import TestABC


# TODO: Consider the Composite design pattern once
#       we have higher-level QC suites
class SuiteABC(SerializableMixin, ABC):
    """Abstract base class for QC test suites.

    Args:
        target (Target): Single- or multi-file target.
        required_tests (Optional[Collection[str]]):
            List of tests that must pass for the
            overall suite to pass. Defaults to None,
            which requires tier-1 and tier-2 tests.
        skipped_tests (Optional[Collection[str]]):
            List of tests that should not be
            evaluated. Defaults to None.
    """

    # Class attributes
    file_type: ClassVar[FileType]
    add_tests: ClassVar[tuple[Type[TestABC], ...]]
    del_tests: ClassVar[tuple[Type[TestABC], ...]]

    # Instance attributes
    type: str
    target: Target
    required_tests: set[str]
    skipped_tests: set[str]

    def __init__(
        self,
        target: Target,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ):
        self.type = self.__class__.__name__
        self.target = target

        test_classes = self.list_test_classes()
        test_names = set(test.__name__ for test in test_classes)

        required_tests = required_tests or self._default_required_tests()
        self.required_tests = set(required_tests).intersection(test_names)

        skipped_tests = skipped_tests or list()
        self.skipped_tests = set(skipped_tests).intersection(test_names)

        self.tests = self.init_test_classes()
        self._status = TestStatus.NONE

    @classmethod
    def list_test_classes(cls) -> tuple[Type[TestABC], ...]:
        """List all applicable test classes"""
        all_tests: set[Type[TestABC]]
        all_tests = set()

        superclasses = cls.__mro__
        for cls in reversed(superclasses):  # Start from the base class
            if hasattr(cls, "add_tests"):
                add_tests = set(cls.add_tests)  # type: ignore
                all_tests.update(add_tests)
            if hasattr(cls, "del_tests"):
                del_tests = set(cls.del_tests)  # type: ignore
                all_tests.difference_update(del_tests)

        return tuple(all_tests)

    @classmethod
    def _default_required_tests(cls) -> list[str]:
        test_classes = cls.list_test_classes()
        required_tests = filter(lambda test: test.tier <= 2, test_classes)
        required_test_names = [test.__name__ for test in required_tests]
        return required_test_names

    def init_test_classes(self) -> list[TestABC]:
        """Initialize applicable test classes with target."""
        test_classes = self.list_test_classes()
        tests = []
        for test_cls in test_classes:
            test_name = test_cls.__name__
            skip = test_name in self.skipped_tests
            test = test_cls(self.target, skip)
            tests.append(test)
        return tests

    @classmethod
    def list_subclasses(cls) -> tuple[Type[SuiteABC], ...]:
        """List all subclasses."""
        subclasses: set[Type[SuiteABC]]
        subclasses = set(cls.__subclasses__())

        subsubclasses_list = [subcls.list_subclasses() for subcls in subclasses]
        subsubclasses = chain(*subsubclasses_list)
        all_subclasses = subclasses.union(subsubclasses)
        return tuple(all_subclasses)

    @classmethod
    def get_subclass_by_name(cls, name: str) -> Type[SuiteABC]:
        """Retrieve a subclass by name."""
        subclasses = cls.list_subclasses()
        registry = {subcls.__name__: subcls for subcls in subclasses}
        if name not in registry:
            options = list(registry)
            message = f"Suite ({name}) not available ({options})."
            raise ValueError(message)
        return registry[name]

    @classmethod
    def get_subclass_by_file_type(
        cls, file_type: Union[str, FileType]
    ) -> Type[SuiteABC]:
        """Retrieve a subclass by file type."""
        if isinstance(file_type, str):
            try:
                file_type = FileType.get_file_type(file_type)
            except ValueError:
                file_type = FileType.get_file_type("*")
        name = file_type.name
        subclasses = cls.list_subclasses()
        registry = {subcls.file_type.name: subcls for subcls in subclasses}
        if name not in registry:
            # TODO: This might have to be changed if we introduce
            #       composite file types (e.g., BAM/BAI file pair)
            return registry["*"]
        return registry[name]

    def compute_tests(self) -> None:
        """Compute the status for each initialized test."""
        for test in self.tests:
            test.get_status()

    def compute_status(self) -> TestStatus:
        """Compute the overall suite status."""
        self.compute_tests()
        suite_status = TestStatus.NONE
        for test in self.tests:
            test_name = test.type
            if test_name not in self.required_tests:
                continue
            test_status = test.get_status()
            suite_status = test_status
            if suite_status == TestStatus.FAIL:
                break
        return suite_status

    def to_dict(self) -> SerializedObject:
        suite_status = self.compute_status()
        test_dicts = []
        for test in self.tests:
            test_dict = test.to_dict()
            test_dict.pop("target", None)  # Remove redundant `target` info
            test_dicts.append(test_dict)
        suite_dict = {
            "target": self.target.to_dict(),
            "suite_status": {
                "required_tests": list(self.required_tests),
                "skipped_tests": list(self.skipped_tests),
                "status": suite_status.value,
            },
            "tests": test_dicts,
        }
        return suite_dict
