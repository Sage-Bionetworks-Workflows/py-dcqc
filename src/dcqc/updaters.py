from collections import defaultdict
from csv import DictWriter
from dataclasses import dataclass
from pathlib import Path
from typing import List

from dcqc.parsers import CsvParser
from dcqc.suites.suite_abc import SuiteABC


@dataclass
class CsvUpdater:
    input_path: Path
    output_path: Path
    parser: CsvParser

    def __init__(self, input_path: Path, output_path: Path):
        self.output_path = output_path
        self.input_path = input_path

    def update(self, suites: List[SuiteABC]):
        suite_dict = defaultdict(list)
        # {url: [list_of_statuses]} data structure to allow for multi-file targets
        # TODO add support for suites with multiple files in them (multi)
        for suite in suites:
            url = suite.target.files[0].url
            status = suite.get_status()
            suite_dict[url].append(status.value)
        # Evaluate dcqc_status for each url
        collapsed_dict = {}
        for url, statuses in suite_dict.items():
            if "RED" in statuses:
                collapsed_dict[url] = "RED"
            elif "AMBER" in statuses:
                collapsed_dict[url] = "AMBER"
            elif "GREEN" in statuses:
                collapsed_dict[url] = "GREEN"
            else:
                collapsed_dict[url] = "NONE"
        # Create CSV data structure
        row_list = []
        parser = CsvParser(self.input_path)
        for _, csv_data in parser.list_rows():
            csv_data["dcqc_status"] = collapsed_dict[csv_data["url"]]
            row_list.append(csv_data)

        if row_list:
            keys = row_list[0].keys()
            # Export updated CSV
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(
                str(self.output_path), "w+", newline="", encoding="utf-8"
            ) as output_file:
                dict_writer = DictWriter(output_file, keys)
                dict_writer.writeheader()
                dict_writer.writerows(row_list)
        else:
            raise ValueError("No rows found in input CSV")
