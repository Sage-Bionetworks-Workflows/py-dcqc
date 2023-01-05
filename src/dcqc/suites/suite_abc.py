from abc import ABC
from typing import Type

from dcqc.tests.test_abc import TestABC


# TODO: Consider the Composite design pattern once
#       we have higher-level QC suites
class SuiteABC(ABC):
    add_tests: tuple[Type[TestABC], ...]
    del_tests: tuple[Type[TestABC], ...]

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
