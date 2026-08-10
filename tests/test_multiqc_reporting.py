"""Unit tests for the MultiQC reporting helpers.

These cover the pure parsing/shaping functions in
:mod:`dcqc.multiqc_plugin.dcqc_validation` — they do not exercise
:class:`MultiqcModule` itself because that requires a running MultiQC
environment.
"""

import pytest

pytest.importorskip("multiqc")

from dcqc.multiqc_plugin.dcqc_validation import (  # noqa: E402
    FAILED_TESTS_MAX_REASON_LINES,
    details_table_payload,
    failed_tests_html,
    general_stats_payload,
    group_by_suite_type,
    parse_suites,
    suite_summary_table,
)


def _make_suite(
    suite_type="H5ADSuite",
    sample_id="sample_1",
    file_name="sample_1.h5ad",
    overall_status="GREEN",
    tests=None,
    required_tests=None,
):
    return {
        "type": suite_type,
        "target": {"id": sample_id, "files": [{"name": file_name}]},
        "suite_status": {
            "status": overall_status,
            "required_tests": required_tests or [],
        },
        "tests": tests if tests is not None else [],
    }


def _make_test(test_type="H5adHtanValidatorTest", status="passed", reason="", tier="2"):
    return {
        "type": test_type,
        "tier": tier,
        "status": status,
        "status_reason": reason,
        "is_external_test": True,
    }


def test_parse_suites_well_formed_payload():
    suites = [
        _make_suite(
            tests=[
                _make_test(status="passed"),
                _make_test(
                    test_type="FileExtensionTest", status="failed", reason="bad ext"
                ),
                _make_test(test_type="Md5ChecksumTest", status="skipped"),
            ]
        )
    ]

    summaries, details = parse_suites(suites)

    assert set(summaries) == {"sample_1"}
    summary = summaries["sample_1"]
    assert summary["file_name"] == "sample_1.h5ad"
    assert summary["suite_type"] == "H5ADSuite"
    assert summary["overall_status"] == "GREEN"
    assert summary["total_tests"] == 3
    assert summary["passed"] == 1
    assert summary["failed"] == 1
    assert summary["skipped"] == 1

    assert len(details) == 3
    failed = next(d for d in details if d["status"] == "failed")
    assert failed["test_type"] == "FileExtensionTest"
    assert failed["reason"] == "bad ext"
    assert failed["external"] is True


def test_parse_suites_empty_input():
    summaries, details = parse_suites([])
    assert summaries == {}
    assert details == []


def test_parse_suites_skips_suites_with_no_files():
    suites = [
        {
            "type": "FileSuite",
            "target": {"id": "no_files", "files": []},
            "suite_status": {"status": "GREY"},
            "tests": [],
        }
    ]
    summaries, details = parse_suites(suites)
    assert summaries == {}
    assert details == []


def test_parse_suites_uses_sample_id_cleaner():
    suites = [_make_suite(sample_id="raw.name.h5ad")]

    calls: list[tuple] = []

    def cleaner(raw, ctx):
        calls.append((raw, ctx))
        return raw.split(".")[0]

    summaries, _ = parse_suites(
        suites, sample_id_cleaner=cleaner, file_context={"fn": "suites.json"}
    )
    assert set(summaries) == {"raw"}
    assert calls == [("raw.name.h5ad", {"fn": "suites.json"})]


def test_parse_suites_falls_back_to_filename_when_no_id():
    suites = [
        {
            "type": "FileSuite",
            "target": {"files": [{"name": "only.txt"}]},
            "tests": [],
        }
    ]
    summaries, _ = parse_suites(suites)
    assert set(summaries) == {"only.txt"}


def test_group_by_suite_type_separates_suites():
    suites = [
        _make_suite(suite_type="H5ADSuite", sample_id="a", tests=[_make_test()]),
        _make_suite(
            suite_type="TiffSuite",
            sample_id="b",
            file_name="b.tif",
            tests=[_make_test()],
        ),
    ]
    summaries, details = parse_suites(suites)
    grouped = group_by_suite_type(summaries, details)

    assert set(grouped) == {"H5ADSuite", "TiffSuite"}
    assert set(grouped["H5ADSuite"]["samples"]) == {"a"}
    assert set(grouped["TiffSuite"]["samples"]) == {"b"}
    assert len(grouped["H5ADSuite"]["tests"]) == 1
    assert len(grouped["TiffSuite"]["tests"]) == 1


def test_general_stats_payload_shapes():
    summaries = {
        "s": {
            "file_name": "s.h5ad",
            "suite_type": "H5ADSuite",
            "overall_status": "GREEN",
            "total_tests": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
            "required_tests_count": 1,
        }
    }
    data, headers = general_stats_payload(summaries)
    assert data == {
        "s": {
            "suite_type": "H5ADSuite",
            "status": "GREEN",
            "passed": 2,
            "failed": 0,
            "total": 2,
        }
    }
    assert set(headers) == {"suite_type", "status", "passed", "failed", "total"}
    assert headers["status"]["cond_formatting_rules"]["pass"][0]["s_eq"] == "GREEN"


def test_suite_summary_table_config_ids():
    samples = {
        "sample_1": {
            "file_name": "f.h5ad",
            "suite_type": "H5ADSuite",
            "overall_status": "GREEN",
            "total_tests": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "required_tests_count": 1,
        }
    }
    data, headers, config = suite_summary_table("H5ADSuite", samples)
    assert "sample_1" in data
    assert data["sample_1"]["status"] == "GREEN"
    assert config["id"] == "dcqc_H5ADSuite_summary_table"
    assert config["namespace"] == "DCQC H5ADSuite"


def test_details_table_payload_unique_row_ids():
    tests = [
        {
            "sample": "s",
            "file": "f.h5ad",
            "suite_type": "H5ADSuite",
            "test_type": "Md5ChecksumTest",
            "tier": "1",
            "status": "passed",
            "reason": "",
            "external": False,
        },
        {
            "sample": "s",
            "file": "f.h5ad",
            "suite_type": "H5ADSuite",
            "test_type": "Md5ChecksumTest",
            "tier": "1",
            "status": "failed",
            "reason": "mismatch",
            "external": False,
        },
    ]
    data, headers, config = details_table_payload("H5ADSuite", tests)
    assert len(data) == 2  # idx suffix keeps rows distinct
    assert config["id"] == "dcqc_H5ADSuite_details_table"


def test_failed_tests_html_returns_none_when_no_failures():
    tests = [{"status": "passed", "reason": ""}]
    assert failed_tests_html("H5ADSuite", tests) is None


def test_failed_tests_html_renders_failure_block():
    tests = [
        {
            "sample": "s",
            "file": "f.h5ad",
            "suite_type": "H5ADSuite",
            "test_type": "FileExtensionTest",
            "tier": "1",
            "status": "failed",
            "reason": "unexpected suffix",
            "external": False,
        }
    ]
    html = failed_tests_html("H5ADSuite", tests)
    assert html is not None
    assert "FileExtensionTest" in html
    assert "unexpected suffix" in html
    assert html.startswith('<div class="alert alert-danger">')
    assert html.endswith("</div>")


def test_failed_tests_html_truncates_long_reasons():
    long_reason = "\\n".join(
        f"line {i}" for i in range(FAILED_TESTS_MAX_REASON_LINES + 5)
    )
    tests = [
        {
            "sample": "s",
            "file": "f.h5ad",
            "suite_type": "H5ADSuite",
            "test_type": "FileExtensionTest",
            "tier": "1",
            "status": "failed",
            "reason": long_reason,
            "external": False,
        }
    ]
    html = failed_tests_html("H5ADSuite", tests)
    assert html is not None
    assert f"... ({5} more lines)" in html
