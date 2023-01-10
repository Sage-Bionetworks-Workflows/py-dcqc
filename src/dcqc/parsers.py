import csv
from collections.abc import Collection, Iterator
from pathlib import Path
from typing import Optional

from dcqc.file import File
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import Target


class CsvParser:
    path: Path

    def __init__(self, path: Path):
        self.path = path

    def list_rows(self) -> Iterator[tuple[int, dict]]:
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                yield index, row

    def _row_to_file(self, row: dict[str, str]) -> File:
        csv_directory = self.path.parent
        url = row.pop("url")
        file = File(url, row, relative_to=csv_directory)
        return file

    def create_files(self) -> Iterator[File]:
        for _, row in self.list_rows():
            file = self._row_to_file(row)
            yield file

    def create_targets(self) -> Iterator[Target]:
        for file in self.create_files():
            yield Target(file)

    def create_suites(
        self,
        required_tests: Optional[Collection[str]] = None,
        skipped_tests: Optional[Collection[str]] = None,
    ) -> Iterator[SuiteABC]:
        for target in self.create_targets():
            # This function assumes that there is one file per target,
            # which is always the case when parsing CSV files (for now)
            first_file = target.files[0]
            file_type = first_file.get_file_type()
            suite_cls = SuiteABC.get_suite_by_file_type(file_type)
            suite = suite_cls(target, required_tests, skipped_tests)
            yield suite
