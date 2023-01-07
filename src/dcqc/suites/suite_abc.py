from __future__ import annotations

from abc import ABC
from collections.abc import Collection
from itertools import chain
from typing import Optional, Type
from warnings import warn

from dcqc.enums import TestStatus
from dcqc.file import FileType
from dcqc.target import Target
from dcqc.tests.test_abc import TestABC


# TODO: Consider the Composite design pattern once
#       we have higher-level QC suites
class SuiteABC(ABC):
    # Class attributes
    file_type: FileType
    add_tests: tuple[Type[TestABC], ...]
    del_tests: tuple[Type[TestABC], ...]

    # Instance attributes
    type: str
    target: Target
    required_tests: Collection[str]

    def __init__(
        self,
        target: Target,
        required_tests: Optional[Collection[str]] = None,
    ):
        self.type = self.__class__.__name__
        self.target = target
        self.required_tests = required_tests or self._default_required_tests()
        self.tests = self.init_test_classes()
        self._status = TestStatus.NONE

    @classmethod
    def list_test_classes(cls):
        superclasses = cls.__mro__
        superclasses = reversed(superclasses)
        all_tests = []
        for cls in superclasses:
            if hasattr(cls, "add_tests"):
                add_tests = set(cls.add_tests)  # type: ignore
                all_tests.extend(add_tests)
            if hasattr(cls, "del_tests"):
                del_tests = set(cls.del_tests)  # type: ignore
                all_tests = [test for test in all_tests if test not in del_tests]
        return all_tests

    @classmethod
    def _default_required_tests(cls):
        test_classes = cls.list_test_classes()
        required_tests = filter(lambda test: test.tier <= 2, test_classes)
        required_test_names = [test.__name__ for test in required_tests]
        return required_test_names

    def init_test_classes(self):
        test_classes = self.list_test_classes()
        tests = [test_cls(self.target) for test_cls in test_classes]
        return tests

    @classmethod
    def _list_subclasses(cls) -> set[Type[SuiteABC]]:
        subclasses = set(cls.__subclasses__())
        subsubclasses_list = [subcls._list_subclasses() for subcls in subclasses]
        subsubclasses = chain(*subsubclasses_list)
        return subclasses.union(subsubclasses)

    @classmethod
    def get_suite_by_name(cls, name: str) -> Type[SuiteABC]:
        subclasses = cls._list_subclasses()
        registry = {subcls.type: subcls for subcls in subclasses}
        if name not in registry:
            options = list(registry)
            message = f"Suite ({name}) not available ({options})."
            raise ValueError(message)
        return registry[name]

    @classmethod
    def get_suite_by_file_type(cls, file_type: FileType) -> Type[SuiteABC]:
        name = file_type.name
        subclasses = cls._list_subclasses()
        registry = {subcls.file_type.name: subcls for subcls in subclasses}
        if name not in registry:
            # TODO: This might have to be changed if we introduce
            #       composite file types (e.g., BAM/BAI file pair)
            return registry["*"]
        return registry[name]

    def compute_tests(self):
        for test in self.tests:
            test.get_status()

    def compute_status(self) -> TestStatus:
        suite_status = TestStatus.NONE
        for test in self.tests:
            test_name = test.type
            if test_name not in self.required_tests:
                continue
            test_status = test.get_status()
            if test_status == TestStatus.NONE:
                message = f"Suite ({self}) has a test ({test_name}) without a status."
                raise ValueError(message)
            elif test_status == TestStatus.SKIP:
                message = f"Suite ({self}) is ignoring a skipped test ({test_name})."
                warn(message)
            elif test_status == TestStatus.FAIL:
                suite_status = TestStatus.FAIL
                break
            elif test_status == TestStatus.PASS:
                suite_status = TestStatus.PASS
        return suite_status

    def to_dict(self):
        suite_status = self.compute_status()
        suite_dict = {
            "target": self.target.to_dict(),
            "suite_status": {
                "required_tests": self.required_tests,
                "status": suite_status.value,
            },
            "tests": [test.to_dict(with_target=False) for test in self.tests],
        }
        return suite_dict
