# py-dcqc

<!--
[![ReadTheDocs](https://readthedocs.org/projects/dcqc/badge/?version=latest)](https://sage-bionetworks-workflows.github.io/dcqc/)
-->
[![PyPI-Server](https://img.shields.io/pypi/v/dcqc.svg)](https://pypi.org/project/dcqc/)
[![codecov](https://codecov.io/gh/Sage-Bionetworks-Workflows/py-dcqc/branch/main/graph/badge.svg?token=OCC4MOUG5P)](https://codecov.io/gh/Sage-Bionetworks-Workflows/py-dcqc)
[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](#pyscaffold)

> Python package for performing quality control (QC) for data coordination (DC)

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

## Installation

You can install py-dcqc directly from PyPI:

```bash
pip install 'dcqc[all]'
```

The `all` extra adds `rdflib`, which `JsonLdLoadTest` needs to parse JSON-LD files. Without it, that one test raises `ModuleNotFoundError` when you compute its status, while every other test continues to work. The published Docker image installs this extra. If you know you will never check JSON-LD files, plain `pip install dcqc` is enough.

For development installation from source:

```bash
git clone https://github.com/Sage-Bionetworks-Workflows/py-dcqc.git
cd py-dcqc
pip install -e '.[all]'
```

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

- Here is a single file target input file example

  | url               | file_type | md5_checksum                     |
  |-------------------|-----------|----------------------------------|
  | syn://syn41864974 | TXT       | 38b86a456d1f441008986c6f798d5ef9 |

- Here is an input file example with several targets. Every row becomes its own single-file target, so the rows are checked independently of one another.

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

**The order of the names inside a cell is not stable.** All four list columns come from Python sets, so the same input can give the same names in a different order on the next run. Compare the set of names, not the text of the cell, and do not use these cells in a byte comparison against an expected file.

## Example Usage

Three of the sections below are also runnable scripts, so that you can see a whole pipeline work before you read it step by step. All three take their input from `examples/`, write every artifact to a directory of their own, and need `SYNAPSE_AUTH_TOKEN` in your environment.

| Script | Section | Writes |
|---|---|---|
| `examples/internal.sh` | [Internal Test by Hand](#internal-test-by-hand) | `internal_example/results.csv` |
| `examples/external.sh` | [External Test by Hand](#external-test-by-hand) | `external_example/results.csv` |
| `examples/docker.sh` | [Internal Test in the py-dcqc Docker Image](#internal-test-in-the-py-dcqc-docker-image) | `docker_example/results.csv` |

`examples/docker.sh` needs only `docker`, because it runs `dcqc` in the published image. The other two need `dcqc` itself, so activate the project environment first with `source "$(pipenv --venv)/bin/activate"`.

### Basic File QC

Run QC on a single file:

```bash
dcqc qc-file examples/data.csv --file-type csv \
  --metadata '{"md5_checksum": "52f81b43ac7bde58d3c97184588fba07"}'
```

To run without a checksum, skip that test instead:

```bash
dcqc qc-file examples/data.csv --file-type csv --skipped-tests Md5ChecksumTest
```

### Internal Test by Hand

The commands below form one continuous pipeline. Each step consumes the files the previous step wrote, so run them in order. Start from the root of a clone, which is where `examples/internal_target.csv` sits. That manifest holds the single TXT row shown in [Input](#input), so every test in it is an internal one. The steps must run in this order, because each command validates the type of the JSON it is given.

This section needs `dcqc` installed in a virtual environment. The [Internal Test in the py-dcqc Docker Image](#internal-test-in-the-py-dcqc-docker-image) section below runs the same six commands in the published image instead, and needs no local install.

Steps 4 to 6 apply to a single target, while steps 3, 7 and 8 apply to the whole manifest. Every intermediate file name starts with the name of its target, so name the target in each glob. A bare `computed/*.json` in step 6 matches the tests of every target you have processed so far, and the command then stops with `ValueError: Not all tests refer to the same target`.

Every step after step 2 runs inside `internal_example/`, so all of the JSON stays in that one directory instead of in the root of your clone. This matches [External Test by Hand](#external-test-by-hand) below, which works the same way in `external_example/`.

All eight steps are also in `examples/internal.sh`, which runs them in order:

```bash
export SYNAPSE_AUTH_TOKEN=<your personal access token>
bash examples/internal.sh
```

Read the steps below to understand what it does, and to run them one at a time. The script stops if `internal_example/` already exists, because the `dcqc` commands refuse to write over their output.

1. Export a Synapse token, because every URL in the example manifest is a synapse URL:

   ```bash
   export SYNAPSE_AUTH_TOKEN=<your personal access token>
   ```

2. Make the working directory and enter it:

   ```bash
   mkdir -p internal_example
   cd internal_example
   ```

   The manifest is now the one path that points outside, as `../examples/internal_target.csv`.

3. Create targets from a CSV file. Each row becomes one target, numbered from `0001`:

   ```bash
   dcqc create-targets ../examples/internal_target.csv targets/
   # writes targets/target-0001.json, targets/target-0002.json, ...
   ```

   `create-targets` only converts the manifest into JSON; it runs no test. For each row it makes a `File` from the `url` column, keeps every other column as that file's metadata, and wraps the file in a target whose ID is the row number, padded to four digits. Relative URLs are resolved against the directory that holds the CSV file.

4. Create tests for one target. Each test becomes its own file, named after the target and the test:

   ```bash
   dcqc create-tests targets/target-0001.json tests/
   # writes tests/target-0001.Md5ChecksumTest.json, tests/target-0001.FileExtensionTest.json, ...
   ```

   `create-tests` writes one file for every test in the file type's suite. Give `--required-tests` to `create-suite` in step 6, not here, to select the tests that must pass for the suite to be GREEN. `create-tests` accepts the option, but it changes neither which files are written nor the required set that reaches the report, because that set is a property of the suite. The default required set is every tier-1 and tier-2 test.

5. Compute the status of each test. This is the step that *nf-dcqc* fans out, one call per test, and it is where the result of an external test enters the pipeline:

   ```bash
   mkdir -p computed suites
   for test_json in tests/target-0001.*.json; do
     dcqc compute-test "$test_json" "computed/$(basename "$test_json")" \
       || echo "not computed: $test_json"
   done
   ```

   `mkdir -p computed suites` creates both output directories in advance. The current code creates a missing parent itself, so this is not strictly needed, but an older `dcqc` raises `fs.errors.CreateFailed: root path '...' does not exist` the first time it writes into either one — `computed/` here, `suites/` in step 6.

   Run in this way, `compute-test` succeeds for internal tests only. For an external test it reads `std_out.txt`, `std_err.txt` and `exit_code.txt` from the current directory, and it stops with `FileNotFoundError` when those files are absent. The `|| echo` branch keeps the loop going and names the tests it could not compute. See [External Test by Hand](#external-test-by-hand) for how to produce those three files yourself.

6. Collect the computed tests of one target into a suite:

   ```bash
   dcqc create-suite suites/target-0001.json computed/target-0001.*.json
   ```

   `create-suite` computes any test in the list that is still `pending`, because serializing a suite calls `compute_status()`. Step 5 is therefore not required to get a status for an internal test. The glob matches only the files that step 5 wrote, so a test that step 5 could not compute is absent from the suite, and the suite status is derived from the remaining tests only. A TIFF suite built in this way reports GREEN while its external tests are still missing. Use *nf-dcqc* for a complete result, or [External Test by Hand](#external-test-by-hand) to fill in the missing tests one at a time first.

7. Combine every suite into a single JSON report. Repeat steps 4 to 6 for each target first, so that `suites/` holds one file per target:

   ```bash
   dcqc combine-suites all_suites.json suites/*.json
   ```

8. Create an output file that is your input file updated with the tests' results, then leave the directory:

   ```bash
   dcqc update-csv all_suites.json ../examples/internal_target.csv results.csv
   cd ..
   ```

   The final result is `internal_example/results.csv`: the input manifest with the five `dcqc_` columns appended, in the form shown in [Output](#output). The section below describes it.

   Every row of the input CSV must have a suite in `all_suites.json`, because the command looks each row up by its `url`. If you processed only some of the targets, it stops with a bare `KeyError` naming the first missing URL, for example `KeyError: 'a.txt'`.

   Each row is joined to its suite by the raw `url` value, which is a synapse URL here and therefore passes through unchanged. A manifest of relative local paths does not survive this join from another directory.


`internal_example/results.csv` is the end of the pipeline, and it is the only file you must read. It holds every column of `examples/internal_target.csv`, unchanged, plus the five columns that `update-csv` appends:

```csv
url,file_type,md5_checksum,dcqc_status,dcqc_required_tests,dcqc_skipped_tests,dcqc_failed_tests,dcqc_errored_tests
syn://syn41864974,TXT,38b86a456d1f441008986c6f798d5ef9,GREEN,"Md5ChecksumTest,FileExtensionTest",,,
```

One row of the manifest gives one row here, and the columns hold the status of that row's suite. The row above is GREEN: both required tests passed, and the other three lists are empty. The `dcqc_status` value alone is enough to accept or reject a file. Read the other four columns to find out why a row is not GREEN, and which test to look at.

Your `dcqc_required_tests` cell can read `"FileExtensionTest,Md5ChecksumTest"` instead. The order inside the four list columns is not stable between runs, as [Output](#output) explains. Only the set of names is meaningful.

### External Test by Hand

*nf-dcqc* is the supported way to run external tests, and the only practical way to run a manifest of them. The steps here do the same work by hand with `docker run`, and end in the same `results.csv` as the internal pipeline above.

The manifest is `examples/external_target.csv`, which holds the single TIFF row shown in [Input](#input), and a TIFF suite contains external tests. Steps 3, 4, 12, 13 and 14 are the same commands as the internal pipeline; the rest stand in for the work that *nf-dcqc* would do.

A TIFF target needs three container runs, one each for `LibTiffInfoTest`, `TiffDateTimeTest` and `TiffTag306DateTimeTest`. Steps 1 to 5 are done once for the target, steps 6 to 10 are repeated for one external test at a time, and steps 11 to 14 are done once at the end. The reason the three tests cannot share a directory is given after the steps.

Every step after step 2 runs inside `external_example/`, so the JSON, the downloaded file and the container output all stay in that one directory. `compute-test` reads the container output from the current directory and has no option that points it elsewhere, which is why you change directory once rather than write a prefix on every path.

All fourteen steps are also in `examples/external.sh`, which runs them in order and loops steps 6 to 10 over the three external tests:

```bash
export SYNAPSE_AUTH_TOKEN=<your personal access token>
bash examples/external.sh
```

It needs `docker` and `jq` on your PATH as well as `dcqc` and `synapse`. Read the steps below to understand what it does, and to run one external test at a time. The script stops if `external_example/` already exists, because the `dcqc` commands refuse to write over their output.

1. Export a Synapse token, because every URL in the example manifest is a synapse URL:

   ```bash
   export SYNAPSE_AUTH_TOKEN=<your personal access token>
   ```

2. Make the working directory and enter it:

   ```bash
   mkdir -p external_example
   cd external_example
   ```

   The manifest is now the one path that points outside, as `../examples/external_target.csv`.

3. Create targets from the CSV file:

   ```bash
   dcqc create-targets ../examples/external_target.csv targets/
   # writes targets/target-0001.json
   ```

4. Create tests for the target:

   ```bash
   dcqc create-tests targets/target-0001.json tests/
   # writes tests/target-0001.LibTiffInfoTest.json,
   #        tests/target-0001.TiffDateTimeTest.json, ...
   ```

   The suite of a TIFF file holds two internal tests as well, `Md5ChecksumTest` and `FileExtensionTest`. Only the three external tests need the container runs below; step 11 computes the internal two.

5. Download the file here, and create the two output directories. The generated command names the file by its bare filename and nothing else, so the file must sit in the directory you mount:

   ```bash
   synapse get syn43716055 --downloadLocation .
   mkdir -p computed suites
   ```

   The synID is the manifest URL without its `syn://` prefix, and `synapse` writes the file under the same name that the command uses. The `synapse` CLI is part of `synapseclient`, which `fs-synapse` installs, so it is already in the environment that holds `dcqc`.

   `mkdir -p computed suites` creates both output directories in advance. The current code creates a missing parent itself, so this is not strictly needed, but an older `dcqc` raises `fs.errors.CreateFailed: root path '...' does not exist` the first time it writes into either one — `computed/` in step 9, `suites/` in step 12.

6. Write the process descriptor:

   ```bash
   dcqc create-process tests/target-0001.LibTiffInfoTest.json process.json
   ```

   It holds four keys: `container`, `command`, `cpus` and `memory`. `create-process` also makes its own copy of the file in a temporary directory of the form `/tmp/dcqc-staged-*/`, because it calls `File.stage()` to learn the filename. That copy is outside `external_example/` and the container never sees it; the one from step 5 is the one it reads.

7. Read the container and the command out of it:

   ```bash
   container=$(jq -er .container process.json)
   process_command=$(jq -er .command process.json)
   ```

8. Run the container, keeping all three outputs. `$PWD` is `external_example/`, so that is what gets mounted:

   ```bash
   docker run --rm -v "$PWD":/data:ro -w /data "$container" sh -c "$process_command" \
     > std_out.txt 2> std_err.txt
   echo $? > exit_code.txt
   ```

   The mount is read-only. All three TIFF commands only read the file, and `std_out.txt`, `std_err.txt` and `exit_code.txt` are written by the shell redirection above, on the host, not inside the container. Drop `:ro` if you add an external test whose tool writes an output file of its own.

   `sh -c` is required, not a convenience. Two of the three TIFF commands pipe `tifftools` into `jq` and `grep`, and the descriptor stores the command as one space-joined string, so without a shell the `|` reaches the tool as a literal argument.

   Run `docker pull "$container"` first. Docker writes its pull progress to standard error, so on a first run that progress lands in `std_err.txt`, and `compute-test` reports it as the `status_reason` of a failing test.

9. Compute the status. `compute-test` reads the three output files from the current directory, so run it here:

   ```bash
   dcqc compute-test tests/target-0001.LibTiffInfoTest.json \
     computed/target-0001.LibTiffInfoTest.json
   ```

10. Delete `std_out.txt`, `std_err.txt`, `exit_code.txt` and `process.json`, then return to step 6 for the next test. `create-process` refuses to write over an existing file, so leaving `process.json` in place stops the next pass with `FileExistsError: URL (process.json) already exists.`

    Go on to step 11 when `computed/` holds all three external tests.

11. Compute the two internal tests of the suite. They need no container, and step 5 has already put the file in place:

    ```bash
    for test_json in tests/target-0001.Md5ChecksumTest.json \
                     tests/target-0001.FileExtensionTest.json; do
      dcqc compute-test "$test_json" "computed/$(basename "$test_json")"
    done
    ```

    Name these two files, rather than globbing `tests/*.json`. A glob puts the three external tests through `compute-test` a second time, and each one stops with `FileNotFoundError`, because step 10 deleted the container output that it reads.

12. Collect all five computed tests into a suite:

    ```bash
    dcqc create-suite suites/target-0001.json computed/target-0001.*.json
    ```

    With all three external tests in `computed/`, together with the two internal tests from step 11, this builds a suite that holds all five tests of the TIFF suite, and the status it reports is a real one. Any test missing from `computed/` is missing from the suite as well, and the status is then derived from the remaining tests only. This is why step 10 sends you back for the other two container runs first.

13. Combine every suite into a single JSON report. This manifest holds one row, so `suites/` holds one file:

    ```bash
    dcqc combine-suites all_suites.json suites/*.json
    ```

14. Write the results CSV, then leave the directory:

    ```bash
    dcqc update-csv all_suites.json ../examples/external_target.csv results.csv
    cd ..
    ```

    The final result is `external_example/results.csv`: the input manifest with the five `dcqc_` columns appended, in the form shown in [Output](#output). The section below describes it.

    Each row is joined to its suite by the raw `url` value, which is a synapse URL here and therefore passes through unchanged. A manifest of relative local paths does not survive this join from another directory.


`external_example/results.csv` is the end of the pipeline, and it is the only file you must read. It holds every column of `examples/external_target.csv`, unchanged, plus the five columns that `update-csv` appends:

```csv
url,file_type,md5_checksum,dcqc_status,dcqc_required_tests,dcqc_skipped_tests,dcqc_failed_tests,dcqc_errored_tests
syn://syn43716055,TIFF,38b86a456d1f441008986c6f798d5ef9,GREY,"Md5ChecksumTest,FileExtensionTest,LibTiffInfoTest",,"FileExtensionTest,LibTiffInfoTest",TiffTag306DateTimeTest
```

GREY is the expected result for this manifest, and not a sign that a step went wrong. The file behind `syn://syn43716055` is a text file that the manifest declares as TIFF, so the TIFF tests cannot succeed on it: `FileExtensionTest` and `LibTiffInfoTest` both failed, and `TiffTag306DateTimeTest` gave no result at all. One errored test makes the whole suite GREY, and GREY takes precedence over RED, so the two failed required tests do not show in `dcqc_status`. Read `dcqc_failed_tests` and `dcqc_errored_tests` to see them.

`TiffDateTimeTest` passed, so it is in none of the lists, and it is absent from `dcqc_required_tests` because it is a tier-4 test.

The three names in `dcqc_required_tests`, and the two in `dcqc_failed_tests`, can come out in a different order on your run. The order inside the four list columns is not stable, as [Output](#output) explains. Only the set of names is meaningful.

The CSV names the tests but not the reason each one gave. Keep `all_suites.json` from step 13 for that, because it holds the `status_reason` of every test, for example `new line.txt: Not a TIFF or MDI file, bad magic number 28267` for `LibTiffInfoTest`.

### Internal Test in the py-dcqc Docker Image

This section runs the pipeline of [Internal Test by Hand](#internal-test-by-hand) in the published image, with no local Python install. It takes the same manifest, runs the same six commands and ends in the same GREEN row, so read it as a second way to invoke that pipeline rather than as a different one. Only `docker` is needed on your PATH, not `dcqc`.

Every step after step 3 runs inside `docker_example/`, which is a directory of its own so that this pipeline can run beside `internal_example/`. Start from the root of a clone, as before.

A bare `docker run` in front of each command does not work, because a container gets a fresh filesystem and exits after one command: step 4 would write `targets/target-0001.json` inside the container, and that file would be gone before step 5 could read it. Every step therefore needs the same flags, which step 3 puts in a wrapper.

Running in the image does not change which tests can complete: external tests still fail at `compute-test`, because the image holds `dcqc` and not the tool containers that the external tests call.

All nine steps are also in `examples/docker.sh`, which runs them in order:

```bash
export SYNAPSE_AUTH_TOKEN=<your personal access token>
bash examples/docker.sh
```

It needs `docker` on your PATH, and nothing else; no environment has to be activated, because `dcqc` runs in the image. Read the steps below to understand what it does, and to run them one at a time. The script stops if `docker_example/` already exists, because the `dcqc` commands refuse to write over their output.

If `docker` needs `sudo` on your machine, pass the token through explicitly, because `sudo` strips the environment it does not know about:

```bash
sudo SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" bash examples/docker.sh
```

Plain `sudo bash examples/docker.sh` reaches the container with the variable unset, and every `syn://` lookup then stops with `SynapseNoCredentialsError: No valid authentication credentials provided.` The script checks for the token before it makes any directory, so this fails at once rather than part way through.

Under `sudo`, `id -u` reports `0`, so the `--user` flag of step 3 maps the container to `root` and the output is root-owned again. Add `--user "$SUDO_UID:$SUDO_GID"` to the wrapper to keep the files owned by you.

1. Export a Synapse token, because every URL in the example manifest is a synapse URL:

   ```bash
   export SYNAPSE_AUTH_TOKEN=<your personal access token>
   ```

2. Make the working directory and enter it:

   ```bash
   mkdir -p docker_example
   cd docker_example
   ```

   The manifest is now the one path that points outside, as `../examples/internal_target.csv`.

3. Define the wrapper once. The six commands below are then identical to the ones in the virtual-environment steps:

   ```bash
   dcqc_docker() {
     docker run --rm \
       -v "$PWD/..":/data -w /data/docker_example \
       --user "$(id -u):$(id -g)" \
       -e HOME=/data/docker_example \
       -e SYNAPSE_AUTH_TOKEN \
       ghcr.io/sage-bionetworks-workflows/py-dcqc:main \
       dcqc "$@"
   }
   ```

   `-v "$PWD/..":/data` mounts the root of your clone into the container, so the intermediate JSON is written to the host and survives between steps. The clone root is mounted rather than `docker_example/` itself, because the manifest at `../examples/internal_target.csv` sits outside `docker_example/` and a container sees nothing above its mount.

   `-w /data/docker_example` makes `docker_example/` the working directory inside the container, so every path is written exactly as it is in the steps below. Without this, relative paths resolve against the image's own `WORKDIR` of `/usr/src/app`, and step 4 stops with `FileNotFoundError: [Errno 2] No such file or directory: '../examples/internal_target.csv'` before it writes anything.

   `-e SYNAPSE_AUTH_TOKEN` forwards the token from step 1, which the example manifest needs to read its `syn://` URLs. It forwards the variable as your shell holds it, so the token must be in the environment that runs `docker`, not only in the one that exported it: under `sudo`, write `sudo SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" docker run ...`, or the container gets an empty value and step 6 stops with `SynapseNoCredentialsError`. Drop the flag if your manifest points at files inside the mounted directory. The image's `CMD` is only an `import dcqc` smoke test, so a real `dcqc ...` command must always be given, as it is on the last line.

   `--user "$(id -u):$(id -g)"` runs the container as you rather than as `root`. Without it, `targets/`, `tests/` and `results.csv` appear on the host owned by `root`, and you then need `sudo` to remove `docker_example/` before you can run the pipeline a second time.

   `-e HOME=/data/docker_example` gives that user a writable home directory. The mapped user has no home in the image, and `synapseclient` then stops with `PermissionError: [Errno 13] Permission denied: '/.synapseCache'`. Pointing `HOME` at the working directory keeps the cache inside `docker_example/`, which is gitignored. Drop this flag if your manifest holds no `syn://` URLs.

   Run `docker pull ghcr.io/sage-bionetworks-workflows/py-dcqc:main` now, as the script does, to keep the pull progress of a first run out of the output of step 4.

4. Create targets from the CSV file:

   ```bash
   dcqc_docker create-targets ../examples/internal_target.csv targets/
   # writes targets/target-0001.json
   ```

5. Create tests for the target:

   ```bash
   dcqc_docker create-tests targets/target-0001.json tests/
   # writes tests/target-0001.Md5ChecksumTest.json,
   #        tests/target-0001.FileExtensionTest.json
   ```

6. Compute the status of each test:

   ```bash
   mkdir -p computed suites
   for test_json in tests/target-0001.*.json; do
     dcqc_docker compute-test "$test_json" "computed/$(basename "$test_json")" \
       || echo "not computed: $test_json"
   done
   ```

   The glob is expanded by your shell against the host directory, not by the container, which is why the mount must be in place from step 4 onward.

   `mkdir -p computed suites` creates both output directories in advance. The current code creates a missing parent directory itself, so `suites/` is not strictly needed with the `main` image, but an older image raises `fs.errors.CreateFailed: root path '/data/docker_example/suites' does not exist` at step 7. Creating it costs nothing and keeps the pipeline working on any tag.

7. Collect the computed tests into a suite:

   ```bash
   dcqc_docker create-suite suites/target-0001.json computed/target-0001.*.json
   ```

8. Combine every suite into a single JSON report:

   ```bash
   dcqc_docker combine-suites all_suites.json suites/*.json
   ```

9. Write the results CSV, then leave the directory:

   ```bash
   dcqc_docker update-csv all_suites.json ../examples/internal_target.csv results.csv
   cd ..
   ```

`docker_example/results.csv` is the end of the pipeline, and it is the same file that the virtual-environment run writes to `internal_example/results.csv`:

```csv
url,file_type,md5_checksum,dcqc_status,dcqc_required_tests,dcqc_skipped_tests,dcqc_failed_tests,dcqc_errored_tests
syn://syn41864974,TXT,38b86a456d1f441008986c6f798d5ef9,GREEN,"Md5ChecksumTest,FileExtensionTest",,,
```

The order inside `dcqc_required_tests` is not stable here either, as [Output](#output) explains.

The files themselves are owned by you, not by `root`, because of the `--user` flag in the wrapper of step 3. Drop that flag and the image runs as `root`, which leaves `targets/`, `tests/` and `results.csv` owned by `root` on the host and makes `rm -rf docker_example` need `sudo` before a second run.

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
