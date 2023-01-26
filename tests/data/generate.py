#!/usr/bin/env python3

"""Generate test files using latest version of dcqc."""

import os
import sys

from dcqc.file import File
from dcqc.mixins import SerializableMixin
from dcqc.reports import JsonReport
from dcqc.suites.suite_abc import SuiteABC
from dcqc.target import Target
from dcqc.tests import tests

# Shared values
data_dir = sys.path[0]
data_dir = os.path.relpath(data_dir)
report = JsonReport()


# Shared functions
def export(obj: SerializableMixin, filename: str):
    output_url = os.path.join(data_dir, filename)
    report.save(obj, output_url, overwrite=True)


# target.json
file_url = os.path.join(data_dir, "test.txt")
metadata = {"file_type": "TIFF", "md5_checksum": "14758f1afd44c09b7992073ccf00b43d"}
file = File(file_url, metadata)
target = Target(file, id="001")
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

# suite.json
suite_tests = [internal_test, external_test]
required_tests = ["Md5ChecksumTest"]
skipped_tests = ["LibTiffInfoTest"]
suite = SuiteABC.from_tests(suite_tests, required_tests, skipped_tests)
export(suite, "suite.json")
