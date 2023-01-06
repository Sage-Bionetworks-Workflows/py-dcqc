import csv
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

    def iter_targets(self):
        for _, row in self.iterrows():
            url = row.pop("url")
            file = File(url, row)
            yield Target(file)
