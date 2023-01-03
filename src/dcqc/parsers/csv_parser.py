import csv
from pathlib import Path

from dcqc.targets.file_target import FileTarget


class CsvParser:
    path: Path

    def __init__(self, path: Path):
        self.path = path

    def iterrows(self):
        with self.path.open(newline="") as file:
            reader = csv.DictReader(file)
            for index, row in enumerate(reader, start=1):
                yield index, row

    def parse_qc_targets(self):
        for index, row in self.iterrows():
            uri = row.pop("uri")
            yield FileTarget(uri, row, index)
