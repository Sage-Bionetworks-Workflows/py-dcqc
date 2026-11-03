from __future__ import annotations

from abc import ABC
from collections.abc import Collection, Sequence
from copy import deepcopy
from enum import Enum
from typing import (
    Any,
    ClassVar,
    Optional,
    Type,
    Union,
)

from dcqc.file import FileType
from dcqc.mixins import SerializableMixin, SerializedObject, SubclassRegistryMixin
from dcqc.target import BaseTarget, SingleTarget
from dcqc.tests import BaseTest, TestStatus


class SuiteStatus(Enum):
    """Status of a suite."""

    NONE = "NONE"  # status not yet evaluated
    GREEN = "GREEN"  # all tests passed
    RED = "RED"  # one or more required tests failed
    AMBER = "AMBER"  # all required tests passed, but one or more optional tests failed
    GREY = "GREY"  # error occurred


# TODO: Consider the Composite design pattern once
#       we have higher-level QC suites
class SuiteABC(SerializableMixin, SubclassRegistryMixin, ABC):
    """Abstract base class for QC test suites.

    Args:
        target: Single- or multi-file target.
        required_tests: List of tests that must pass for the
            overall suite to pass. Defaults to None,
            which requires tier-1 and tier-2 tests.
        skipped_tests: List of tests that should not be
            evaluated. Defaults to None.

    A suite gives the target class that it accepts in the target_cls class
    attribute, for example target_cls = PairedTarget in FastqSuite. A suite
    that does not set target_cls inherits it from its parent, and SuiteABC
    sets a default of SingleTarget.
    """

    # Class attributes
    file_type: ClassVar[FileType]
    target_cls: ClassVar[type[BaseTarget]] = SingleTarget
    add_tests: ClassVar[tuple[Type[BaseTest], ...]]
    del_tests: ClassVar[tuple[Type[BaseTest], ...]]

    # Instance attributes
    type: str
    target: BaseTarget
    required_tests: set[str]
    skipped_tests: set[str]

    def __init__(
        self,
        target: BaseTarget,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ):
        self.type = self.__class__.__name__
        self.target = target

        test_classes = self.list_test_classes()
        test_names = set(test.__name__ for test in test_classes)

        # To differentiate between None and []
        if required_tests is None:
            required_tests = self._default_required_tests()
        self.required_tests = set(required_tests).intersection(test_names)

        skipped_tests = skipped_tests or list()
        self.skipped_tests = set(skipped_tests).intersection(test_names)

        self.tests = self.init_test_classes()
        self._status = SuiteStatus.NONE

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Set up and check each new suite class when it is defined.

        Python calls this hook one time for each subclass, when the class
        statement runs (at import time). The hook does these steps:

        1. Make sure that target_cls is a BaseTarget subclass. A suite that
           does not set target_cls inherits it from its parent (default
           SingleTarget).
        2. Make sure that every test of the suite, inherited tests included,
           accepts target_cls (see ensure_tests_match_target_cls). Thus a
           bad suite fails at import time, not during a QC run.
        3. If step 1 or 2 fails, mark the class as failed before the error is
           raised again. Python adds the class to __subclasses__() before
           this hook runs, so the class stays there after the error. The mark
           makes list_subclasses leave the class out, so that
           get_subclass_by_file_type cannot return a broken suite in place
           of a real one.

        Args:
            **kwargs: Keyword arguments from the class statement. They go
                to the parent hook.

        Raises:
            TypeError: If target_cls is not a BaseTarget subclass, or if a
                test does not accept the suite target class.
        """
        super().__init_subclass__(**kwargs)
        try:
            cls.ensure_target_cls_is_a_target_class()
            cls.ensure_tests_match_target_cls()
        except TypeError:
            cls.mark_registration_failed()
            raise

    @classmethod
    def ensure_target_cls_is_a_target_class(cls) -> None:
        """Ensure that the target_cls attribute is a BaseTarget subclass.

        Raises:
            TypeError: If target_cls is not a BaseTarget subclass, for
                example a Union or an instance.
        """
        target_cls = cls.target_cls
        if not (isinstance(target_cls, type) and issubclass(target_cls, BaseTarget)):
            message = (
                f"{cls.__name__} must set target_cls to a BaseTarget subclass, "
                f"not {target_cls!r}."
            )
            raise TypeError(message)

    @classmethod
    def ensure_tests_match_target_cls(cls) -> None:
        """Ensure that every test accepts the suite target class.

        A test accepts the suite target class if the target class
        is the same as, or a subclass of, the target_cls attribute
        of the test. A test that does not set target_cls inherits
        BaseTarget from BaseTest, and thus accepts any target.

        Raises:
            TypeError: If a test does not accept the suite target class.
        """
        for test_cls in cls.list_test_classes():
            test_target_cls = test_cls.target_cls
            if not issubclass(cls.target_cls, test_target_cls):
                message = (
                    f"{cls.__name__} uses target class {cls.target_cls.__name__}, "
                    f"but {test_cls.__name__} requires {test_target_cls.__name__}."
                )
                raise TypeError(message)

    @classmethod
    def from_target(
        cls,
        target: BaseTarget,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> SuiteABC:
        """Generate a suite from a target.

        The suite is selected based on the target file type.

        Args:
            target: A QC target.
            required_tests: List of required tests.
                Defaults to None, which requires tier-1
                and tier-2 tests.
            skipped_tests: List of skipped tests.
                Defaults to None.

        Returns:
            SuiteABC: An initialized test suite.
        """
        file_type = target.get_file_type()
        suite_cls = SuiteABC.get_subclass_by_file_type(file_type)
        urls = [file.url for file in target.files]
        suite_cls.ensure_accepts_target_cls(type(target), file_type, urls)
        suite = suite_cls(target, required_tests, skipped_tests)
        return suite

    @classmethod
    def from_tests(
        cls,
        tests: Sequence[BaseTest],
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> SuiteABC:
        """Generate a suite from a set of tests.

        The tests must all have the same target.

        Args:
            tests: Set of tests with the same target.
            required_tests: List of required tests.
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
    def list_test_classes(cls) -> tuple[Type[BaseTest], ...]:
        """List all applicable test classes, sorted by class name"""
        all_tests: set[Type[BaseTest]]
        all_tests = set()

        superclasses = cls.__mro__
        for cls in reversed(superclasses):  # Start from the base class
            if hasattr(cls, "add_tests"):
                add_tests = set(cls.add_tests)  # type: ignore
                all_tests.update(add_tests)
            if hasattr(cls, "del_tests"):
                del_tests = set(cls.del_tests)  # type: ignore
                all_tests.difference_update(del_tests)

        return tuple(sorted(all_tests, key=lambda test_cls: test_cls.__name__))

    @classmethod
    def list_test_classes_by_file_type(cls) -> dict[str, list[Type[BaseTest]]]:
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
        required_tests = filter(lambda test: test.tier.value <= 2, test_classes)
        required_test_names = [test.__name__ for test in required_tests]
        return required_test_names

    def init_test_classes(self) -> list[BaseTest]:
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

    @classmethod
    def ensure_accepts_target_cls(
        cls,
        target_cls: Type[BaseTarget],
        file_type: FileType,
        urls: Sequence[str],
    ) -> None:
        """Make sure that this suite class accepts a target class.

        Each suite class sets the target class that it accepts in its
        target_cls attribute. For example, FastqSuite accepts only a
        PairedTarget, and TiffSuite accepts only a SingleTarget. This method
        makes sure that target_cls is that class or a subclass of it.

        The method uses classes and URLs, not a target instance. Thus
        CsvParser can do the check before it stages the files, so a bad
        manifest fails before any download. SuiteABC.from_target also calls
        this method, on every target.

        Args:
            target_cls: The class of the target to check, for example
                SingleTarget or PairedTarget.
            file_type: The file type of the target. It is used only in the
                error message. It can be different from the file_type of
                the suite, because FileSuite is used for each file type
                that no suite claims.
            urls: The URLs of the files in the target. They are used only
                in the error message.

        Raises:
            ValueError: If this suite class does not accept target_cls. The
                message gives the URLs, the two target classes and the
                suite class. It does not tell about the 'dcqc_grouping'
                column, because some callers have no CSV manifest, for
                example qc-file. CsvParser adds that hint.
        """
        if not issubclass(target_cls, cls.target_cls):
            message = (
                f"Target ({', '.join(urls)}) is a {target_cls.__name__}, but "
                f"{cls.__name__} for file type '{file_type.name}' requires "
                f"a {cls.target_cls.__name__}."
            )
            raise ValueError(message)

    @property
    def tests_by_name(self) -> dict[str, BaseTest]:
        return {test.type: test for test in self.tests}

    def compute_tests(self) -> None:
        """Compute the status for each initialized test."""
        self.target.stage()
        for test in self.tests:
            test.get_status()

    def compute_status(self) -> SuiteStatus:
        """Compute the overall suite status."""
        self.compute_tests()
        if self._status != SuiteStatus.NONE:
            return self._status
        self._status = SuiteStatus.GREEN
        for test in self.tests:
            test_name = test.type
            test_status = test.get_status()
            # if test errors, always return grey immediately
            if test_status == TestStatus.ERROR:
                self._status = SuiteStatus.GREY
                return self._status
            # if required test failed, red takes precedence over amber
            if test_status == TestStatus.FAIL and test_name in self.required_tests:
                self._status = SuiteStatus.RED
            # if test failed not required test, amber
            if test_status == TestStatus.FAIL and self._status != SuiteStatus.RED:
                self._status = SuiteStatus.AMBER
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
        target = BaseTarget.from_dict(target_dict)

        required_tests = dictionary["suite_status"]["required_tests"]
        skipped_tests = dictionary["suite_status"]["skipped_tests"]
        suite = suite_cls(target, required_tests, skipped_tests)

        suite_status = SuiteStatus(dictionary["suite_status"]["status"])
        suite._status = suite_status

        tests = list()
        for test_dict in dictionary["tests"]:
            test_dict["target"] = target_dict
            test = BaseTest.from_dict(test_dict)
            tests.append(test)
        suite.tests = tests

        return suite

    @classmethod
    def get_base_class(cls):
        """Retrieve base class."""
        return SuiteABC

    def get_status(self) -> SuiteStatus:
        """Compute (if applicable) and return the suite status."""
        if self._status == SuiteStatus.NONE:
            self._status = self.compute_status()
        return self._status
