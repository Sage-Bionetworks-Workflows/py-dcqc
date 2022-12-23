from collections.abc import Generator

from dcqc.parsers.csv_parser import CsvParser
from dcqc.targets.file_qc_target import QcTargetABC


def test_that_parsing_a_targets_csv_file_yields_qc_targets(get_data):
    csv_path = get_data("file_qc_targets.csv")
    parser = CsvParser(csv_path)
    result = parser.parse_qc_targets()
    assert isinstance(result, Generator)
    result = list(result)
    assert len(result) == 7
    assert all(isinstance(x, QcTargetABC) for x in result)
