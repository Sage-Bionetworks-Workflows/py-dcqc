import sys
from csv import DictWriter
from pathlib import Path
from typing import List

from typer import Argument, Option, Typer

from dcqc.file import FileType
from dcqc.parsers import CsvParser, JsonParser
from dcqc.reports import JsonReport
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import Target
from dcqc.tests.test_abc import ExternalTestMixin, TestABC

app = Typer()


# Common arguments
# Distinguishing between path and path/url arguments until I/O is consistent
input_path_arg = Argument(..., help="Input file")
input_path_list_arg = Argument(..., help="List of input files")
output_arg = Argument(..., help="Path or (remote) URL for output file.")
output_dir_arg = Argument(..., help="Directory path or (remote) URL for output files.")
output_path_arg = Argument(..., help="Path for output file.")
output_dir_path_arg = Argument(..., help="Directory path for output files.")

# Common options
overwrite_opt = Option(False, "--overwrite", "-f", help="Ignore existing files.")
required_tests_opt = Option(None, "--required-tests", "-r", help="Required tests.")
skipped_tests_opt = Option(None, "--skipped-tests", "-s", help="Skipped tests.")


@app.command()
def create_targets(
    input_csv: Path = input_path_arg,
    output_dir: str = output_dir_arg,
    overwrite: bool = overwrite_opt,
):
    """Create target JSON files from a targets CSV file."""
    parser = CsvParser(input_csv)
    targets = parser.create_targets()

    # Naming the targets by index to ensure no clashes
    indexed_targets = enumerate(targets, start=1)
    named_targets = {f"{index}.json": target for index, target in indexed_targets}

    report = JsonReport()
    report.save_many(named_targets, output_dir, overwrite)


# TODO: Add `--absolute-paths` option to avoid relative paths in JSON files
@app.command()
def stage_target(
    input_json: Path = input_path_arg,
    output_dir: Path = output_dir_path_arg,
    overwrite: bool = overwrite_opt,
):
    """Create local file copies from a target JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    target = JsonParser.parse_expected(input_json, Target)
    for path in target.stage(output_dir, overwrite):
        print(f"Finished staging {path!s}...")


@app.command()
def create_tests(
    input_json: Path = input_path_arg,
    output_dir: Path = output_dir_path_arg,
    required_tests: List[str] = required_tests_opt,
    skipped_tests: List[str] = skipped_tests_opt,
    overwrite: bool = overwrite_opt,
):
    """Create test JSON files from a target JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)

    target = JsonParser.parse_expected(input_json, Target)
    suite = SuiteABC.from_target(target, required_tests, skipped_tests)

    report = JsonReport()
    for test in suite.tests:
        output_path = output_dir / f"{input_json.stem}-{test.type}.json"
        output_url = output_path.as_posix()
        report.save(test, output_url, overwrite)


@app.command()
def create_process(
    input_json: Path = input_path_arg,
    output_path: Path = output_path_arg,
    overwrite: bool = overwrite_opt,
):
    """Create external process JSON file from a test JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    test = JsonParser.parse_expected(input_json, ExternalTestMixin)
    process = test.generate_process()
    output_url = output_path.as_posix()

    report = JsonReport()
    report.save(process, output_url, overwrite)


@app.command()
def compute_test(
    input_json: Path = input_path_arg,
    output_path: Path = output_path_arg,
    overwrite: bool = overwrite_opt,
):
    """Compute the test status from a test JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    test = JsonParser.parse_expected(input_json, TestABC)
    test.get_status()
    output_url = output_path.as_posix()

    report = JsonReport()
    report.save(test, output_url, overwrite)


@app.command()
def create_suite(
    output: str = output_arg,
    input_jsons: List[Path] = input_path_list_arg,
    required_tests: List[str] = required_tests_opt,
    skipped_tests: List[str] = skipped_tests_opt,
    overwrite: bool = overwrite_opt,
):
    """Create a suite from a set of test JSON files sharing the same target."""
    tests = [JsonParser.parse_expected(test_json, TestABC) for test_json in input_jsons]
    suite = SuiteABC.from_tests(tests, required_tests, skipped_tests)
    report = JsonReport()
    report.save(suite, output, overwrite)


@app.command()
def combine_suites(
    output: str = output_arg,
    input_jsons: List[Path] = input_path_list_arg,
    overwrite: bool = overwrite_opt,
):
    """Combine several suite JSON files into a single JSON report."""
    suites = [JsonParser.parse_expected(json_, SuiteABC) for json_ in input_jsons]
    report = JsonReport()
    report.save(suites, output, overwrite)


@app.command()
def list_tests():
    """List the tests available for each file type."""
    test_classes_by_file_type = SuiteABC.list_test_classes_by_file_type()

    rows = list()
    for file_type_name, test_classes in test_classes_by_file_type.items():
        file_type = FileType.get_file_type(file_type_name)
        for test_cls in test_classes:
            test_dict = {
                "file_type": file_type_name,
                "edam_iri": file_type.edam_iri,
                "test_name": test_cls.__name__,
                "test_tier": test_cls.tier,
                "test_type": "external" if test_cls.is_external_test else "internal",
            }
            rows.append(test_dict)

    fieldnames = list(rows[0])
    writer = DictWriter(sys.stdout, fieldnames)
    writer.writeheader()
    writer.writerows(rows)
