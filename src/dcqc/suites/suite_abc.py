from __future__ import annotations

from abc import ABC
from collections.abc import Collection, Sequence
from copy import deepcopy
from itertools import chain
from typing import ClassVar, Optional, Type, Union

from dcqc.file import FileType
from dcqc.mixins import SerializableMixin, SerializedObject
from dcqc.target import Target
from dcqc.tests.test_abc import TestABC, TestStatus


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
    def from_target(
        cls,
        target: Target,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> SuiteABC:
        """Generate a suite from a target.

        The suite is selected based on the target file type.

        Args:
            target: A QC target.
            required_tests: List of requires tests.
                Defaults to None, which requires tier-1
                and tier-2 tests.
            skipped_tests: List of skipped tests.
                Defaults to None.

        Returns:
            SuiteABC: An initialized test suite.
        """
        file_type = target.get_file_type()
        suite_cls = SuiteABC.get_subclass_by_file_type(file_type)
        suite = suite_cls(target, required_tests, skipped_tests)
        return suite

    @classmethod
    def from_tests(
        cls,
        tests: Sequence[TestABC],
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> SuiteABC:
        """Generate a suite from a set of tests.

        The tests must all have the same target.

        Args:
            tests: Set of tests with the same target.
            required_tests: List of requires tests.
                Defaults to None, which requires tier-1
                and tier-2 tests.
            skipped_tests: List of skipped tests.
                Defaults to None.

        Returns:
            SuiteABC: An initialized test suite.
        """
        targets = list()
        suite_tests = list()
        skipped_tests = skipped_tests or list()
        skipped_tests = set(skipped_tests)
        for test in tests:
            test_copy = test.copy()
            if test_copy.type in skipped_tests:
                test_copy.skip()
            targets.append(test_copy.target)
            suite_tests.append(test_copy)

        representative_target = targets[0]
        if not all(representative_target == target for target in targets):
            message = f"Not all tests refer to the same target ({targets})."
            raise ValueError(message)
        suite = cls.from_target(representative_target, required_tests, skipped_tests)
        suite.tests = suite_tests

        return suite

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
    def list_test_classes_by_file_type(cls) -> dict[str, list[Type[TestABC]]]:
        """List test classes by file type."""
        result = dict()
        suite_classes = cls.list_subclasses()
        for suite_cls in suite_classes:
            file_type = suite_cls.file_type.name
            test_classes = suite_cls.list_test_classes()
            result[file_type] = list(test_classes)
        return result

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
        subclasses: list[Type[SuiteABC]]
        subclasses = cls.__subclasses__()

        subsubclasses_list = [subcls.list_subclasses() for subcls in subclasses]
        subclasses_chain = chain(subclasses, *subsubclasses_list)
        all_subclasses = tuple(dict.fromkeys(subclasses_chain))
        return all_subclasses

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
        self.target.stage()
        for test in self.tests:
            test.get_status()

    def compute_status(self) -> TestStatus:
        """Compute the overall suite status."""
        self.compute_tests()
        if self._status is not TestStatus.NONE:
            return self._status
        for test in self.tests:
            test_name = test.type
            if test_name not in self.required_tests:
                continue
            test_status = test.get_status()
            self._status = test_status
            if self._status == TestStatus.FAIL:
                break
        return self._status

    def to_dict(self) -> SerializedObject:
        suite_status = self.compute_status()
        test_dicts = []
        for test in self.tests:
            test_dict = test.to_dict()
            test_dict.pop("target", None)  # Remove redundant `target` info
            test_dicts.append(test_dict)
        suite_dict = {
            "type": self.type,
            "target": self.target.to_dict(),
            "suite_status": {
                "required_tests": list(self.required_tests),
                "skipped_tests": list(self.skipped_tests),
                "status": suite_status.value,
            },
            "tests": test_dicts,
        }
        return suite_dict

    @classmethod
    def from_dict(cls, dictionary: SerializedObject) -> SuiteABC:
        """Deserialize a dictionary into a suite.

        Args:
            dictionary: A serialized suite object.

        Returns:
            The reconstructed suite object.
        """
        dictionary = deepcopy(dictionary)

        suite_cls_name = dictionary["type"]
        suite_cls = SuiteABC.get_subclass_by_name(suite_cls_name)

        target_dict = dictionary["target"]
        target = Target.from_dict(target_dict)

        required_tests = dictionary["suite_status"]["required_tests"]
        skipped_tests = dictionary["suite_status"]["skipped_tests"]
        suite = suite_cls(target, required_tests, skipped_tests)

        suite_status = TestStatus(dictionary["suite_status"]["status"])
        suite._status = suite_status

        tests = list()
        for test_dict in dictionary["tests"]:
            test_dict["target"] = target_dict
            test = TestABC.from_dict(test_dict)
            tests.append(test)
        suite.tests = tests

        return suite
