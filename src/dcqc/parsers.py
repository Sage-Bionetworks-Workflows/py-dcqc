import csv
import json
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Type, TypeVar, cast

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import BaseTarget, PairedTarget, SingleTarget
from dcqc.tests.base_test import BaseTest

# For context on TypeVar, check out this GitHub PR comment:
# https://github.com/Sage-Bionetworks-Workflows/py-dcqc/pull/8#discussion_r1087141497
T = TypeVar("T", bound=SerializableMixin)


@dataclass
class _PlannedTarget:
    """A checked target of the manifest, before its files are staged.

    Attributes:
        target_cls: The class of the target, SingleTarget for a row with no
            grouping value, or PairedTarget for a group.
        members: Pairs of a row number, which starts at 1, and the file of
            each row of the target, in manifest order.
    """

    target_cls: type[BaseTarget]
    members: list[tuple[int, File]]


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
    Note that list_rows does not apply this rewrite, but list_rows_and_files
    does.

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

        No file is staged here. Use create_targets for that.

        Yields:
            Triples of a row number, which starts at 1, the row as a
            dictionary that maps each column name to its value, and the file.
        """
        for index, row in self.list_rows():
            yield index, row, self._row_to_file(dict(row))

    def _stage_file(self, index: int, file: File) -> None:
        """Stage one file, if stage_files is True and the file is remote.

        The file is downloaded into a staged_files/index_<number> directory
        next to the manifest, and an existing copy is overwritten.

        Args:
            index: The row number of the file, which starts at 1.
            file: The file to stage.
        """
        if not file.is_file_local() and self.stage_files:
            destination = self.path.parent / "staged_files" / f"index_{index}"
            destination.mkdir(parents=True, exist_ok=True)
            file.stage(destination, overwrite=True)

    def create_targets(self) -> Iterator[BaseTarget]:
        """Create the targets for the rows of the manifest.

        The optional dcqc_grouping column tells which rows go into one target.
        Spaces at the start and end of each value are removed. The values
        are case-sensitive, so A and a are two different groups. A row with
        an empty or missing value becomes one SingleTarget. All rows with
        the same value become one PairedTarget, in manifest order.
        The rows of a group do not have to be next to each other.

        The grouping value is removed from the file metadata, because it
        describes the target, not the file.

        Each row and group is checked before a file is staged or a target
        is yielded. Thus a bad row or group raises an error before any
        download, and the caller does not get part of the targets. See
        _plan_targets for the checks.

        Raises:
            ValueError: If a file has an unknown file type, if a group does
                not have exactly two files, if the files of a group have
                different file types, or if the suite for the file type
                does not accept the target class. For example, an ungrouped
                FASTQ row and a grouped TIFF row are errors.

        Yields:
            The targets. Each identifier is the lowest row number of the
            target with four digits, such as 0001. The single-file targets
            come first, and the grouped targets come after the last row.
        """
        yield from self._build_targets(self._plan_targets())

    def _plan_targets(self) -> list[_PlannedTarget]:
        """Sort the manifest rows into planned targets, and check each one.

        create_targets calls this first, so that all checks run before
        _build_targets stages a file. This method does not stage a file and
        does not build a target.

        For each row, the dcqc_grouping value is removed from the file
        metadata, and the spaces at its start and end are removed. A row
        with an empty or missing value is a single row, and it becomes a
        SingleTarget. All rows with the same value are one group, and each
        group becomes a PairedTarget. The rows of a group do not have to be
        next to each other in the manifest.

        A single row is bad if its file has an unknown file type. A group is
        bad if it does not have exactly two files, if a file has an unknown
        file type, or if the two files have different file types. A single
        row or a group is also bad if the suite for its file type does not
        accept its target class. All rows and groups are checked before an
        error is raised, so that one error tells about all of them. The bad
        single rows come first, in manifest order, and then the bad groups,
        in the order of their first row.

        Raises:
            ValueError: If a single row or a group is bad. The message has
                one line for each bad single row, with its row number, and
                one line for each bad group, with its grouping value and its
                row numbers.

        Returns:
            One planned target for each single row, in manifest order, and
            then one for each group, in the order of its first row. The
            members of a group are in manifest order.
        """
        # Rows without a grouping value, in manifest order.
        singles: list[tuple[int, File]] = []
        # Maps each grouping value to the pairs of a row number and the file
        # of each row in that group, in manifest order.
        groups: dict[str, list[tuple[int, File]]] = {}
        for index, _, file in self.list_rows_and_files():
            group = (file.metadata.pop("dcqc_grouping", None) or "").strip()
            if group:
                groups.setdefault(group, []).append((index, file))
            else:
                singles.append((index, file))

        plans: list[_PlannedTarget] = []
        # One message for each bad single row, in manifest order, and then
        # one message for each bad group, in the order of its first row.
        errors: list[str] = []
        for index, file in singles:
            try:
                file.get_file_type()
            except ValueError as error:
                errors.append(f"Row {index} has an unknown file type. {error}")
                continue
            plan = _PlannedTarget(SingleTarget, [(index, file)])
            error_message = self._check_plan(plan, f"Row {index}")
            if error_message:
                errors.append(error_message)
            else:
                plans.append(plan)
        for group, members in groups.items():
            indices = [index for index, _ in members]
            try:
                self._ensure_group_file_types_known(group, members)
            except ValueError as error:
                errors.append(str(error))
                continue
            plan = _PlannedTarget(PairedTarget, members)
            location = f"Group ({group}) in rows {indices}"
            error_message = self._check_plan(plan, location)
            if error_message:
                errors.append(error_message)
            else:
                plans.append(plan)
        if errors:
            raise ValueError("\n".join(errors))
        return plans

    @classmethod
    def _check_plan(cls, plan: _PlannedTarget, location: str) -> Optional[str]:
        """Check the files and the target class of a plan.

        The files are checked with the validate_files method of the target
        class, so the parser and the target use the same rule. Then the
        target class is checked against the suite for the file type.

        Every file of the plan must have a known file type.

        Args:
            plan: The planned target to check.
            location: The rows of the plan, for the start of the message,
                for example "Row 3" or "Group (a) in rows [2, 5]".

        Returns:
            None if the plan is good. If not, the error message, which
            starts with the location.
        """
        files = [file for _, file in plan.members]
        problems = plan.target_cls.validate_files(files)
        if problems:
            return f"{location} " + " ".join(problems)
        file_type = files[0].get_file_type()
        return cls._check_suite_accepts_plan(plan, file_type, location)

    @staticmethod
    def _check_suite_accepts_plan(
        plan: _PlannedTarget, file_type: FileType, location: str
    ) -> Optional[str]:
        """Check the target class of a plan against its suite.

        If the check fails, the message also tells the rows of the plan, and
        how to change the dcqc_grouping column.
        SuiteABC.ensure_accepts_target_cls does not give this hint, because
        some of its callers have no CSV manifest.

        Args:
            plan: The planned target to check.
            file_type: The file type of the files of the plan.
            location: The rows of the plan, for the start of the message,
                for example "Row 3" or "Group (a) in rows [2, 5]".

        Returns:
            None if the suite accepts the target class. If not, the error
            message, with the rows and the dcqc_grouping hint.
        """
        suite_cls = SuiteABC.get_subclass_by_file_type(file_type)
        urls = [file.url for _, file in plan.members]
        try:
            suite_cls.ensure_accepts_target_cls(plan.target_cls, file_type, urls)
        except ValueError as error:
            if issubclass(plan.target_cls, PairedTarget):
                hint = "Remove the 'dcqc_grouping' value from these files."
            else:
                hint = "Give the files the same 'dcqc_grouping' value."
            return f"{location}: {error} {hint}"
        return None

    def _ensure_group_file_types_known(
        self, group: str, members: list[tuple[int, File]]
    ) -> None:
        """Ensure that each file of one group has a known file type.

        Args:
            group: The grouping value of the rows.
            members: Pairs of a row number and the file, in manifest order.

        Raises:
            ValueError: If a file of the group has an unknown file type. The
                message gives the grouping value, the row numbers of the
                group and the row of the bad file.
        """
        indices = [index for index, _ in members]
        for index, file in members:
            try:
                file.get_file_type()
            except ValueError as error:
                message = (
                    f"Group ({group}) in rows {indices} has an unknown file type "
                    f"in row {index}. {error}"
                )
                raise ValueError(message) from error

    def _build_targets(self, plans: list[_PlannedTarget]) -> Iterator[BaseTarget]:
        """Stage the files of the checked plans, and build their targets.

        Args:
            plans: The planned targets from _plan_targets.

        Yields:
            The targets, as described in create_targets.
        """
        for plan in plans:
            for index, file in plan.members:
                self._stage_file(index, file)
            files = [file for _, file in plan.members]
            # The members are in manifest order, so the first row number is
            # the lowest.
            yield plan.target_cls(files, id=f"{plan.members[0][0]:04}")

    def create_suites(
        self,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> Iterator[SuiteABC]:
        """Create a test suite for each target of the manifest.

        The suite class is selected from the file type of the target. The
        targets come from create_targets, so each row and group is checked,
        also against its suite, before a file is staged. Thus a bad manifest
        raises an error before any download, and the caller does not get
        part of the suites. All suites are created before the first suite
        is yielded.

        Args:
            required_tests: Names of the tests that must pass. If None, the
                default set for the suite is used. An unknown name is
                ignored.
            skipped_tests: Names of the tests that are not run. If None, no
                test is skipped. An unknown name is ignored.

        Raises:
            ValueError: If a row or group is bad, as described in
                create_targets.

        Yields:
            The suites, one for each target.
        """
        targets = list(self.create_targets())
        suites = [
            SuiteABC.from_target(target, required_tests, skipped_tests)
            for target in targets
        ]
        yield from suites


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
        test_classes = BaseTest.list_concrete_subclasses()
        test_cls_map = {cls.__name__: cls for cls in test_classes}

        suite_classes = SuiteABC.list_concrete_subclasses()
        suite_cls_map = {cls.__name__: cls for cls in suite_classes}

        target_classes = BaseTarget.list_concrete_subclasses()
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
