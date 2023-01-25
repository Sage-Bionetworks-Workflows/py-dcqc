import csv
import json
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import Any, Optional, Type, TypeVar

from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import Target
from dcqc.tests.test_abc import TestABC

T = TypeVar("T", bound=SerializableMixin)


# TODO: Add support for URLs instead of paths
# TODO: Add support for a `unique_id` column
class CsvParser:
    path: Path

    def __init__(self, path: Path, stage_files: bool = False):
        self.path = path
        self.stage_files = stage_files

    def list_rows(self) -> Iterator[tuple[int, dict]]:
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                yield index, row

    def _row_to_file(self, row: dict[str, str]) -> File:
        url = row.pop("url")
        file = File(url, row, relative_to=self.path.parent)
        return file

    def create_files(self) -> Iterator[File]:
        for index, row in self.list_rows():
            file = self._row_to_file(row)
            if not file.is_file_local() and self.stage_files:
                destination = self.path.parent / "staged_files" / f"index_{index}"
                destination.mkdir(parents=True, exist_ok=True)
                file.stage(destination, overwrite=True)
            yield file

    def create_targets(self, stage_files: bool = True) -> Iterator[Target]:
        for file in self.create_files():
            if stage_files:
                file.stage()
            yield Target(file)

    def create_suites(
        self,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
        stage_files: bool = True,
    ) -> Iterator[SuiteABC]:
        for target in self.create_targets(stage_files):
            yield SuiteABC.from_target(target, required_tests, skipped_tests)


class JsonParser:
    path: Path

    def __init__(self, path: Path):
        self.path = path

    @classmethod
    def parse_expected(cls, path: Path, expected_cls: Type[T]) -> T:
        """Generate expected object from JSON file.

        Args:
            json_path: JSON file describine the expected object.

        Raises:
            ValueError: If the JSON file does not
                describe a expected object.

        Returns:
            The reconstructed object.
        """
        parser = JsonParser(path)
        object_ = parser.parse_object()

        if not isinstance(object_, expected_cls):
            message = f"Parsed JSON file ({path!s}) does not describe a {expected_cls}."
            raise ValueError(message)

        return object_

    def load_json(self) -> Any:
        with self.path.open("r") as infile:
            contents = json.load(infile)
        return contents

    def get_class(self, cls_name: str) -> Type[SerializableMixin]:
        test_classes = TestABC.list_subclasses()
        test_cls_map = {cls.__name__: cls for cls in test_classes}

        suite_classes = SuiteABC.list_subclasses()
        suite_cls_map = {cls.__name__: cls for cls in suite_classes}

        if cls_name == "File":
            return File
        elif cls_name == "Target":
            return Target
        elif cls_name in test_cls_map:
            return test_cls_map[cls_name]
        elif cls_name in suite_cls_map:
            return suite_cls_map[cls_name]
        else:
            message = f"Type ({cls_name}) is not recognized."
            raise ValueError(message)

    def from_dict(self, dictionary) -> SerializableMixin:
        if "type" not in dictionary:
            message = f"Cannot parse JSON object due to missing type ({dictionary})."
            raise ValueError(message)
        cls_name = dictionary["type"]
        cls = self.get_class(cls_name)
        object_ = cls.from_dict(dictionary)
        return object_

    def parse_object(self) -> SerializableMixin:
        contents = self.load_json()
        if isinstance(contents, list):
            message = f"JSON file ({self.path}) contains a list of objects."
            raise ValueError(message)
        object_ = self.from_dict(contents)
        return object_

    def parse_objects(self) -> list[SerializableMixin]:
        contents = self.load_json()
        if not isinstance(contents, list):
            message = f"JSON file ({self.path}) does not contain a list of objects."
            raise ValueError(message)
        objects = [self.from_dict(object_) for object_ in contents]
        return objects
