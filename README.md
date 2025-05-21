# py-dcqc

<!--
[![ReadTheDocs](https://readthedocs.org/projects/dcqc/badge/?version=latest)](https://sage-bionetworks-workflows.github.io/dcqc/)
-->
[![PyPI-Server](https://img.shields.io/pypi/v/dcqc.svg)](https://pypi.org/project/dcqc/)
[![codecov](https://codecov.io/gh/Sage-Bionetworks-Workflows/py-dcqc/branch/main/graph/badge.svg?token=OCC4MOUG5P)](https://codecov.io/gh/Sage-Bionetworks-Workflows/py-dcqc)
[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](#pyscaffold)

> Python package for performing quality control (QC) for data coordination (DC)

## Purpose

This Python package provides a framework for performing quality control (QC) on data files. Quality control can range from low-level integrity checks (_e.g._ MD5 checksum, file extension) to high-level checks such as conformance to a format specification and consistency with associated metadata.

The tool is designed to be flexible and extensible, allowing for:
- File integrity validation
- Format specification conformance
- Metadata consistency checks
- Custom test suite creation
- Integration with external QC tools
- Batch processing of multiple files
- Comprehensive reporting in JSON format

## Core Concepts

### Files and FileTypes

A `File` represents a local or remote file along with its metadata. Each file has an associated `FileType` that bundles information about:
- Valid file extensions
- EDAM format ontology identifiers
- File type-specific validation rules

Built-in file types include TXT, JSON, JSON-LD, TIFF, OME-TIFF, TSV, CSV, BAM, FASTQ, and HDF5.

### Targets

A `Target` represents one or more files that should be validated together. There are two types of targets:
- `SingleTarget`: For validating individual files
- `PairedTarget`: For validating exactly two related files together (e.g., paired-end sequencing data)

### Tests

Tests are individual validation checks that can be run on targets. There are two types of tests:

1. **Internal Tests**: Tests written and executed in Python
   - File extension validation
   - Metadata consistency checks
   - Format validation
   
2. **External Tests**: Tests that utilize external tools or processes
   - File integrity checks (MD5, checksums)
   - Format-specific validation tools
   - Custom validation scripts

Tests are further organized into tiers:
- Tier 1: File Integrity - Basic file integrity checks
- Tier 2: Internal Conformance - Format and metadata conformance checks run internally
- Tier 3: External Conformance - Format validation using external tools
- Tier 4: Subjective Conformance - Checks that may require human judgment

### Suites

A `Suite` is a collection of tests that are specific to a particular file type (e.g., FASTQ, BAM, CSV). Each file type has its own suite of tests that are appropriate for that format. Suites:
- Group tests together based on the target file type
- Can specify required vs optional tests:
  - By default, Tier 1 (File Integrity) and Tier 2 (Internal Conformance) tests are required
  - Users can explicitly specify which tests are required by name
- Allow tests to be skipped if specified in the suite
- Provide overall validation status:
  - GREEN: All tests passed
  - RED: One or more required tests failed
  - AMBER: All required tests passed, but optional tests failed
  - GREY: Error occurred during testing

### Reports

Reports provide structured output of test results in various formats:
- JSON reports for machine readability
- CSV updates for batch processing
- Detailed test status and error messages
- Aggregated results across multiple suites

## Installation

You can install py-dcqc directly from PyPI:

```bash
pip install dcqc
```

For development installation from source:

```bash
git clone https://github.com/Sage-Bionetworks-Workflows/py-dcqc.git
cd py-dcqc
pip install -e .
```

### Docker

You can also use the official Docker container:

```bash
docker pull ghcr.io/sage-bionetworks-workflows/py-dcqc:latest
```

To run commands using the Docker container:

```bash
docker run ghcr.io/sage-bionetworks-workflows/py-dcqc:latest dcqc --help
```

For processing local files, remember to mount your data directory:

```bash
docker run -v /path/to/your/data:/data ghcr.io/sage-bionetworks-workflows/py-dcqc:latest dcqc qc_file --input-file /data/myfile.csv --file-type csv
```

## Command Line Interface

To see all available commands and their options:

```bash
dcqc --help
```

Main commands include:

- `create_targets`: Create target JSON files from a targets CSV file
- `create_tests`: Create test JSON files from a target JSON file
- `create_process`: Create external process JSON file from a test JSON file
- `compute_test`: Compute the test status from a test JSON file
- `create_suite`: Create a suite from a set of test JSON files sharing the same target
- `combine_suites`: Combine several suite JSON files into a single JSON report
- `list_tests`: List the tests available for each file type
- `qc_file`: Run QC tests on a single file (external tests are skipped)
- `update_csv`: Update input CSV file with dcqc_status column

For detailed help on any command:

```bash
dcqc <command> --help
```

## Example Usage

### Basic File QC

Run QC on a single file:

```bash
dcqc qc-file --input-file data.csv --file-type csv --metadata '{"author": "John Doe"}'
```

### Creating and Running Test Suites

1. Create targets from a CSV file:
```bash
dcqc create-targets input_targets.csv output_dir/
```

2. Create tests for a target:
```bash
dcqc create-tests target.json tests_dir/ --required-tests "ChecksumTest" "FormatTest"
```

3. Run tests and create a suite:
```bash
dcqc create-suite --output-json results.json test1.json test2.json test3.json
```

### Listing Available Tests

To see all available tests for different file types:

```bash
dcqc list-tests
```

## Integration with nf-dcqc

Early versions of this package were developed to be used by its sibling, the [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) Nextflow workflow. The initial command-line interface was developed with nf-dcqc in mind, favoring smaller steps to enable parallelism in Nextflow.

# PyScaffold

This project has been set up using PyScaffold 4.3. For details and usage
information on PyScaffold see https://pyscaffold.org/.

```console
putup --name dcqc --markdown --github-actions --pre-commit --license Apache-2.0 py-dcqc
```
