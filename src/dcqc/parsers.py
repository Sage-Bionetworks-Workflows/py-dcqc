import csv
import os
from collections.abc import Iterator
from pathlib import Path

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
        csv_path = self.path
        url = row.pop("url")
        if File.LOCAL_REGEX.match(url):
            scheme, separator, resource = url.rpartition("://")
            path = Path(resource)
            if not path.is_absolute():
                resource = os.path.relpath(csv_path.parent / resource)
            url = "".join([scheme, separator, resource])
        file = File(url, row)
        return file

    def list_targets(self) -> Iterator[Target]:
        for _, row in self.list_rows():
            file = self._row_to_file(row)
            yield Target(file)

    def list_suites(self) -> Iterator[SuiteABC]:
        # TODO: Generalize this function to support multi-file targets
        for target in self.list_targets():
            if len(target.files) > 1:
                message = (
                    f"Target ({target}) is composed of more than one file. "
                    "`iter_suites()` currently only supports single-file targets."
                )
                raise ValueError(message)
            first_file = target.files[0]
            file_type = first_file.get_file_type()
            suite_cls = SuiteABC.get_suite_by_file_type(file_type)
            suite = suite_cls(target)
            yield suite
