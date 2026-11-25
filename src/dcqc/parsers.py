import csv
import json
from collections.abc import Collection, Iterable, Iterator
from pathlib import Path
from typing import Any, NamedTuple, Optional, Type, TypeVar, cast

from dcqc.file import File, FileType
from dcqc.mixins import SerializableMixin
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import BaseTarget, PairedTarget, SingleTarget
from dcqc.tests.base_test import BaseTest

# For context on TypeVar, check out this GitHub PR comment:
# https://github.com/Sage-Bionetworks-Workflows/py-dcqc/pull/8#discussion_r1087141497
T = TypeVar("T", bound=SerializableMixin)


class ManifestRow(NamedTuple):
    """One row of a manifest, as input for build_targets.

    Attributes:
        number: The row number, which starts at 1.
        file: The file of the row.
        group: The dcqc_grouping value of the row, with the spaces at its
            start and end removed. An empty string means that the row is
            not in a group.
    """

    number: int
    file: File
    group: str = ""


class ManifestTarget(NamedTuple):
    """A target from build_targets, with the rows that it came from.

    Attributes:
        target: The target. Its files are not staged.
        rows: The rows of the target, in manifest order. The files of the
            rows are the same objects as the files of the target, in the
            same order. Thus staging the file of a row also stages the file
            of the target.
    """

    target: BaseTarget
    rows: list[ManifestRow]


def build_targets(rows: Iterable[ManifestRow]) -> list[ManifestTarget]:
    """Sort the rows of a manifest into targets, and check each one.

    This function is pure. It does not read a file, it does not stage a
    file, and it does not change the rows or their files. Thus a caller can
    check all rows before it stages a file.

    A row with an empty group value becomes one SingleTarget. All rows with
    the same group value become one PairedTarget, in manifest order. The
    values are case-sensitive, so A and a are two different groups. The rows
    of a group do not have to be next to each other.

    All rows and groups are checked before an error is raised, so that one
    error tells about all of them. The bad single rows come first, in
    manifest order, and then the bad groups, in the order of their first
    row.

    Args:
        rows: The rows of the manifest, in manifest order.

    Raises:
        ValueError: If a file has an unknown file type, if a group does not
            have exactly two files, if the files of a group have different
            file types, or if the suite of a group has no test that needs a
            PairedTarget. The message has one line for each bad single row,
            with its row number, and one line for each bad group, with its
            group value and its row numbers.

    Returns:
        One target for each single row, in manifest order, and then one for
        each group, in the order of its first row. Each identifier is the
        lowest row number of the target with four digits, such as 0001.
    """
    singles: list[ManifestRow] = []
    groups: dict[str, list[ManifestRow]] = {}
    for row in rows:
        if row.group:
            groups.setdefault(row.group, []).append(row)
        else:
            singles.append(row)

    targets: list[ManifestTarget] = []
    errors: list[str] = []
    for row in singles:
        error = _check_rows(SingleTarget, [row], f"Row {row.number}")
        if error:
            errors.append(error)
        else:
            targets.append(_make_target(SingleTarget, [row]))
    for group, members in groups.items():
        indices = [row.number for row in members]
        location = f"Group ({group}) in rows {indices}"
        error = _check_rows(PairedTarget, members, location)
        error = error or _check_suite_has_paired_test(members, location)
        if error:
            errors.append(error)
        else:
            targets.append(_make_target(PairedTarget, members))
    if errors:
        raise ValueError("\n".join(errors))
    return targets


def _make_target(
    target_cls: type[BaseTarget], rows: list[ManifestRow]
) -> ManifestTarget:
    """Make a target from rows that were checked with _check_rows.

    Args:
        target_cls: The class of the target.
        rows: The rows of the target, in manifest order.

    Returns:
        The target and its rows. The identifier is the first row number,
        which is the lowest, because the rows are in manifest order.
    """
    files = [row.file for row in rows]
    target = target_cls(files, id=f"{rows[0].number:04}")
    return ManifestTarget(target, list(rows))


def _check_rows(
    target_cls: type[BaseTarget], rows: list[ManifestRow], location: str
) -> Optional[str]:
    """Check the files of the rows for a target of a class.

    First, every file must have a known file type. Then the files are
    checked with the validate_files method of the target class, so that
    build_targets and the target use the same rule. The check stops at the
    first problem.

    Args:
        target_cls: The class of the target.
        rows: The rows of the target, in manifest order.
        location: The rows, for the start of the message, for example
            "Row 3" or "Group (a) in rows [2, 5]".

    Returns:
        None if the rows are good. If not, the error message, which starts
        with the location.
    """
    for row in rows:
        try:
            row.file.get_file_type()
        except ValueError as error:
            in_row = f" in row {row.number}" if len(rows) > 1 else ""
            return f"{location} has an unknown file type{in_row}. {error}"
    problems = target_cls.validate_files([row.file for row in rows])
    if problems:
        return f"{location} " + " ".join(problems)
    return None


def _check_suite_has_paired_test(
    rows: list[ManifestRow], location: str
) -> Optional[str]:
    """Check that the suite of a group has a test that needs a PairedTarget.

    The suite makes only the tests that accept the target (see
    SuiteABC.list_test_classes_for_target). Thus a group in a suite with no
    paired test would quietly lose the tests that need a SingleTarget, for
    example the TIFF tests. The rule comes from the target_cls attribute of
    each test, so the suite does not store it again.

    Call this function only after _check_rows, because it needs a known
    file type, and the files of the group must have the same file type.

    Args:
        rows: The rows of the group, in manifest order.
        location: The rows, for the start of the message, for example
            "Group (a) in rows [2, 5]".

    Returns:
        None if the suite has a test that needs a PairedTarget. If not, the
        error message, which starts with the location.
    """
    file_type = rows[0].file.get_file_type()
    suite_cls = SuiteABC.get_subclass_by_file_type(file_type)
    for test_cls in suite_cls.list_test_classes():
        if issubclass(test_cls.target_cls, PairedTarget):
            return None
    return (
        f"{location} has file type {file_type.name}, but its suite "
        f"({suite_cls.__name__}) has no test that needs a PairedTarget. "
        "Remove the dcqc_grouping value from these rows."
    )


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
        if not file.is_url_local() and self.stage_files:
            destination = self.path.parent / "staged_files" / f"index_{index}"
            destination.mkdir(parents=True, exist_ok=True)
            file.stage(destination, overwrite=True)

    def list_manifest_rows(self) -> Iterator[ManifestRow]:
        """Iterate over the rows of the manifest, as input for build_targets.

        The dcqc_grouping value of each row is removed from the file
        metadata, because it describes the target, not the file. The spaces
        at the start and end of the value are removed. A missing value
        becomes an empty string. Each File is new, so the change does not
        affect a caller of list_rows_and_files.

        No file is staged here.

        Yields:
            One ManifestRow for each row, in manifest order.
        """
        for index, _, file in self.list_rows_and_files():
            group = (file.metadata.pop("dcqc_grouping", None) or "").strip()
            yield ManifestRow(index, file, group)

    def create_targets(self) -> Iterator[BaseTarget]:
        """Create the targets for the rows of the manifest, and stage them.

        The optional dcqc_grouping column tells which rows go into one
        target. See build_targets for the grouping rules and the checks.

        All rows and groups are checked by build_targets before a file is
        staged or a target is yielded. Thus a bad row or group raises an
        error before any download, and the caller does not get part of the
        targets. Then the files of each target are staged, if stage_files is
        True, before the target is yielded.

        Raises:
            ValueError: If a row or a group is bad, as described in
                build_targets. Thus a grouped TIFF pair is an error, but a
                grouped FASTQ pair is good. Any file type can be a single
                row. The suite makes only the tests that accept the target
                class, so an ungrouped FASTQ row does not get
                PairedFastqParityTest.

        Yields:
            The targets, in the order that build_targets gives.
        """
        for manifest_target in build_targets(self.list_manifest_rows()):
            self._stage_target(manifest_target)
            yield manifest_target.target

    def _stage_target(self, manifest_target: ManifestTarget) -> None:
        """Stage the files of a target from build_targets.

        Each file goes into the directory of its own row. See _stage_file.

        Args:
            manifest_target: The target and its rows.
        """
        for row in manifest_target.rows:
            self._stage_file(row.number, row.file)

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
