#!/usr/bin/env python3
# TODO move this to pytest fixtures

"""Generate test files using latest version of dcqc."""

import os
import sys
from pathlib import Path
from typing import Sequence

from dcqc import tests
from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.parsers import JsonParser
from dcqc.reports import JsonReport
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import SingleTarget

# Shared values
data_dir = sys.path[0]
data_dir = os.path.relpath(data_dir)
report = JsonReport(paths_relative_to=Path.cwd())


# Shared functions
def export(obj: SerializableMixin | Sequence[SerializableMixin], filename: str):
    output_url = os.path.join(data_dir, filename)
    report.save(obj, output_url, overwrite=True)


# file.json
file_url = os.path.join(data_dir, "test.txt")
metadata = {"file_type": "TIFF", "md5_checksum": "14758f1afd44c09b7992073ccf00b43d"}
file = File(file_url, metadata)
export(file, "file.json")

# target.json
target = SingleTarget(file, id="001")
export(target, "target.json")

# test.internal.json
internal_test = tests.Md5ChecksumTest(target)
export(internal_test, "test.internal.json")

# test.external.json
external_test = tests.LibTiffInfoTest(target)
export(external_test, "test.external.json")

# test.computed.json
computed_test = tests.Md5ChecksumTest(target)
computed_test.get_status()
export(computed_test, "test.computed.json")

# tests.json
test_list = [internal_test, external_test, computed_test]
export(test_list, "tests.json")

# suite.json
suite_tests = [internal_test, external_test]
required_tests = ["Md5ChecksumTest"]
skipped_tests = ["LibTiffInfoTest"]
suite = SuiteABC.from_tests(suite_tests, required_tests, skipped_tests)
export(suite, "suite.json")

# suites.json
input_jsons = [
    Path(file_path)
    for file_path in [
        "tests/data/suites_files/suites_1.json",
        "tests/data/suites_files/suites_2.json",
        "tests/data/suites_files/suites_3.json",
    ]
]
suites = [JsonParser.parse_object(json_, SuiteABC) for json_ in input_jsons]
export(suites, "suites.json")
