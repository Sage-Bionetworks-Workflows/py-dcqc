import csv
import json
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import Any, Optional, Type, TypeVar, cast

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import BaseTarget, SingleTarget
from dcqc.tests.base_test import BaseTest

# For context on TypeVar, check out this GitHub PR comment:
# https://github.com/Sage-Bionetworks-Workflows/py-dcqc/pull/8#discussion_r1087141497
T = TypeVar("T", bound=SerializableMixin)


# TODO: Add support for URLs instead of paths
# TODO: Add support for a `unique_id` column
class CsvParser:
    """Parses a CSV manifest into the DCQC object model.

    The manifest must have a url column. Every other column becomes file
    metadata. Only two metadata keys are read by code, file_type and
    md5_checksum.

    A local relative URL is interpreted relative to the directory that holds
    the manifest, not relative to the current work directory. Remote URLs and
    absolute paths are not changed. See File._relativize_url for the rewrite.
    Note that list_rows does not apply this rewrite, but create_files does.

    Attributes:
        path: Location of the CSV manifest.
        stage_files: Whether to download each remote file to a directory
            next to the manifest.
    """

    path: Path
    stage_files: bool

    def __init__(self, path: Path, stage_files: bool = False):
        """Initialize a CSV manifest parser.

        Args:
            path: Location of the CSV manifest.
            stage_files: Whether to download each remote file to a directory
                next to the manifest. Defaults to False.
        """
        self.path = path
        self.stage_files = stage_files

    def list_rows(self) -> Iterator[tuple[int, dict]]:
        """Iterate over the rows of the CSV manifest.

        The URLs are given as they are written in the manifest. Use
        list_rows_and_files to get the URLs that are relative to the manifest
        directory as well.

        Yields:
            Pairs of a row number, which starts at 1, and the row as a
            dictionary that maps each column name to its value.
        """
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                yield index, row

    def _row_to_file(self, row: dict[str, str]) -> File:
        """Convert one manifest row into a File.

        The url column is removed from the row, and the columns that remain
        become the file metadata.

        Args:
            row: One manifest row, which maps each column name to its value.
                This dictionary is changed in place.

        Returns:
            The file. Its URL is relative to the manifest directory.
        """
        url = row.pop("url")
        file = File(url, row, relative_to=self.path.parent)
        return file

    def list_rows_and_files(self) -> Iterator[tuple[int, dict, File]]:
        """Iterate over the rows of the manifest with their File objects.

        This is the one place that pairs a manifest row with its file, so
        that every caller agrees on the URL of a row. The row is given
        unchanged, with its url column, while the URL of the file is
        relative to the manifest directory.

        No file is staged here. Use create_files for that.

        Yields:
            Triples of a row number, which starts at 1, the row as a
            dictionary that maps each column name to its value, and the file.
        """
        for index, row in self.list_rows():
            yield index, row, self._row_to_file(dict(row))

    def create_files(self) -> Iterator[tuple[int, File]]:
        """Create a File object for each row of the manifest.

        Each File is only a descriptor, which holds the URL and the metadata.
        No data is read or copied, unless the file is staged.

        A file is staged only if stage_files is True and the file is remote.
        It is then downloaded into a staged_files/index_<number> directory
        next to the manifest, and an existing copy is overwritten.

        Yields:
            Pairs of a row number, which starts at 1, and the file.
        """
        for index, _, file in self.list_rows_and_files():
            if not file.is_file_local() and self.stage_files:
                destination = self.path.parent / "staged_files" / f"index_{index}"
                destination.mkdir(parents=True, exist_ok=True)
                file.stage(destination, overwrite=True)
            yield index, file

    def create_targets(self) -> Iterator[SingleTarget]:
        """Create a single-file target for each row of the manifest.

        Yields:
            The targets. Each identifier is the row number with four digits,
            such as 0001.
        """
        for index, file in self.create_files():
            yield SingleTarget(file, id=f"{index:04}")

    def create_suites(
        self,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> Iterator[SuiteABC]:
        """Create a test suite for each row of the manifest.

        The suite class is selected from the file type of the target.

        Args:
            required_tests: Names of the tests that must pass. If None, the
                default set for the suite is used. An unknown name is
                ignored.
            skipped_tests: Names of the tests that are not run. If None, no
                test is skipped. An unknown name is ignored.

        Yields:
            The suites, one for each row.
        """
        for target in self.create_targets():
            yield SuiteABC.from_target(target, required_tests, skipped_tests)


class JsonParser:
    path: Path

    def __init__(self, path: Path):
        self.path = path

    def load_json(self) -> Any:
        with self.path.open("r") as infile:
            contents = json.load(infile)
        return contents

    def check_expected_cls(self, instance: Any, expected_cls: Type[T]) -> T:
        if not isinstance(instance, expected_cls):
            cls_name = expected_cls.__name__
            message = f"JSON file ({self.path!s}) is not expected type ({cls_name})."
            raise ValueError(message)
        instance = cast(T, instance)
        return instance

    @classmethod
    def get_class(cls, cls_name: str) -> Type[SerializableMixin]:
        test_classes = BaseTest.list_subclasses()
        test_cls_map = {cls.__name__: cls for cls in test_classes}

        suite_classes = SuiteABC.list_subclasses()
        suite_cls_map = {cls.__name__: cls for cls in suite_classes}

        target_classes = BaseTarget.list_subclasses()
        target_cls_map = {cls.__name__: cls for cls in target_classes}

        file_types = FileType.list_file_types()
        file_types_names = {ft.name.lower() for ft in file_types}

        if cls_name in target_cls_map:
            return target_cls_map[cls_name]
        elif cls_name in test_cls_map:
            return test_cls_map[cls_name]
        elif cls_name in suite_cls_map:
            return suite_cls_map[cls_name]
        elif cls_name.lower() in file_types_names:
            return File
        else:
            message = f"Type ({cls_name}) is not recognized."
            raise ValueError(message)

    @classmethod
    def from_dict(cls, dictionary) -> SerializableMixin:
        if "type" not in dictionary:
            message = f"Cannot parse JSON object due to missing type ({dictionary})."
            raise ValueError(message)
        type_name = dictionary["type"]
        type_class = cls.get_class(type_name)
        object_ = type_class.from_dict(dictionary)
        return object_

    @classmethod
    def parse_object(cls, path: Path, expected_cls: Type[T]) -> T:
        parser = cls(path)
        contents = parser.load_json()

        if isinstance(contents, list):
            message = f"JSON file ({parser.path}) contains a list of objects."
            raise ValueError(message)

        object_ = cls.from_dict(contents)
        expected = parser.check_expected_cls(object_, expected_cls)
        return expected

    @classmethod
    def parse_objects(cls, path: Path, expected_cls: Type[T]) -> list[T]:
        parser = cls(path)
        contents = parser.load_json()

        if not isinstance(contents, list):
            message = f"JSON file ({parser.path}) does not contain a list of objects."
            raise ValueError(message)

        objects = [cls.from_dict(dictionary) for dictionary in contents]
        expected = [parser.check_expected_cls(obj, expected_cls) for obj in objects]
        return expected
