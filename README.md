# py-dcqc

<!--
[![ReadTheDocs](https://readthedocs.org/projects/dcqc/badge/?version=latest)](https://sage-bionetworks-workflows.github.io/dcqc/)
-->
[![PyPI-Server](https://img.shields.io/pypi/v/dcqc.svg)](https://pypi.org/project/dcqc/)
[![codecov](https://codecov.io/gh/Sage-Bionetworks-Workflows/py-dcqc/branch/main/graph/badge.svg?token=OCC4MOUG5P)](https://codecov.io/gh/Sage-Bionetworks-Workflows/py-dcqc)
[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](#pyscaffold)

> Python package for performing quality control (QC) for data coordination (DC)

## Table of Contents

- [Intended Audience](#intended-audience)
- [Purpose](#purpose)
- [Core Concepts](#core-concepts)
  - [Files and FileTypes](#files-and-filetypes)
  - [Targets](#targets)
  - [Tests](#tests)
  - [Suites](#suites)
  - [Reports](#reports)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Docker](#docker)
- [Command Line Interface](#command-line-interface)
  - [Common options](#common-options)
- [Input](#input)
- [Output](#output)
- [Getting Started](#getting-started)
  - [Tutorials](#tutorials)
    - [Listing Available Tests](#listing-available-tests)
    - [Basic File QC](#basic-file-qc)
    - [Internal Test by Hand](#internal-test-by-hand)
    - [External Test by Hand](#external-test-by-hand)
    - [Internal Test in the py-dcqc Docker Image](#internal-test-in-the-py-dcqc-docker-image)
- [Integration with nf-dcqc](#integration-with-nf-dcqc)
- [PyScaffold](#pyscaffold)

## Intended Audience

This package is designed to be used by [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc), the Nextflow workflow that runs the QC steps in parallel. It is not intended for direct use by end users. The CLI is deliberately split into many small commands that read and write JSON so that _nf-dcqc_ can distribute the steps.

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

Built-in file types include:

- TXT
- JSON
- JSON-LD
- TIFF
- OME-TIFF
- TSV
- CSV
- BAM
- FASTQ
- HDF5
- H5AD

### Targets

A target is one unit of QC: the file, or the pair of files, that `dcqc` judges together and reports on as a single row. Its `id` is what ties its scattered test results back into one verdict.

#### The two types of targets

There are two types of targets:

- `SingleTarget`: exactly one file.
- `PairedTarget`: exactly two related files, such as paired-end sequencing data.

#### Why targets exist

**Some checks need more than one file at a time.** A test has exactly one target, not a list of files. When a `PairedTarget` counts the lines of read 1 and read 2 and compares the two counts, it can see both files only because both are in one target. Without targets, each test would have to invent its own way to group files.

**A target is also what keeps split-up results together.** This is the reason that matters even for single-file QC. The CLI divides QC into small steps so that _nf-dcqc_ can run them at the same time on different machines, which scatters one target's tests across separate JSON files. The target `id` is what matches them back up: `create-tests` names every file it writes after the target, and `create-suite` rejects a set of tests that do not all share one target.

### Tests

Tests are individual validation checks that can be run on targets. There are two types of tests:

1. **Internal Tests**: The check is Python code in this package, so `dcqc` runs it and returns a status immediately. Today these cover tiers 1 and 2.

2. **External Tests**: The check is a command-line tool in a Docker container. `dcqc` cannot run it. The test only describes the container image and the command to run, and the [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) workflow runs that container. The result comes back through `compute-test`. Today these cover tiers 2 and 4.

The tiers are described below. For the tests themselves, run `dcqc list-tests`: the `test_tier` column gives the tier of each test, and the last column shows whether it is internal or external. Because `dcqc` cannot run external tests on its own, `dcqc qc-file` skips all of them.

Tests are further organized into four tiers. The tier decides whether a test is required: by default, tier-1 and tier-2 tests must pass for a suite to be GREEN, while tier-3 and tier-4 tests are optional.

The list below gives the intended scope of each tier, then the tests that exist today.

- Tier 1 - File Integrity: Checking that the file is whole and "available". These tests verify basic file integrity and usually require additional information, including:
  - MD5 checksum verification
  - Expected file extension checks
  - Format-specific checks (e.g., first/last bytes)
  - Decompression checks if applicable

- Tier 2 - Internal Conformance: Checking that the file is internally consistent and compliant with its stated format. These tests only need the files themselves and their format specification:
  - File format validation using available tools
  - Internal metadata validation against schema (e.g., OME XML)
  - Additional checks on internal metadata

- Tier 3 - External Conformance: Checking that file features are consistent with separately submitted metadata. These tests use additional information but remain objective/quantitative:
  - Channel count consistency
  - File/image size consistency
  - Antibody nomenclature conformance
  - Secondary file presence (e.g., CRAI file for CRAM)

- Tier 4 - Subjective Conformance: Checking files against qualitative criteria that may need expert review. These tests often involve metrics, heuristics, or sophisticated models:
  - Sample swap detection
  - PHI detection in images and metadata
  - Outlier detection using metrics (e.g., file size)

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

## Prerequisites

See [Prerequisites in CONTRIBUTING.md](CONTRIBUTING.md#prerequisites) for the tools you need (pipenv, tox) and the full setup.

## Installation

You can install py-dcqc directly from PyPI:

```bash
pip install 'dcqc[all]'
```

The `all` extra adds `rdflib`, which `JsonLdLoadTest` needs to parse JSON-LD files. Without it, that one test raises `ModuleNotFoundError` when you compute its status, while every other test continues to work. The published Docker image installs this extra. If you know you will never check JSON-LD files, plain `pip install dcqc` is enough.

For development installation from source, use pipenv. `Pipfile.lock` is committed and the rest of the repo assumes that environment:

```bash
git clone https://github.com/Sage-Bionetworks-Workflows/py-dcqc.git
cd py-dcqc
pipenv install --dev
```

Installing into a virtualenv of your own with `pip install -e '.[all,testing,dev]'` is an equivalent fallback. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full setup.

### Docker

You can also use the official Docker container:

```bash
docker pull ghcr.io/sage-bionetworks-workflows/py-dcqc:main
```

**Use the `main` tag.** It is built from the default branch on every push, so it
matches the code in this repository.


To run commands using the Docker container:

```bash
docker run ghcr.io/sage-bionetworks-workflows/py-dcqc:main dcqc --help
```

For processing local files, remember to mount your data directory:

```bash
docker run -v /path/to/your/data:/data ghcr.io/sage-bionetworks-workflows/py-dcqc:main \
  dcqc qc-file /data/myfile.csv --file-type csv \
  --metadata '{"md5_checksum": "my_files_checksum"}'
```

`Md5ChecksumTest` compares the file against an expected checksum, which it reads
from the `md5_checksum` key in the file metadata. `qc-file` reads no manifest, so
that value can only come from `--metadata`. If the key is missing, the command
stops with a `KeyError` instead of reporting a test result. When you do not have a
checksum for the file, skip that one test:

```bash
docker run -v /path/to/your/data:/data ghcr.io/sage-bionetworks-workflows/py-dcqc:main \
  dcqc qc-file /data/myfile.csv --file-type csv --skipped-tests Md5ChecksumTest
```

## Command Line Interface

To see all available commands and their options:

```bash
dcqc --help
```

To print the installed version:

```bash
dcqc --version
```

If the `dcqc` console script is not on your PATH, you can call the same interface as a module:

```bash
python -m dcqc --help
```

Main commands include:

- `create-targets`: Create target JSON files from a targets CSV file
- `create-tests`: Create test JSON files from a target JSON file
- `create-process`: Create external process JSON file from a test JSON file
- `compute-test`: Compute the test status from a test JSON file
- `create-suite`: Create a suite from a set of test JSON files sharing the same target
- `combine-suites`: Combine several suite JSON files into a single JSON report
- `list-tests`: List the tests available for each file type
- `qc-file`: Run QC tests on a single file (external tests are skipped)
- `update-csv`: Update input CSV file with dcqc_status column

### Common options

Several commands share the same options:

| Option | Short | Description | Accepted by |
|---|---|---|---|
| `--overwrite` | `-f` | Ignore existing files | `create-targets`, `create-tests`, `create-process`, `compute-test`, `create-suite`, `combine-suites` |
| `--required-tests` | `-r` | Tests that must pass for the suite to be GREEN. Repeat the option for each test. Defaults to all tier-1 and tier-2 tests | `create-tests`, `create-suite`, `qc-file` |
| `--skipped-tests` | `-s` | Tests that should not be evaluated. Repeat the option for each test | `create-tests`, `create-suite`, `qc-file` |
| `--file-type` | `-t` | File type, such as TXT or TIFF. Required | `qc-file` |
| `--metadata` | `-m` | File metadata as a JSON string. Defaults to `{}` | `qc-file` |

Test names for `--required-tests` and `--skipped-tests` are the test class names that `dcqc list-tests` prints, for example `Md5ChecksumTest`.

For detailed help on any command:

```bash
dcqc <command> --help
```


## Input

The input is a tabular file that contains a list of the file targets to run through dcqc

- Here is a single file target input file example, also at `examples/example_manifest_single.csv`

  | url               | file_type | md5_checksum                     |
  |-------------------|-----------|----------------------------------|
  | syn://syn41864974 | TXT       | 38b86a456d1f441008986c6f798d5ef9 |

- Here is an input file example with several targets, also at `examples/example_manifest.csv`. Every row becomes its own single-file target, so the rows are checked independently of one another.

  | url               | file_type | md5_checksum                     |
  |-------------------|----------|----------------------------------|
  | syn://syn41864974 | TXT      | 38b86a456d1f441008986c6f798d5ef9 |
  | syn://syn41864977 | TXT      | make-status-red                  |
  | syn://syn43716055 | TIFF     | 38b86a456d1f441008986c6f798d5ef9 |
  | syn://syn43716711 | TIFF     | a542e9b744bedcfd874129ab0f98c4ff |

## Output

The output is a tabular file with your original targets files but additional columns including `dcqc_status`.

- Here is an example of the output of a single file target that ran through dcqc:

  | url               | file_type | md5_checksum                     | dcqc_status | dcqc_required_tests                | dcqc_skipped_tests | dcqc_failed_tests | dcqc_errored_tests |
  |-------------------|----------|----------------------------------|-------------|------------------------------------|--------------------|-------------------|--------------------|
  | syn://syn41864974 | TXT      | 38b86a456d1f441008986c6f798d5ef9 | GREEN       | Md5ChecksumTest,FileExtensionTest |                    |                   |                    |

- Here is an example of the output of multi-file targets that ran through dcqc:

  | url               | file_type | md5_checksum                     | dcqc_status | dcqc_required_tests                                 | dcqc_skipped_tests | dcqc_failed_tests                 | dcqc_errored_tests     |
  |-------------------|----------|----------------------------------|-------------|-----------------------------------------------------|--------------------|-----------------------------------|------------------------|
  | syn://syn41864974 | TXT      | 38b86a456d1f441008986c6f798d5ef9 | GREEN       | Md5ChecksumTest,FileExtensionTest                   |                    |                                   |                        |
  | syn://syn41864977 | TXT      | make-status-red                  | RED         | Md5ChecksumTest,FileExtensionTest                   |                    | Md5ChecksumTest                   |                        |
  | syn://syn43716055 | TIFF     | 38b86a456d1f441008986c6f798d5ef9 | GREY        | Md5ChecksumTest,FileExtensionTest,LibTiffInfoTest   |                    | FileExtensionTest,LibTiffInfoTest | TiffTag306DateTimeTest |
  | syn://syn43716711 | TIFF     | a542e9b744bedcfd874129ab0f98c4ff | GREY        | Md5ChecksumTest,FileExtensionTest,LibTiffInfoTest   |                    | FileExtensionTest,LibTiffInfoTest | TiffTag306DateTimeTest |

`dcqc_required_tests` holds the required set of the suite. Both tables above use the default, which is every tier-1 and tier-2 test of the file type. Give `--required-tests` to `create-suite` or `qc-file` to use a different set.

**The order of the names inside a cell is not stable.** This applies to the four list columns — `dcqc_required_tests`, `dcqc_skipped_tests`, `dcqc_failed_tests`, and `dcqc_errored_tests` — because they come from Python sets, so the same input can give the same names in a different order on the next run. Compare the set of names, not the text of the cell, and do not use these cells in a byte comparison against an expected file.

## Getting Started

### Tutorials

Three of the sections below are also runnable scripts, so that you can see a whole pipeline work before you read it step by step. All three take their input from `examples/`, write every artifact to a directory of their own, and need `SYNAPSE_AUTH_TOKEN` in your environment.

| Script | Section | Writes |
|---|---|---|
| `examples/internal.sh` | [Internal Test by Hand](#internal-test-by-hand) | `internal_example/results.csv` |
| `examples/external.sh` | [External Test by Hand](#external-test-by-hand) | `external_example/results.csv` |
| `examples/docker.sh` | [Internal Test in the py-dcqc Docker Image](#internal-test-in-the-py-dcqc-docker-image) | `docker_example/results.csv` |

`examples/docker.sh` needs only `docker`, because it runs `dcqc` in the published image. `examples/internal.sh` needs `dcqc` itself, so activate the project environment first with `source "$(pipenv --venv)/bin/activate"`. `examples/external.sh` needs that same activated environment plus `docker` and `jq` on your PATH, because it runs each external test's container by hand.

#### Listing Available Tests

To see all available tests for different file types:

```bash
dcqc list-tests
```

#### Basic File QC

Run QC on a single file:

```bash
dcqc qc-file examples/data.csv --file-type csv \
  --metadata '{"md5_checksum": "52f81b43ac7bde58d3c97184588fba07"}'
```

To run without a checksum, skip that test instead:

```bash
dcqc qc-file examples/data.csv --file-type csv --skipped-tests Md5ChecksumTest
```

#### Internal Test by Hand

Walks the full internal pipeline — `create-targets` → `create-tests` → `compute-test` → `create-suite` → `combine-suites` → `update-csv` — command by command in a local Python environment. The manifest is `examples/internal_target.csv`, the single TXT row from [Input](#input), so every test in its suite is internal and no container is needed. The commands must run in this order, because each one validates the type of the JSON it is given.

```bash
export SYNAPSE_AUTH_TOKEN=<your personal access token>
bash examples/internal.sh
```

`examples/internal.sh` runs the pipeline itself; read it for the commands and the reasoning behind each one. It refuses to run if `internal_example/` already exists, and writes its result to `internal_example/results.csv`, in the shape shown in [Output](#output).

The [Internal Test in the py-dcqc Docker Image](#internal-test-in-the-py-dcqc-docker-image) section below runs this same pipeline in the published image instead, with no local install.

#### External Test by Hand

*nf-dcqc* is the supported way to run external tests, and the only practical way to run a manifest of them. `examples/external.sh` does the same work by hand with `docker run`, so you can see what *nf-dcqc* does for you. The manifest is `examples/external_target.csv`, the single TIFF row from [Input](#input); a TIFF suite has three external tests — `LibTiffInfoTest`, `TiffDateTimeTest` and `TiffTag306DateTimeTest` — each needing its own container run, plus the same two internal tests as above.

```bash
export SYNAPSE_AUTH_TOKEN=<your personal access token>
bash examples/external.sh
```

It also needs `docker`, `jq` and the `synapse` CLI on your PATH. Read `examples/external.sh` for the commands, including why each `docker run` flag is there and why the container's output files must be deleted between tests.

It refuses to run if `external_example/` already exists, and writes its result to `external_example/results.csv`. Expect `GREY`, not `GREEN`: the file behind `syn://syn43716055` is actually a TXT file that the manifest deliberately mis-declares as TIFF, so `FileExtensionTest` and `LibTiffInfoTest` fail and `TiffTag306DateTimeTest` errors outright — see [Output](#output) for what each column means. `all_suites.json`, written partway through the script, holds the `status_reason` of every test if the CSV alone does not tell you enough, for example `new line.txt: Not a TIFF or MDI file, bad magic number 28267` for `LibTiffInfoTest`.

#### Internal Test in the py-dcqc Docker Image

Runs the same pipeline as [Internal Test by Hand](#internal-test-by-hand) inside the published image, so only `docker` is needed — no local Python install, and no environment to activate.

```bash
export SYNAPSE_AUTH_TOKEN=<your personal access token>
bash examples/docker.sh
```

Read `examples/docker.sh` for the commands. The `dcqc_docker` wrapper it defines carries the mount, working directory, user and `HOME` flags that let a container behave like a local install across every step; a bare `docker run` cannot do this, because a container gets a fresh filesystem and exits after one command. It refuses to run if `docker_example/` already exists, and writes its result to `docker_example/results.csv` — the same content as `internal_example/results.csv` above.

If `docker` needs `sudo` on your machine, pass the token through explicitly, because `sudo` strips the environment it does not know about:

```bash
sudo SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" bash examples/docker.sh
```

The script checks for the token before it makes any directory, so a plain `sudo bash examples/docker.sh` fails at once with that same reminder rather than part way through. Under `sudo`, `id -u` also reports `0`, so the container maps to `root` and the output files come back root-owned; add `--user "$SUDO_UID:$SUDO_GID"` to the wrapper in the script to keep them owned by you.

## Integration with nf-dcqc

Early versions of this package were developed to be used by its sibling, the [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) Nextflow workflow. The initial command-line interface was developed with nf-dcqc in mind, favoring smaller steps to enable parallelism in Nextflow.

# PyScaffold

This project has been set up using PyScaffold 4.3. For details and usage
information on PyScaffold see https://pyscaffold.org/.

```console
putup --name dcqc --markdown --github-actions --pre-commit --license Apache-2.0 py-dcqc
```
