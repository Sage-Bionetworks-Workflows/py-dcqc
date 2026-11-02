import csv
import re
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.parsers import CsvParser, JsonParser, _PlannedTarget
from dcqc.suites.suite_abc import SuiteABC
from dcqc.suites.suites import FastqSuite, TXTSuite
from dcqc.target import PairedTarget, SingleTarget
from dcqc.tests.base_test import BaseTest, TestStatus


@pytest.fixture
def write_manifest(tmp_path: Path, get_data: Callable) -> Callable:
    """Give a function that writes a manifest with a dcqc_grouping column.

    The function writes the manifest to tmp_path. Each row points at a local
    test file of the given file type, so no file is downloaded. All rows have
    the same placeholder MD5 checksum.

    Args:
        tmp_path: Directory where the manifest is written.
        get_data: Fixture factory that gives the path of a test data file.

    Returns:
        A function that takes the rows and returns the path of the manifest.
        The rows are pairs of a file type, TXT, TIFF or FASTQ, and a grouping
        value. A grouping value of None writes a short row with no grouping
        cell, so that csv.DictReader gives None for that cell.
    """
    urls = {
        "FASTQ": get_data("fastq1.fastq"),
        "TIFF": get_data("circuit.tif"),
        "TXT": get_data("test.txt"),
    }

    def _write_manifest(rows: list[tuple[str, str | None]]) -> Path:
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "md5_checksum", "dcqc_grouping"])
            for file_type, grouping in rows:
                cells = [str(urls[file_type]), file_type, "0" * 32]
                if grouping is not None:
                    cells.append(grouping)
                writer.writerow(cells)
        return manifest

    return _write_manifest


def plan_indices(plans: list[_PlannedTarget]) -> list[list[int]]:
    """Give the row numbers of each planned target.

    Args:
        plans: The planned targets from CsvParser._plan_targets.

    Returns:
        One list of row numbers for each plan, in the order of the plans.
    """
    return [[index for index, _ in plan.members] for plan in plans]


def test_that_parsing_a_csv_file_yields_suites(get_data):
    csv_path = get_data("files.csv")
    csv_parser = CsvParser(csv_path)
    result = csv_parser.create_suites()
    assert isinstance(result, Generator)
    result = list(result)
    assert len(result) > 1
    assert all(isinstance(x, SuiteABC) for x in result)


def test_that_parsing_a_json_file_must_match_listed_type(get_data):
    json_path = get_data("file.json")
    assert JsonParser.parse_object(json_path, File)
    with pytest.raises(ValueError):
        JsonParser.parse_object(json_path, SingleTarget)


def test_for_an_error_when_parsing_an_unrecognized_type():
    with pytest.raises(ValueError):
        JsonParser.get_class("foobar")


def test_for_an_error_when_parsing_an_abstract_type():
    # An abstract class must be rejected like an unknown name, and not
    # accepted here only to raise a TypeError when it is instantiated.
    with pytest.raises(ValueError):
        JsonParser.get_class("ExternalTestMixin")


def test_for_an_error_when_parsing_a_dictionary_without_a_type():
    dictionary = {"foo": "bar"}
    with pytest.raises(ValueError):
        JsonParser.from_dict(dictionary)


def test_for_an_error_when_parsing_a_list_of_objects_with_parse_object(get_data):
    json_path = get_data("tests.json")
    with pytest.raises(ValueError):
        JsonParser.parse_object(json_path, SerializableMixin)


def test_for_an_error_when_parsing_a_single_object_with_parse_objects(get_data):
    json_path = get_data("target.json")
    with pytest.raises(ValueError):
        JsonParser.parse_objects(json_path, SerializableMixin)


def test_that_json_parser_can_parse_multiple_objects(get_data):
    json_path = get_data("tests.json")
    result = JsonParser.parse_objects(json_path, BaseTest)
    assert len(result) > 0
    assert isinstance(result[0], BaseTest)


class TestCreateTargets:
    """Tests for CsvParser.create_targets.

    Most tests write a small manifest with a dcqc_grouping column to a temporary
    directory. Each row points at a local test file, so no file is
    downloaded.
    """

    def test_that_a_manifest_without_a_grouping_column_yields_single_targets(
        self, get_data: Callable
    ) -> None:
        """Make sure that a manifest with no dcqc_grouping column gives the old targets.

        Each row must give one SingleTarget, and its identifier must be the row
        number with four digits.

        Args:
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest of 8 rows with no dcqc_grouping column
        csv_path = get_data("files_ungrouped.csv")

        # WHEN the targets are created
        targets = list(CsvParser(csv_path).create_targets())

        # THEN each row gives one SingleTarget
        assert len(targets) == 8
        assert all(isinstance(target, SingleTarget) for target in targets)

        # AND each identifier is the row number with four digits
        assert [target.id for target in targets] == [f"{i:04}" for i in range(1, 9)]

    def test_that_grouped_rows_yield_one_paired_target(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that two rows with the same grouping value give one target.

        The two grouped rows are not next to each other, and one value has
        spaces around it. The other rows have an empty grouping value and a
        missing grouping cell, and each must give a SingleTarget. The grouped
        target must come last, and the grouping value must not stay in the file
        metadata.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with two FASTQ rows in group 1 that are not adjacent
        # AND one group value with spaces around it
        # AND a TXT row with an empty value and a TXT row with no grouping cell
        rows = [("TXT", ""), ("FASTQ", " 1 "), ("TXT", None), ("FASTQ", "1")]
        manifest = write_manifest(rows)

        # WHEN the targets are created
        targets = list(CsvParser(manifest).create_targets())

        # THEN each TXT row gives a SingleTarget, and the group gives a
        # PairedTarget last
        assert [type(target) for target in targets] == [
            SingleTarget,
            SingleTarget,
            PairedTarget,
        ]

        # AND the group identifier is its lowest row number
        assert [target.id for target in targets] == ["0001", "0003", "0002"]

        # AND the paired target holds the two FASTQ files
        paired = targets[2]
        assert all(file.type == "FASTQ" for file in paired.files)

        # AND no file keeps the grouping value in its metadata
        assert all("dcqc_grouping" not in file.metadata for file in paired.files)
        assert all(
            "dcqc_grouping" not in target.files[0].metadata for target in targets[:2]
        )

    def test_for_an_error_before_any_file_is_staged_when_a_group_is_bad(
        self, mocker, write_manifest: Callable
    ) -> None:
        """Make sure that a bad group raises an error before staging or yielding.

        The bad group is after a row with no grouping value. No file may be
        staged, and no target may be yielded, before the error.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then a group of one row
        rows: list[tuple[str, str | None]] = [("TXT", ""), ("FASTQ", "a")]
        manifest = write_manifest(rows)
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once
        with pytest.raises(ValueError, match=r"Group \(a\) in rows \[2\]"):
            next(targets)

        # AND no file was staged
        spy.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_file_type_is_unknown(
        self, mocker, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that an unknown file type in a group raises an error at once.

        The group is after a row with no grouping value. No file may be
        staged, and no target may be yielded, before the error. The error
        must tell the group value and the row number.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a single TXT row and then a group of a FASTQ
        # row and a row with an unknown file type
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([get_data("test.txt").as_posix(), "TXT", ""])
            writer.writerow([get_data("fastq1.fastq").as_posix(), "FASTQ", "a"])
            writer.writerow([get_data("fastq2.fastq.gz").as_posix(), "tiffx", "a"])
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the group and the row
        message = "Group (a) in rows [2, 3] has an unknown file type in row 3."
        with pytest.raises(ValueError, match=re.escape(message)):
            next(targets)

        # AND no file was staged
        spy.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_single_row_type_is_unknown(
        self, mocker, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that an unknown file type in a single row raises an error at once.

        The bad row is after a good single row. No file may be staged, and
        no target may be yielded, before the error. The error must tell the
        row number.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a single TXT row and then a single row with an
        # unknown file type
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([get_data("test.txt").as_posix(), "TXT", ""])
            writer.writerow([get_data("circuit.tif").as_posix(), "tiffx", ""])
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the row
        message = "Row 2 has an unknown file type."
        with pytest.raises(ValueError, match=re.escape(message)):
            next(targets)

        # AND no file was staged
        spy.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_group_has_two_file_types(
        self, mocker, write_manifest: Callable
    ) -> None:
        """Make sure that a group with two file types raises an error at once.

        The group is after a row with no grouping value. No file may be
        staged, and no target may be yielded, before the error.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then a group of one
        # FASTQ row and one TXT row
        rows: list[tuple[str, str | None]] = [
            ("TXT", ""),
            ("FASTQ", "a"),
            ("TXT", "a"),
        ]
        manifest = write_manifest(rows)
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the group and the rows
        message = "Group (a) in rows [2, 3] has different file types"
        with pytest.raises(ValueError, match=re.escape(message)):
            next(targets)

        # AND no file was staged
        spy.assert_not_called()

    def test_that_the_paired_target_files_are_in_manifest_order(
        self, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that the files of a PairedTarget are in the order of the rows.

        The two rows point at two different FASTQ files, so that the order can
        be seen in the target.

        Args:
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a compressed FASTQ row before an uncompressed
        # FASTQ row in group a
        first = get_data("fastq2.fastq.gz").as_posix()
        second = get_data("fastq1.fastq").as_posix()
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([first, "FASTQ", "a"])
            writer.writerow([second, "FASTQ", "a"])

        # WHEN the targets are created
        targets = list(CsvParser(manifest).create_targets())

        # THEN there is one PairedTarget
        assert len(targets) == 1
        assert isinstance(targets[0], PairedTarget)

        # AND its files are in the same order as the rows
        assert [file.url for file in targets[0].files] == [first, second]

    @pytest.mark.parametrize(
        "rows, expected_id",
        [
            pytest.param(
                [("TXT", ""), ("TXT", ""), ("FASTQ", "a"), ("TXT", ""), ("FASTQ", "a")],
                "0003",
                id="lowest-row-number",
            ),
            pytest.param(
                [("FASTQ", "../pair 1"), ("FASTQ", "../pair 1")],
                "0001",
                id="unsafe-grouping-value",
            ),
        ],
    )
    def test_that_the_paired_target_id_is_the_lowest_row_number_with_four_digits(
        self,
        write_manifest: Callable,
        rows: list[tuple[str, str | None]],
        expected_id: str,
    ) -> None:
        """Make sure that the identifier of a PairedTarget comes from the row numbers.

        The identifier must be the lowest row number with four digits. It
        must not use the grouping value, because that value can contain
        characters that are not safe in a file name.

        Args:
            write_manifest: Fixture that writes the manifest.
            rows: The file type and the grouping value of each row.
            expected_id: The identifier that the target must have.
        """
        # GIVEN a manifest with one group of two FASTQ rows
        manifest = write_manifest(rows)

        # WHEN the targets are created
        targets = list(CsvParser(manifest).create_targets())

        # THEN the PairedTarget is last, and its identifier is the lowest row
        # number of the group with four digits
        assert isinstance(targets[-1], PairedTarget)
        assert targets[-1].id == expected_id

    @pytest.mark.parametrize(
        "rows, message",
        [
            pytest.param(
                [("TXT", ""), ("FASTQ", "")],
                "Row 2: Target (",
                id="ungrouped-fastq",
            ),
            pytest.param(
                [("TXT", ""), ("TIFF", "a"), ("TIFF", "a")],
                "Group (a) in rows [2, 3]: Target (",
                id="grouped-tiff",
            ),
        ],
    )
    def test_for_an_error_before_any_file_is_staged_when_a_suite_rejects_a_target(
        self,
        mocker,
        write_manifest: Callable,
        rows: list[tuple[str, str | None]],
        message: str,
    ) -> None:
        """Make sure that a target class that its suite rejects is an error at once.

        FastqSuite accepts only a PairedTarget, and TiffSuite accepts only a
        SingleTarget. The bad row or group is after a good single row. No
        file may be staged, and no target may be yielded, before the error.
        The error must tell the rows and the dcqc_grouping hint.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            write_manifest: Fixture that writes the manifest.
            rows: The file type and the grouping value of each row.
            message: The start of the error message.
        """
        # GIVEN a manifest with a single TXT row and then a target that its
        # suite does not accept
        manifest = write_manifest(rows)
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the rows and the hint
        with pytest.raises(ValueError, match="'dcqc_grouping' value") as info:
            next(targets)
        assert str(info.value).startswith(message)

        # AND no file was staged
        spy.assert_not_called()


class TestPlanTargets:
    """Tests for CsvParser._plan_targets.

    Each test writes a small manifest with a dcqc_grouping column to a
    temporary directory. Each row points at a local test file, so no file is
    downloaded.
    """

    def test_that_a_manifest_without_a_grouping_column_gives_only_single_rows(
        self, get_data: Callable
    ) -> None:
        """Make sure that a manifest with no dcqc_grouping column has no groups.

        Each row must be one SingleTarget plan, with its row number, in
        manifest order.

        Args:
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest of 8 rows with no dcqc_grouping column
        csv_path = get_data("files_ungrouped.csv")

        # WHEN the rows are read and checked
        plans = CsvParser(csv_path)._plan_targets()

        # THEN each row is a single row, in manifest order
        assert plan_indices(plans) == [[index] for index in range(1, 9)]
        assert all(plan.target_cls is SingleTarget for plan in plans)

    def test_that_rows_with_no_grouping_value_are_single_rows(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that empty, blank and missing grouping values give single rows.

        A value of only spaces must be the same as an empty value after the
        spaces are removed.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with an empty value, a value of only spaces and a
        # row with no grouping cell
        rows: list[tuple[str, str | None]] = [
            ("TXT", ""),
            ("TXT", "   "),
            ("TXT", None),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        plans = CsvParser(manifest)._plan_targets()

        # THEN each row is a single row
        assert plan_indices(plans) == [[1], [2], [3]]
        assert all(plan.target_cls is SingleTarget for plan in plans)

        # AND no file keeps the grouping value in its metadata
        files = [file for plan in plans for _, file in plan.members]
        assert all("dcqc_grouping" not in file.metadata for file in files)

    def test_that_grouped_rows_are_collected_into_one_group(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that rows with the same grouping value go into one group.

        The grouped rows are not next to each other, and one value has spaces
        around it. The members must be in manifest order, and the grouping
        value must not stay in the file metadata.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with two FASTQ rows in group 1 that are not adjacent
        # AND one group value with spaces around it
        rows: list[tuple[str, str | None]] = [
            ("FASTQ", " 1 "),
            ("TXT", ""),
            ("FASTQ", "1"),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        plans = CsvParser(manifest)._plan_targets()

        # THEN the TXT row is a single row, and it comes first
        # AND there is one group, with its members in manifest order
        assert plan_indices(plans) == [[2], [1, 3]]
        assert [plan.target_cls for plan in plans] == [SingleTarget, PairedTarget]

        # AND no file keeps the grouping value in its metadata
        members = plans[1].members
        assert all("dcqc_grouping" not in file.metadata for _, file in members)

    def test_that_groups_are_in_the_order_of_their_first_row(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that the groups are in the order of their first row.

        The order must not come from the grouping values, so group b comes
        before group a when its first row is earlier in the manifest.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest where the first row of group b is before group a
        rows: list[tuple[str, str | None]] = [
            ("FASTQ", "b"),
            ("FASTQ", "a"),
            ("FASTQ", "a"),
            ("FASTQ", "b"),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        plans = CsvParser(manifest)._plan_targets()

        # THEN group b comes first, and each group has its own rows
        assert plan_indices(plans) == [[1, 4], [2, 3]]

    def test_for_an_error_when_a_group_is_bad(self, write_manifest: Callable) -> None:
        """Make sure that a bad group raises an error after a good group.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a good group and then a group of one row
        rows: list[tuple[str, str | None]] = [
            ("FASTQ", "a"),
            ("FASTQ", "a"),
            ("FASTQ", "b"),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        # THEN an error tells the bad group value and its row numbers
        parser = CsvParser(manifest)
        with pytest.raises(ValueError, match=re.escape("Group (b) in rows [3]")):
            parser._plan_targets()

    def test_that_grouping_values_are_case_sensitive(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that values with different case go into different groups.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with two FASTQ rows whose values differ only in case
        rows: list[tuple[str, str | None]] = [("FASTQ", "A"), ("FASTQ", "a")]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        # THEN each value is its own group of one file, which raises an error
        parser = CsvParser(manifest)
        with pytest.raises(
            ValueError,
            match=re.escape("Group (A) in rows [1] has a file count of 1"),
        ):
            parser._plan_targets()

    def test_for_an_error_when_a_group_has_two_file_types(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a group of two files with different file types is bad.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a group of one FASTQ row and one TXT row
        rows: list[tuple[str, str | None]] = [("FASTQ", "a"), ("TXT", "a")]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        # THEN an error tells the group value, the row numbers and the types
        message = "Group (a) in rows [1, 2] has different file types: ['FASTQ', 'TXT']."
        parser = CsvParser(manifest)
        with pytest.raises(ValueError, match=re.escape(message)):
            parser._plan_targets()

    def test_for_an_error_when_a_group_has_three_files(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a group of three files is bad.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a group of three FASTQ rows
        rows: list[tuple[str, str | None]] = [
            ("FASTQ", "a"),
            ("FASTQ", "a"),
            ("FASTQ", "a"),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        # THEN an error tells the group value, the row numbers and the count
        message = "Group (a) in rows [1, 2, 3] has a file count of 3."
        parser = CsvParser(manifest)
        with pytest.raises(ValueError, match=re.escape(message)):
            parser._plan_targets()

    def test_that_one_error_tells_about_all_bad_groups(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that all groups are sorted before the error is raised.

        The error must tell about each bad group, and not about the good
        group.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a group of one file, a pair with two file
        # types, a group of three files and a good pair
        rows: list[tuple[str, str | None]] = [
            ("FASTQ", "one"),
            ("FASTQ", "pair"),
            ("TXT", "pair"),
            ("FASTQ", "list"),
            ("FASTQ", "list"),
            ("FASTQ", "list"),
            ("FASTQ", "good"),
            ("FASTQ", "good"),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        parser = CsvParser(manifest)
        with pytest.raises(ValueError) as info:
            parser._plan_targets()

        # THEN the error tells about each bad group
        message = str(info.value)
        assert "Group (one) in rows [1] has a file count of 1." in message
        assert "Group (pair) in rows [2, 3] has different file types" in message
        assert "Group (list) in rows [4, 5, 6] has a file count of 3." in message

        # AND it does not tell about the good group
        assert "Group (good)" not in message

    def test_that_one_error_tells_about_bad_single_rows_and_bad_groups(
        self, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that the bad single rows come first in the error.

        The error must tell about each bad single row, in manifest order,
        and then about each bad group. It must not tell about the good row.

        Args:
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a group of one file, a good single row and
        # two single rows with unknown file types
        txt = get_data("test.txt").as_posix()
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([txt, "TXT", "one"])
            writer.writerow([txt, "TXT", ""])
            writer.writerow([txt, "tiffx", ""])
            writer.writerow([txt, "txtx", ""])

        # WHEN the rows are read and checked
        parser = CsvParser(manifest)
        with pytest.raises(ValueError) as info:
            parser._plan_targets()

        # THEN the error tells about each bad single row and then the bad group
        lines = str(info.value).splitlines()
        assert len(lines) == 3
        assert lines[0].startswith("Row 3 has an unknown file type.")
        assert lines[1].startswith("Row 4 has an unknown file type.")
        assert lines[2].startswith("Group (one) in rows [1] has a file count of 1.")

    def test_that_one_error_tells_about_all_target_class_errors(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that the suite checks do not stop at the first error.

        The error must tell about each target that its suite does not
        accept, and also about the other bad groups, in the same order as
        the other errors.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with two ungrouped FASTQ rows, a grouped TIFF
        # pair, a group of one file and a good TXT row
        rows: list[tuple[str, str | None]] = [
            ("FASTQ", ""),
            ("TIFF", "a"),
            ("TIFF", "a"),
            ("FASTQ", ""),
            ("FASTQ", "b"),
            ("TXT", ""),
        ]
        manifest = write_manifest(rows)

        # WHEN the rows are read and checked
        parser = CsvParser(manifest)
        with pytest.raises(ValueError) as info:
            parser._plan_targets()

        # THEN the error tells about each bad single row and then each bad
        # group
        lines = str(info.value).splitlines()
        assert len(lines) == 4
        assert lines[0].startswith("Row 1: Target (")
        assert lines[0].endswith("Give the files the same 'dcqc_grouping' value.")
        assert lines[1].startswith("Row 4: Target (")
        assert lines[2].startswith("Group (a) in rows [2, 3]: Target (")
        assert lines[2].endswith("Remove the 'dcqc_grouping' value from these files.")
        assert lines[3].startswith("Group (b) in rows [5] has a file count of 1.")


class TestCreateSuites:
    """Tests for CsvParser.create_suites.

    Each test writes a small manifest with a dcqc_grouping column to a
    temporary directory. Each row points at a local test file, so no file is
    downloaded. In each error test, a good TXT row comes before the bad row,
    so a lazy create_suites would yield the TXT suite before the error.
    """

    def test_for_an_error_before_any_suite_when_a_tiff_pair_is_grouped(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a grouped TIFF target raises an error before any suite.

        TiffSuite accepts only a SingleTarget.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then two grouped TIFF rows
        rows: list[tuple[str, str | None]] = [
            ("TXT", ""),
            ("TIFF", "a"),
            ("TIFF", "a"),
        ]
        manifest = write_manifest(rows)
        suites = CsvParser(manifest).create_suites()

        # WHEN the first suite is requested
        # THEN the error comes at once and tells the user to remove the value
        with pytest.raises(ValueError, match="Remove the 'dcqc_grouping' value"):
            next(suites)

    def test_for_an_error_before_any_suite_when_a_fastq_row_is_not_grouped(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that an ungrouped FASTQ row raises an error before any suite.

        FastqSuite accepts only a PairedTarget.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then an ungrouped FASTQ row
        rows: list[tuple[str, str | None]] = [("TXT", ""), ("FASTQ", "")]
        manifest = write_manifest(rows)
        suites = CsvParser(manifest).create_suites()

        # WHEN the first suite is requested
        # THEN the error comes at once and tells the user to group the files
        with pytest.raises(ValueError, match="same 'dcqc_grouping' value"):
            next(suites)

    def test_for_an_error_before_any_suite_when_a_single_row_type_is_unknown(
        self, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that an unknown file type in a single row has its row number.

        Args:
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a single TXT row and then a single row with an
        # unknown file type
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([get_data("test.txt").as_posix(), "TXT", ""])
            writer.writerow([get_data("circuit.tif").as_posix(), "tiffx", ""])
        suites = CsvParser(manifest).create_suites()

        # WHEN the first suite is requested
        # THEN the error comes at once and tells the row
        message = "Row 2 has an unknown file type."
        with pytest.raises(ValueError, match=re.escape(message)):
            next(suites)

    def test_for_an_error_before_any_file_is_staged_when_a_tiff_pair_is_grouped(
        self, mocker, write_manifest: Callable
    ) -> None:
        """Make sure that a grouped TIFF target raises an error before staging.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then two grouped TIFF rows
        rows: list[tuple[str, str | None]] = [
            ("TXT", ""),
            ("TIFF", "a"),
            ("TIFF", "a"),
        ]
        manifest = write_manifest(rows)
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        suites = parser.create_suites()

        # WHEN the first suite is requested
        # THEN the error comes at once
        with pytest.raises(ValueError, match="Remove the 'dcqc_grouping' value"):
            next(suites)

        # AND no file was staged
        spy.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_fastq_row_is_not_grouped(
        self, mocker, write_manifest: Callable
    ) -> None:
        """Make sure that an ungrouped FASTQ row raises an error before staging.

        Args:
            mocker: Fixture that makes the spy on _stage_file.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then an ungrouped FASTQ row
        rows: list[tuple[str, str | None]] = [("TXT", ""), ("FASTQ", "")]
        manifest = write_manifest(rows)
        parser = CsvParser(manifest, stage_files=True)
        spy = mocker.spy(parser, "_stage_file")
        suites = parser.create_suites()

        # WHEN the first suite is requested
        # THEN the error comes at once
        with pytest.raises(ValueError, match="same 'dcqc_grouping' value"):
            next(suites)

        # AND no file was staged
        spy.assert_not_called()

    def test_that_a_grouped_fastq_manifest_gives_a_suite_that_runs(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a grouped FASTQ pair gives a FastqSuite that runs.

        All tests of the suite must run on the PairedTarget without an error.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then two grouped FASTQ rows
        rows: list[tuple[str, str | None]] = [
            ("TXT", ""),
            ("FASTQ", "a"),
            ("FASTQ", "a"),
        ]
        manifest = write_manifest(rows)

        # WHEN the suites are created
        suites = list(CsvParser(manifest).create_suites())

        # THEN the TXT row gives a TXTSuite, and the pair gives a FastqSuite
        assert [type(suite) for suite in suites] == [TXTSuite, FastqSuite]
        fastq_suite = suites[1]
        assert isinstance(fastq_suite.target, PairedTarget)

        # AND each test of the FastqSuite runs without an error
        fastq_suite.compute_tests()
        statuses = {test.type: test.get_status() for test in fastq_suite.tests}
        assert TestStatus.ERROR not in statuses.values(), statuses


class TestStageFile:
    """Tests for CsvParser._stage_file.

    Each test gives a mock File, so no file is downloaded. The manifest path
    is in a temporary directory, so the staged_files directory is made there.
    The manifest itself is not written, because the method does not read it.
    """

    manifest: Path

    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path: Path) -> None:
        """Keep the manifest path for the parsers.

        Args:
            tmp_path: Directory that holds the manifest path.
        """
        self.manifest = tmp_path / "manifest.csv"

    def make_file(self, mocker, is_local: bool):
        """Make a mock File that tells if it is local.

        Args:
            mocker: Fixture that makes the mock.
            is_local: The value that is_file_local returns.

        Returns:
            The mock File.
        """
        file = mocker.create_autospec(File, instance=True)
        file.is_file_local.return_value = is_local
        return file

    def test_that_a_remote_file_is_staged_next_to_the_manifest(self, mocker) -> None:
        """Make sure that a remote file is staged into its row directory.

        The directory must be staged_files/index_<number> next to the
        manifest, and an existing copy must be overwritten.

        Args:
            mocker: Fixture that makes the mock File.
        """
        # GIVEN a parser that stages files, and a remote file
        parser = CsvParser(self.manifest, stage_files=True)
        file = self.make_file(mocker, is_local=False)

        # WHEN the file of row 3 is staged
        parser._stage_file(3, file)

        # THEN the file is staged into the directory of row 3, with overwrite
        destination = self.manifest.parent / "staged_files" / "index_3"
        file.stage.assert_called_once_with(destination, overwrite=True)

        # AND the directory exists
        assert destination.is_dir()

    def test_that_a_remote_file_is_not_staged_when_stage_files_is_false(
        self, mocker
    ) -> None:
        """Make sure that no file is staged when stage_files is False.

        Args:
            mocker: Fixture that makes the mock File.
        """
        # GIVEN a parser that does not stage files, and a remote file
        parser = CsvParser(self.manifest, stage_files=False)
        file = self.make_file(mocker, is_local=False)

        # WHEN the file is staged
        parser._stage_file(1, file)

        # THEN the file is not staged
        file.stage.assert_not_called()

        # AND no staged_files directory is made
        assert not (self.manifest.parent / "staged_files").exists()

    def test_that_a_local_file_is_not_staged(self, mocker) -> None:
        """Make sure that a local file is not staged, also when stage_files is True.

        Args:
            mocker: Fixture that makes the mock File.
        """
        # GIVEN a parser that stages files, and a local file
        parser = CsvParser(self.manifest, stage_files=True)
        file = self.make_file(mocker, is_local=True)

        # WHEN the file is staged
        parser._stage_file(1, file)

        # THEN the file is not staged
        file.stage.assert_not_called()

        # AND no staged_files directory is made
        assert not (self.manifest.parent / "staged_files").exists()


class TestEnsureGroupFileTypesKnown:
    """Tests for CsvParser._ensure_group_file_types_known.

    The tests give the row numbers and files directly, so no manifest is
    read. The parser path has no effect on the method.
    """

    parser: CsvParser
    fastq_file: File
    compressed_fastq_file: File

    @pytest.fixture(autouse=True)
    def setup_method(self, get_data: Callable, test_files: dict[str, File]) -> None:
        """Make a parser and the files for the groups.

        Args:
            get_data: Fixture factory that gives the path of a test data file.
            test_files: Fixture that maps a key to a test file.
        """
        self.parser = CsvParser(get_data("files.csv"))
        self.fastq_file = test_files["good_fastq"]
        self.compressed_fastq_file = test_files["good_compressed_fastq"]

    def test_that_a_group_of_known_file_types_raises_no_error(self) -> None:
        """Make sure that a group with known file types passes the check."""
        # GIVEN a group of a FASTQ file and a TXT file
        txt_file = File(self.fastq_file.url, {"file_type": "TXT"})
        members = [(3, self.fastq_file), (7, txt_file)]

        # WHEN the file types are checked
        # THEN no error is raised
        self.parser._ensure_group_file_types_known("a", members)

    def test_for_an_error_when_a_file_of_the_group_has_an_unknown_file_type(
        self,
    ) -> None:
        """Make sure that an unknown file type raises an error with its row number."""
        # GIVEN a group of a FASTQ file and a file with an unknown file type
        unknown_file = File(self.fastq_file.url, {"file_type": "tiffx"})
        members = [(3, self.fastq_file), (7, unknown_file)]

        # WHEN the file types are checked
        # THEN an error tells the group value, the row numbers and the bad row
        message = "Group (a) in rows [3, 7] has an unknown file type in row 7."
        with pytest.raises(ValueError, match=re.escape(message)):
            self.parser._ensure_group_file_types_known("a", members)
