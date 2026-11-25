import csv
import re
from collections.abc import Callable, Collection, Generator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.parsers import CsvParser, JsonParser
from dcqc.suites.suite_abc import SuiteABC
from dcqc.suites.suites import FastqSuite, TXTSuite
from dcqc.target import PairedTarget, SingleTarget
from dcqc.tests.base_test import BaseTest, TestStatus

# A remote URL for the staging tests. File.stage is patched in each of them,
# so the file is never downloaded.
REMOTE_URL = "syn://syn50555279"


@pytest.fixture
def write_manifest(tmp_path: Path, get_data: Callable) -> Callable:
    """Give a function that writes a manifest with a dcqc_grouping column.

    The function writes the manifest to tmp_path. Each row points at a local
    test file of the given file type, so no file is downloaded. A row in
    remote_rows points at REMOTE_URL instead, so that a test can see if that
    row is staged. All rows have the same placeholder MD5 checksum.

    Args:
        tmp_path: Directory where the manifest is written.
        get_data: Fixture factory that gives the path of a test data file.

    Returns:
        A function that takes the rows and returns the path of the manifest.
        The rows are pairs of a file type, TXT, TIFF or FASTQ, and a grouping
        value. A grouping value of None writes a short row with no grouping
        cell, so that csv.DictReader gives None for that cell. The optional
        remote_rows are the row numbers, which start at 1, that point at
        REMOTE_URL.
    """
    urls = {
        "FASTQ": get_data("fastq1.fastq"),
        "TIFF": get_data("circuit.tif"),
        "TXT": get_data("test.txt"),
    }

    def _write_manifest(
        rows: list[tuple[str, str | None]], remote_rows: Collection[int] = ()
    ) -> Path:
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "md5_checksum", "dcqc_grouping"])
            for index, (file_type, grouping) in enumerate(rows, start=1):
                url = REMOTE_URL if index in remote_rows else str(urls[file_type])
                cells = [url, file_type, "0" * 32]
                if grouping is not None:
                    cells.append(grouping)
                writer.writerow(cells)
        return manifest

    return _write_manifest


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
        self, mocker: MockerFixture, write_manifest: Callable
    ) -> None:
        """Make sure that a bad group raises an error before staging or yielding.

        The bad group is after a row with no grouping value. No file may be
        staged, and no target may be yielded, before the error.

        Args:
            mocker: Fixture that patches File.stage.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a remote single TXT row and then a group of
        # one row
        rows: list[tuple[str, str | None]] = [("TXT", ""), ("FASTQ", "a")]
        manifest = write_manifest(rows, remote_rows={1})
        parser = CsvParser(manifest, stage_files=True)
        stage = mocker.patch.object(File, "stage")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once
        with pytest.raises(ValueError, match=r"Group \(a\) in rows \[2\]"):
            next(targets)

        # AND no file was staged
        stage.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_file_type_is_unknown(
        self, mocker: MockerFixture, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that an unknown file type in a group raises an error at once.

        The group is after a row with no grouping value. No file may be
        staged, and no target may be yielded, before the error. The error
        must tell the group value and the row number.

        Args:
            mocker: Fixture that patches File.stage.
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a remote single TXT row and then a group of a
        # FASTQ row and a row with an unknown file type
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([REMOTE_URL, "TXT", ""])
            writer.writerow([get_data("fastq1.fastq").as_posix(), "FASTQ", "a"])
            writer.writerow([get_data("fastq2.fastq.gz").as_posix(), "tiffx", "a"])
        parser = CsvParser(manifest, stage_files=True)
        stage = mocker.patch.object(File, "stage")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the group and the row
        message = "Group (a) in rows [2, 3] has an unknown file type in row 3."
        with pytest.raises(ValueError, match=re.escape(message)):
            next(targets)

        # AND no file was staged
        stage.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_single_row_type_is_unknown(
        self, mocker: MockerFixture, tmp_path: Path, get_data: Callable
    ) -> None:
        """Make sure that an unknown file type in a single row raises an error at once.

        The bad row is after a good single row. No file may be staged, and
        no target may be yielded, before the error. The error must tell the
        row number.

        Args:
            mocker: Fixture that patches File.stage.
            tmp_path: Directory where the manifest is written.
            get_data: Fixture factory that gives the path of a test data file.
        """
        # GIVEN a manifest with a remote single TXT row and then a single row
        # with an unknown file type
        manifest = tmp_path / "manifest.csv"
        with manifest.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["url", "file_type", "dcqc_grouping"])
            writer.writerow([REMOTE_URL, "TXT", ""])
            writer.writerow([get_data("circuit.tif").as_posix(), "tiffx", ""])
        parser = CsvParser(manifest, stage_files=True)
        stage = mocker.patch.object(File, "stage")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the row
        message = "Row 2 has an unknown file type."
        with pytest.raises(ValueError, match=re.escape(message)):
            next(targets)

        # AND no file was staged
        stage.assert_not_called()

    def test_for_an_error_before_any_file_is_staged_when_a_group_has_two_file_types(
        self, mocker: MockerFixture, write_manifest: Callable
    ) -> None:
        """Make sure that a group with two file types raises an error at once.

        The group is after a row with no grouping value. No file may be
        staged, and no target may be yielded, before the error.

        Args:
            mocker: Fixture that patches File.stage.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a remote single TXT row and then a group of
        # one FASTQ row and one TXT row
        rows: list[tuple[str, str | None]] = [
            ("TXT", ""),
            ("FASTQ", "a"),
            ("TXT", "a"),
        ]
        manifest = write_manifest(rows, remote_rows={1})
        parser = CsvParser(manifest, stage_files=True)
        stage = mocker.patch.object(File, "stage")
        targets = parser.create_targets()

        # WHEN the first target is requested
        # THEN the error comes at once, and it tells the group and the rows
        message = "Group (a) in rows [2, 3] has different file types"
        with pytest.raises(ValueError, match=re.escape(message)):
            next(targets)

        # AND no file was staged
        stage.assert_not_called()

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
        "rows, expected_classes",
        [
            pytest.param(
                [("TXT", ""), ("FASTQ", "")],
                [SingleTarget, SingleTarget],
                id="ungrouped-fastq",
            ),
            pytest.param(
                [("TXT", ""), ("TIFF", "")],
                [SingleTarget, SingleTarget],
                id="ungrouped-tiff",
            ),
        ],
    )
    def test_that_any_file_type_can_be_a_single_row(
        self,
        write_manifest: Callable,
        rows: list[tuple[str, str | None]],
        expected_classes: list[type],
    ) -> None:
        """Make sure that a single row is not checked against its suite.

        The suite makes only the tests that accept the target, so an
        ungrouped FASTQ row gives a SingleTarget, also though FastqSuite has
        a test that needs a PairedTarget. Only a group is checked against
        its suite.

        Args:
            write_manifest: Fixture that writes the manifest.
            rows: The file type and the grouping value of each row.
            expected_classes: The class of each target, in order.
        """
        # GIVEN a manifest with a single TXT row and then an ungrouped FASTQ
        # or TIFF row
        manifest = write_manifest(rows)

        # WHEN the targets are created
        targets = list(CsvParser(manifest).create_targets())

        # THEN no error is raised, and each target has the expected class
        assert [type(target) for target in targets] == expected_classes

    def test_that_a_grouping_value_of_only_spaces_gives_a_single_row(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a value of only spaces is the same as an empty value.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with two TXT rows whose grouping value is only spaces
        rows: list[tuple[str, str | None]] = [("TXT", "   "), ("TXT", "   ")]
        manifest = write_manifest(rows)

        # WHEN the targets are created
        targets = list(CsvParser(manifest).create_targets())

        # THEN each row gives its own SingleTarget
        assert [type(target) for target in targets] == [SingleTarget, SingleTarget]
        assert [target.id for target in targets] == ["0001", "0002"]

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

        # WHEN the targets are created
        targets = list(CsvParser(manifest).create_targets())

        # THEN group b, which starts in row 1, comes before group a
        assert [type(target) for target in targets] == [PairedTarget, PairedTarget]
        assert [target.id for target in targets] == ["0001", "0002"]

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

        # WHEN the targets are created
        with pytest.raises(ValueError) as info:
            list(CsvParser(manifest).create_targets())

        # THEN each value is its own group of one file
        lines = str(info.value).splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("Group (A) in rows [1] has a file count of 1.")
        assert lines[1].startswith("Group (a) in rows [2] has a file count of 1.")

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

        # WHEN the targets are created
        # THEN an error tells the group value, the row numbers and the count
        message = "Group (a) in rows [1, 2, 3] has a file count of 3."
        with pytest.raises(ValueError, match=re.escape(message)):
            list(CsvParser(manifest).create_targets())

    def test_that_one_error_tells_about_all_bad_groups(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that all groups are checked before the error is raised.

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

        # WHEN the targets are created
        with pytest.raises(ValueError) as info:
            list(CsvParser(manifest).create_targets())

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

        # WHEN the targets are created
        with pytest.raises(ValueError) as info:
            list(CsvParser(manifest).create_targets())

        # THEN the error tells about each bad single row and then the bad group
        lines = str(info.value).splitlines()
        assert len(lines) == 3
        assert lines[0].startswith("Row 3 has an unknown file type.")
        assert lines[1].startswith("Row 4 has an unknown file type.")
        assert lines[2].startswith("Group (one) in rows [1] has a file count of 1.")

    def test_that_only_a_group_is_checked_against_the_suite(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a grouped TIFF pair is bad, but ungrouped FASTQ rows are good.

        TiffSuite has no test that needs a PairedTarget, so the TIFF group is
        bad. A single row is not checked against its suite, so the ungrouped
        FASTQ rows are good. The group of one file is also bad.

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

        # WHEN the targets are created
        with pytest.raises(ValueError) as info:
            list(CsvParser(manifest).create_targets())

        # THEN the error tells about the TIFF group and the group of one file
        lines = str(info.value).splitlines()
        assert len(lines) == 2
        assert lines[0].startswith(
            "Group (a) in rows [2, 3] has file type TIFF, but its suite "
            "(TiffSuite) has no test that needs a PairedTarget."
        )
        assert lines[1].startswith("Group (b) in rows [5] has a file count of 1.")

    def test_that_a_remote_file_is_staged_next_to_the_manifest(
        self, mocker: MockerFixture, write_manifest: Callable
    ) -> None:
        """Make sure that a remote file is staged into the directory of its row.

        The directory must be staged_files/index_<number> next to the
        manifest, and an existing copy must be overwritten.

        Args:
            mocker: Fixture that patches File.stage.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest whose second row is remote, and a parser that
        # stages files
        rows: list[tuple[str, str | None]] = [("TXT", ""), ("TXT", "")]
        manifest = write_manifest(rows, remote_rows={2})
        stage = mocker.patch.object(File, "stage")

        # WHEN the targets are created
        targets = list(CsvParser(manifest, stage_files=True).create_targets())

        # THEN the remote file is staged into the directory of row 2, with
        # overwrite. assert_any_call is used because the local file of row 1
        # is staged too: is_file_local is False until local_path is read.
        assert len(targets) == 2
        destination = manifest.parent / "staged_files" / "index_2"
        stage.assert_any_call(destination, overwrite=True)

        # AND the directory exists
        assert destination.is_dir()

    def test_that_no_file_is_staged_when_stage_files_is_false(
        self, mocker: MockerFixture, write_manifest: Callable
    ) -> None:
        """Make sure that a remote file is not staged when stage_files is False.

        Args:
            mocker: Fixture that patches File.stage.
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a remote row, and a parser that does not stage
        # files
        rows: list[tuple[str, str | None]] = [("TXT", "")]
        manifest = write_manifest(rows, remote_rows={1})
        stage = mocker.patch.object(File, "stage")

        # WHEN the targets are created
        targets = list(CsvParser(manifest, stage_files=False).create_targets())

        # THEN the target is created, but no file is staged
        assert len(targets) == 1
        stage.assert_not_called()

        # AND no staged_files directory is made
        assert not (manifest.parent / "staged_files").exists()


class TestCreateSuites:
    """Tests for CsvParser.create_suites.

    Each test writes a small manifest with a dcqc_grouping column to a
    temporary directory. Each row points at a local test file, so no file is
    downloaded. In each error test, a good TXT row comes before the bad row,
    so a lazy create_suites would yield the TXT suite before the error.
    """

    def test_that_an_ungrouped_fastq_row_gives_a_suite_without_the_paired_test(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that an ungrouped FASTQ row gives a FastqSuite that runs.

        The suite has only the tests that accept any target, so it does not
        have PairedFastqParityTest.

        Args:
            write_manifest: Fixture that writes the manifest.
        """
        # GIVEN a manifest with a single TXT row and then an ungrouped FASTQ row
        rows: list[tuple[str, str | None]] = [("TXT", ""), ("FASTQ", "")]
        manifest = write_manifest(rows)

        # WHEN the suites are created
        suites = list(CsvParser(manifest).create_suites())

        # THEN the FASTQ row gives a FastqSuite with a SingleTarget
        assert [type(suite) for suite in suites] == [TXTSuite, FastqSuite]
        fastq_suite = suites[1]
        assert isinstance(fastq_suite.target, SingleTarget)

        # AND the suite does not have the paired test
        test_names = {test.type for test in fastq_suite.tests}
        assert test_names == {"FileExtensionTest", "Md5ChecksumTest"}

        # AND each test runs without an error
        fastq_suite.compute_tests()
        statuses = {test.type: test.get_status() for test in fastq_suite.tests}
        assert TestStatus.ERROR not in statuses.values(), statuses

    def test_for_an_error_before_any_suite_when_a_tiff_pair_is_grouped(
        self, write_manifest: Callable
    ) -> None:
        """Make sure that a grouped TIFF pair raises an error before any suite.

        TiffSuite has no test that needs a PairedTarget, so the TIFF tests
        would quietly be lost.

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
        # THEN the error comes at once and tells the group and the suite
        message = (
            "Group (a) in rows [2, 3] has file type TIFF, but its suite "
            "(TiffSuite) has no test that needs a PairedTarget."
        )
        with pytest.raises(ValueError, match=re.escape(message)):
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
