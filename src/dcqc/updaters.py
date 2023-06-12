from csv import DictWriter
from pathlib import Path
from typing import Dict, List

from dcqc.parsers import CsvParser
from dcqc.suites.suite_abc import SuiteABC


class CsvUpdater:
    input_path: Path
    output_path: Path
    parser: CsvParser

    def __init__(self, input_path: Path, output_path: Path):
        self.output_path = output_path
        self.parser = CsvParser(input_path)

    def update(self, suites: List[SuiteABC]):
        suite_dict: Dict[
            str, List[str]
        ] = {}  # mypy made me do this, but only here. not sure why
        # {url: [list_of_statuses]} data structure to allow for multi-file targets
        for suite in suites:
            url = suite.target.files[0].url
            status = suite.get_status()
            if not suite_dict.get(url):
                suite_dict[url] = [status.value]
            else:
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
        for row in self.parser.list_rows():
            csv_data = row[1]
            csv_data["dcqc_status"] = collapsed_dict[csv_data["url"]]
            row_list.append(csv_data)

        keys = row_list[0].keys()
        # Export updated CSV
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(
            str(self.output_path), "w+", newline="", encoding="utf-8"
        ) as output_file:
            dict_writer = DictWriter(output_file, keys)
            dict_writer.writeheader()
            dict_writer.writerows(row_list)
