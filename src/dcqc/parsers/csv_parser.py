import csv
import os
from pathlib import Path

from dcqc.file import File
from dcqc.target import Target


class CsvParser:
    path: Path

    def __init__(self, path: Path):
        self.path = path

    def iterrows(self):
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

    def iter_targets(self):
        for _, row in self.iterrows():
            file = self._row_to_file(row)
            yield Target(file)
