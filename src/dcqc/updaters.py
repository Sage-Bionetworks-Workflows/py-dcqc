from csv import DictWriter
from pathlib import Path
from dcqc.parsers import CsvParser, JsonParser
from dcqc.suites.suite_abc import SuiteABC
from typing import List, Dict


class CsvUpdater:
    input_path: Path
    output_path: Path
    parser: CsvParser

    def __init__(self, input_path: Path, output_path: Path):
        self.input_path = input_path
        self.output_path = output_path
        self.parser = CsvParser(input_path)

    def update(self, suites: List[SuiteABC]):
        suite_dict: Dict[str, List[str]] = {}  # mypy made me do this, not sure why
        for suite in suites:
            url = suite.target.files[0].url
            status = suite.get_status()
            if not suite_dict.get(url):
                suite_dict[url] = [status.value]
            else:
                suite_dict[url].append(status.value)

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

        row_list = []
        for row in self.parser.list_rows():
            csv_data = row[1]
            csv_data["dcqc_status"] = collapsed_dict[csv_data["url"]]
            row_list.append(csv_data)

        keys = row_list[0].keys()

        with open(
            str(self.output_path), "w", newline="", encoding="utf-8"
        ) as output_file:
            dict_writer = DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(row_list)
