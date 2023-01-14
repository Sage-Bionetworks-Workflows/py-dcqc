from collections.abc import Generator

from dcqc.parsers import CsvParser
from dcqc.target import Target


def test_that_parsing_a_targets_csv_file_yields_qc_targets(get_data):
    csv_path = get_data("files.csv")
    parser = CsvParser(csv_path)
    result = parser.create_targets()
    assert isinstance(result, Generator)
    result = list(result)
    assert len(result) > 1
    assert all(isinstance(x, Target) for x in result)
