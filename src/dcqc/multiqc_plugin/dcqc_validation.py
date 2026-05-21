"""MultiQC module that parses DCQC ``suites.json`` and renders validation results.

The heavy lifting (parsing the suites JSON shape into table-ready rows) is
extracted into module-level pure functions so it can be unit-tested without
spinning up MultiQC. :class:`MultiqcModule` is a thin shell that wires those
results into MultiQC's section/table APIs.
"""

import json
import logging
from typing import Any

from multiqc.base_module import BaseMultiqcModule
from multiqc.plots import table

log = logging.getLogger(__name__)


class ModuleNoSamplesFound(Exception):
    """Raised when no DCQC validation files are discovered."""


SuiteSummary = dict[str, Any]
TestDetail = dict[str, Any]


def parse_suites(
    suites: list[dict[str, Any]],
    sample_id_cleaner=None,
    file_context=None,
) -> tuple[dict[str, SuiteSummary], list[TestDetail]]:
    """Parse a deserialized ``suites.json`` payload.

    Returns a ``(suite_summaries, test_details)`` pair.

    ``sample_id_cleaner`` lets callers plug in MultiQC's
    ``BaseMultiqcModule.clean_s_name`` so sample IDs match those produced by
    other modules. When omitted the raw target id (or filename) is used.
    """

    suite_summaries: dict[str, SuiteSummary] = {}
    test_details: list[TestDetail] = []

    for suite in suites:
        suite_type = suite.get("type", "Unknown")
        target = suite.get("target", {})
        files = target.get("files", [])
        if not files:
            continue

        file_info = files[0]
        file_name = file_info.get("name", "Unknown")
        raw_id = target.get("id", file_name)
        if sample_id_cleaner is not None:
            sample_id = sample_id_cleaner(raw_id, file_context)
        else:
            sample_id = raw_id

        suite_status = suite.get("suite_status", {})
        overall_status = suite_status.get("status", "UNKNOWN")
        required_tests = suite_status.get("required_tests", [])

        tests = suite.get("tests", [])
        test_counts = {"passed": 0, "failed": 0, "skipped": 0}

        for test in tests:
            test_status = test.get("status", "unknown")
            if test_status in test_counts:
                test_counts[test_status] += 1
            test_details.append(
                {
                    "sample": sample_id,
                    "file": file_name,
                    "suite_type": suite_type,
                    "test_type": test.get("type", "Unknown"),
                    "tier": test.get("tier", "-"),
                    "status": test_status,
                    "reason": test.get("status_reason", ""),
                    "external": test.get("is_external_test", False),
                }
            )

        suite_summaries[sample_id] = {
            "file_name": file_name,
            "suite_type": suite_type,
            "overall_status": overall_status,
            "total_tests": len(tests),
            "passed": test_counts["passed"],
            "failed": test_counts["failed"],
            "skipped": test_counts["skipped"],
            "required_tests_count": len(required_tests),
        }

    return suite_summaries, test_details


def group_by_suite_type(
    suite_summaries: dict[str, SuiteSummary],
    test_details: list[TestDetail],
) -> dict[str, dict[str, Any]]:
    """Group summaries and test details by their suite type."""
    grouped: dict[str, dict[str, Any]] = {}
    for sample_id, data in suite_summaries.items():
        suite_type = data["suite_type"]
        grouped.setdefault(suite_type, {"samples": {}, "tests": []})
        grouped[suite_type]["samples"][sample_id] = data
    for test in test_details:
        suite_type = test["suite_type"]
        if suite_type in grouped:
            grouped[suite_type]["tests"].append(test)
    return grouped


STATUS_FORMATTING_RULES = {
    "pass": [{"s_eq": "GREEN"}],
    "warn": [{"s_eq": "YELLOW"}, {"s_eq": "AMBER"}, {"s_eq": "GREY"}],
    "fail": [{"s_eq": "RED"}],
}

TEST_STATUS_FORMATTING_RULES = {
    "pass": [{"s_eq": "passed"}],
    "warn": [{"s_eq": "skipped"}],
    "fail": [{"s_eq": "failed"}],
}


def general_stats_payload(
    suite_summaries: dict[str, SuiteSummary],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Build the ``(data, headers)`` pair MultiQC needs for general stats."""
    data = {
        sample_id: {
            "suite_type": summary["suite_type"],
            "status": summary["overall_status"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "total": summary["total_tests"],
        }
        for sample_id, summary in suite_summaries.items()
    }
    headers = {
        "suite_type": {
            "title": "Suite Type",
            "description": "Type of validation suite",
            "scale": False,
        },
        "status": {
            "title": "Status",
            "description": "Overall validation status",
            "scale": False,
            "cond_formatting_rules": STATUS_FORMATTING_RULES,
        },
        "passed": {
            "title": "Passed",
            "description": "Number of tests passed",
            "scale": "Greens",
            "format": "{:,.0f}",
        },
        "failed": {
            "title": "Failed",
            "description": "Number of tests failed",
            "scale": "Reds",
            "format": "{:,.0f}",
        },
        "total": {
            "title": "Total",
            "description": "Total number of tests run",
            "scale": "Blues",
            "format": "{:,.0f}",
        },
    }
    return data, headers


def suite_summary_table(
    suite_type: str,
    samples: dict[str, SuiteSummary],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    """Build ``(data, headers, config)`` for the per-suite summary table."""
    data = {
        sample_id: {
            "file_name": summary["file_name"],
            "status": summary["overall_status"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "total": summary["total_tests"],
        }
        for sample_id, summary in samples.items()
    }
    headers = {
        "file_name": {
            "title": "File Name",
            "description": "Data file name",
            "scale": False,
        },
        "status": {
            "title": "Overall Status",
            "description": "Overall validation status",
            "scale": False,
            "cond_formatting_rules": STATUS_FORMATTING_RULES,
        },
        "passed": {
            "title": "Passed",
            "description": "Number of tests passed",
            "scale": "Greens",
            "format": "{:,.0f}",
        },
        "failed": {
            "title": "Failed",
            "description": "Number of tests failed",
            "scale": "Reds",
            "format": "{:,.0f}",
        },
        "total": {
            "title": "Total Tests",
            "description": "Total number of tests run",
            "scale": "Blues",
            "format": "{:,.0f}",
        },
    }
    config = {
        "id": f"dcqc_{suite_type}_summary_table",
        "namespace": f"DCQC {suite_type}",
        "title": f"{suite_type} File Summary",
        "col1_header": "Sample ID",
    }
    return data, headers, config


def details_table_payload(
    suite_type: str,
    tests: list[TestDetail],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, str]]:
    """Build ``(data, headers, config)`` for the per-suite test-details table."""
    data: dict[str, dict[str, Any]] = {}
    for idx, test in enumerate(tests):
        row_id = f"{test['sample']}_{test['test_type']}_{idx}"
        data[row_id] = {
            "sample": test["sample"],
            "test": test["test_type"],
            "tier": test["tier"],
            "status": test["status"],
            "external": "Yes" if test["external"] else "No",
        }
    headers = {
        "sample": {
            "title": "Sample ID",
            "description": "Sample identifier",
            "scale": False,
        },
        "test": {
            "title": "Test Name",
            "description": "Name of the validation test",
            "scale": False,
        },
        "tier": {
            "title": "Tier",
            "description": "Test tier level",
            "scale": False,
        },
        "status": {
            "title": "Status",
            "description": "Test result status",
            "scale": False,
            "cond_formatting_rules": TEST_STATUS_FORMATTING_RULES,
        },
        "external": {
            "title": "External",
            "description": "Whether this is an external test",
            "scale": False,
        },
    }
    config = {
        "id": f"dcqc_{suite_type}_details_table",
        "namespace": f"DCQC {suite_type}",
        "title": f"{suite_type} Test Details",
        "col1_header": "Test",
    }
    return data, headers, config


FAILED_TESTS_MAX_REASON_LINES = 50


def failed_tests_html(suite_type: str, tests: list[TestDetail]) -> str | None:
    """Build the HTML block for failed tests, or ``None`` if there are none."""
    failed_tests = [t for t in tests if t["status"] == "failed" and t["reason"]]
    if not failed_tests:
        return None

    parts = [
        '<div class="alert alert-danger">',
        f"<h4>{suite_type} Failed Test Details</h4>",
    ]
    for test in failed_tests:
        parts.append(
            '<div style="margin-bottom: 20px; padding: 10px; '
            'border-left: 3px solid #d9534f;">'
        )
        parts.append(
            f"<h5><strong>{test['file']}</strong> - {test['test_type']}</h5>"
        )
        parts.append(
            f"<p><strong>Sample:</strong> {test['sample']} | "
            f"<strong>Tier:</strong> {test['tier']}</p>"
        )
        parts.append(
            '<div style="background-color: #f5f5f5; padding: 10px; '
            "border-radius: 4px; font-family: monospace; white-space: pre-wrap; "
            'font-size: 0.9em;">'
        )

        lines = test["reason"].split("\\n")
        for line in lines[:FAILED_TESTS_MAX_REASON_LINES]:
            if line.strip():
                parts.append(f"{line}\n")
        if len(lines) > FAILED_TESTS_MAX_REASON_LINES:
            parts.append(
                f"\n... ({len(lines) - FAILED_TESTS_MAX_REASON_LINES} more lines)\n"
            )

        parts.append("</div></div>")

    parts.append("</div>")
    return "".join(parts)


class MultiqcModule(BaseMultiqcModule):
    """DCQC validation module — parses ``suites.json`` and renders results."""

    def __init__(self) -> None:
        super().__init__(
            name="DCQC Validation",
            anchor="dcqc_validation",
            href="https://github.com/Sage-Bionetworks-Workflows/py-dcqc",
            info="displays validation results from DCQC suite testing",
            extra=(
                "Validates data files against schema requirements using DCQC "
                "test suites"
            ),
        )

        self.suite_data: dict[str, SuiteSummary] = {}
        self.test_details: list[TestDetail] = []

        num_suites = self._parse_log_files()
        if num_suites == 0:
            log.info("Could not find any DCQC validation results")
            raise ModuleNoSamplesFound

        log.info("Found %d DCQC validation results", num_suites)

        self.suite_types = group_by_suite_type(self.suite_data, self.test_details)

        self._add_general_statistics()
        for suite_type in sorted(self.suite_types.keys()):
            self._add_suite_type_sections(suite_type)

    def _parse_log_files(self) -> int:
        log.info("Looking for DCQC validation files...")
        for f in self.find_log_files("dcqc_validation", filehandles=True):
            log.info("Processing file: %s", f["fn"])
            try:
                data = json.load(f["f"])
            except json.JSONDecodeError:
                log.warning("Could not parse JSON from %s", f["fn"], exc_info=True)
                continue
            try:
                summaries, details = parse_suites(
                    data,
                    sample_id_cleaner=self.clean_s_name,
                    file_context=f,
                )
            except Exception:
                log.warning("Error processing %s", f["fn"], exc_info=True)
                continue

            for sample_id in summaries:
                self.add_data_source(f, s_name=sample_id)
            self.suite_data.update(summaries)
            self.test_details.extend(details)

        return len(self.suite_data)

    def _add_general_statistics(self) -> None:
        if not self.suite_data:
            return
        data, headers = general_stats_payload(self.suite_data)
        self.general_stats_addcols(data, headers)

    def _add_suite_type_sections(self, suite_type: str) -> None:
        suite_info = self.suite_types[suite_type]
        samples = suite_info["samples"]
        tests = suite_info["tests"]
        if not samples:
            return
        self._add_suite_summary_section(suite_type, samples)
        self._add_suite_test_details_section(suite_type, tests)
        self._add_suite_failed_tests_section(suite_type, tests)

    def _add_suite_summary_section(
        self, suite_type: str, samples: dict[str, SuiteSummary]
    ) -> None:
        if not samples:
            return
        data, headers, config = suite_summary_table(suite_type, samples)
        plural = "s" if len(samples) > 1 else ""
        self.add_section(
            name=f"{suite_type} Validation",
            anchor=f"dcqc-{suite_type.lower()}-summary",
            description=(
                f"Validation results for {suite_type} files "
                f"({len(samples)} file{plural})"
            ),
            plot=table.plot(data, headers, config),
        )

    def _add_suite_test_details_section(
        self, suite_type: str, tests: list[TestDetail]
    ) -> None:
        if not tests:
            return
        data, headers, config = details_table_payload(suite_type, tests)
        self.add_section(
            name=f"{suite_type} Test Details",
            anchor=f"dcqc-{suite_type.lower()}-details",
            description=(
                f"Detailed results for each {suite_type} validation test"
            ),
            plot=table.plot(data, headers, config),
        )

    def _add_suite_failed_tests_section(
        self, suite_type: str, tests: list[TestDetail]
    ) -> None:
        html = failed_tests_html(suite_type, tests)
        if html is None:
            return
        failed_count = sum(
            1 for t in tests if t["status"] == "failed" and t["reason"]
        )
        self.add_section(
            name=f"{suite_type} Failed Tests",
            anchor=f"dcqc-{suite_type.lower()}-failed",
            description=(
                f"Detailed error messages for {failed_count} failed "
                f"{suite_type} test(s)"
            ),
            content=html,
        )
