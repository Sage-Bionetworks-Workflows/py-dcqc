# Architecture

This document covers how to add a new file type, a new suite, or a new test
(internal or external) to `dcqc`. For everything else — environment setup,
branching, submitting a PR, adding a dependency, releasing — see
[CONTRIBUTING.md](CONTRIBUTING.md).

Before you start, read the [Core Concepts] section of the `README.md`. It
describes the four objects that move through the whole system (`File`,
`Target`, `Test` and `Suite`), the difference between internal and external
tests, and the order of the command line pipeline.

## Contributing New File Types

If you want to test a completely new file type, you must add that type first. A
new file type needs two things: a `FileType` object in `src/dcqc/file.py`, and a
suite class in `src/dcqc/suites/suites.py` that claims it. Read the
[Files and FileTypes] section of the `README.md` first. It describes what a file
type is and lists the types that exist today.

Do these two steps.

1. Register the file type in `src/dcqc/file.py`. Add one line to the block of
   `FileType(...)` statements at the end of the module. Constructing the object
   is the registration; there is no separate registry call:

   ```python
   FileType("MY-TYPE", (".mytype", ".mytype.gz"), "format_1234")
   ```

   The three arguments are the name, the valid extensions and the [EDAM]
   identifier. Note these points:

   - **Keep the trailing comma if the type has only one extension.**
     `(".mytype")` is a string, not a tuple, and `FileType` calls `tuple()` on
     it. The result is one element per character, and `FileExtensionTest` then
     accepts any file name that ends in one of those characters. Write
     `(".mytype",)`.
   - `FileExtensionTest` matches with `str.endswith`, so write compound
     extensions in full, as `OME-TIFF` and `FASTQ` do (`.ome.tif`,
     `.fastq.gz`).
   - The name must be unique. Names are compared in lower case, and a duplicate
     raises a `ValueError` at import time.
   - Do not give the file type the name of a `Test`, `Suite` or `Target` class.
     `JsonParser.get_class` in `src/dcqc/parsers.py` looks at those classes
     before it looks at the file type names, so the class wins and
     deserialization returns the wrong object.
   - The EDAM identifier is optional, but give one if the format has one.

2. Add a suite class that claims the type in `src/dcqc/suites/suites.py`. See
   [Contributing New Suites](#contributing-new-suites) for the details:


## Contributing New Suites

A suite connects one file type to the tests that DCQC runs on files of that type.
There is one suite class for each file type. All of them are in
`src/dcqc/suites/suites.py`.

Do these two steps.

1. Add the class to `src/dcqc/suites/suites.py`. Give it a docstring, the file
   type it claims, and the tests that are new at this level:

   ```python
   class MyTypeSuite(FileSuite):
       """Suite class for MY-TYPE files."""

       file_type = FileType.get_file_type("MY-TYPE")
       add_tests = (tests.MyNewTest,)
   ```

   Note these points:

   - Subclass `FileSuite` for a new format. Subclass a more specific suite if
     your type is a subtype of an existing format, as `H5ADSuite(HDF5Suite)`,
     `OmeTiffSuite(TiffSuite)` and `JsonLdSuite(JsonSuite)` do.
   - `add_tests` is additive along the class hierarchy. It does not replace the
     list of the parent class. `list_test_classes` unions the `add_tests` of
     every class in the method resolution order, so a subclass also runs the
     tests of its parents. Inheritance is the only way to share tests between
     suites.
   - Two suites must not claim the same file type. The registry is a dictionary
     keyed on the file type name, so the second class replaces the first one with
     no warning.


## Contributing New Tests

A new test needs two things: a test class, and registration. If you write the class but do not register it, nothing tells you.

### Internal and External Tests

There are two kinds of test. Before you write a test, decide which kind it is. The difference is where the business logic of the test runs.

- An **internal test** runs its business logic in Python, in `py-dcqc`. It subclasses `InternalBaseTest` and implements `compute_status`. `dcqc compute-test` runs the test and gets the result directly. Examples are `Md5ChecksumTest`, `FileExtensionTest` and `PairedFastqParityTest`.
- An **external test** runs its business logic in a Docker container. It subclasses `ExternalBaseTest` and implements `generate_process`. `py-dcqc` does not run the container. `dcqc create-process` writes a `Process` object that describes the container and the command. The [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) workflow runs that command. Then `dcqc compute-test` reads the exit code, the standard output and the standard error of the command, and it compares the exit code with `pass_code` and `fail_code`. Examples are `LibTiffInfoTest` and `BioFormatsInfoTest`.

Use an internal test if you can write the logic in Python with the dependencies of `py-dcqc`. Use an external test if the check needs a tool that is not a Python package, such as `tiffinfo` or Bio-Formats. External tests are more difficult to write, test and debug.

### What Makes a Good Test

A good test, internal or external, has these properties:

- **It checks one thing.** One test gives one status. A test that does many checks gives one reason for many problems, and a user cannot see which check failed. Make one test for each check.
- **It is deterministic.** The same file gives the same status each time, on each machine. It does not depend on the time, on random values, or on the network.
- **It needs only the file.** It does not download data, call a web service, or need credentials when it runs.
- **Its failure reason is short and specific.** One or two lines that name the problem. A user reads the reason in `suites.json`, and a long reason makes that report hard to read.
- **Its output contains no sensitive data.** The reason goes into `suites.json`, and the metrics go into `suites.json` and the output CSV.

### Registering a New Test

Do these two steps for every new test, internal or external.

1. Add an import line for your module to `src/dcqc/tests/__init__.py`, in alphabetical order with the lines that are there:

   ```python
   from dcqc.tests.my_new_test import MyNewTest
   ```

   These imports look unused, but they are the registration. Do not remove them.

2. Add your class to the `add_tests` tuple of one or more suites in `src/dcqc/suites/suites.py`:

   ```python
   class TiffSuite(FileSuite):
       """Suite class for TIFF files."""

       file_type = FileType.get_file_type("TIFF")
       add_tests = (
           tests.LibTiffInfoTest,
           tests.TiffDateTimeTest,
           tests.TiffTag306DateTimeTest,
           tests.MyNewTest,
       )
   ```

### Contributing Internal Tests

Before you write an internal test, make sure that it is the correct kind. See [Internal and External Tests].

When contributing an internal test be sure to do the following:

1. Follow the [Code Contributions](CONTRIBUTING.md#code-contributions) steps in CONTRIBUTING.md to set up `py-dcqc` and create your contribution.

2. Add a new module at `src/dcqc/tests/<snake_case>_test.py`, with one test class in it. These modules are package code, not unit tests, although their names end in `_test.py`. The unit tests are in the `tests/` directory at the root of the repository.

3. Subclass `InternalBaseTest`, and import it from `dcqc.tests.base_test`. The `dcqc.tests` package does not re-export it:

   ```python
   from dcqc.tests.base_test import InternalBaseTest


   class MyNewTest(InternalBaseTest):
       """Tests that ..."""
   ```

   The other names that you need, such as `TestStatus`, `TestTier` and `Process`, also come from `dcqc.tests.base_test`. `SingleTarget` and `PairedTarget` come from `dcqc.target`.

4. Include a class docstring that describes the purpose of the test. The
   docstring goes into the Sphinx API documentation. `dcqc list-tests` does not
   show it: that command prints only the file type, the EDAM identifier, the
   test name, the tier and the test type.

5. Include the following class attributes:

   - `tier`: A `TestTier` enum describing the complexity of the validation. Valid `tier` values include:
     - `FILE_INTEGRITY`: Validates basic file integrity and availability. Requires additional information for MD5 verification, file extension validation, format-specific checks, and decompression verification.
     - `INTERNAL_CONFORMANCE`: Ensures file internal consistency and format compliance. Only needs the files themselves and their format specification for validation against schema and internal metadata checks.
     - `EXTERNAL_CONFORMANCE`: Verifies file features against separately submitted metadata. Uses additional information while remaining objective/quantitative for validating channel counts, file sizes, nomenclature, and required companion files.
     - `SUBJECTIVE_CONFORMANCE`: Evaluates files using qualitative criteria that may need expert review. Uses metrics, heuristics, or models for tasks like sample swap detection, PHI detection, and outlier identification.
   - `target`: The target class that the test will be applied to. This value will be `SingleTarget` for individual files and `PairedTarget` for paired files.

6. Implement the major logic of the test in the `compute_status` method. This should include a condition for returning a `status` of `TestStatus.PASS` when the test conditions are met and `TestStatus.FAIL` when they are not.
   - For failing cases be sure to include a line setting the class' `status_reason` to a helpful string that will tell users why the test failed before returning the `status`.
   - To report extra values that the test computes (for example, a count or a size), set them in `self.metrics`. They must be JSON-serializable. They appear in `suites.json` and in the `dcqc_metrics` column of the output CSV.
   - Call `self.target.file.stage()` to get a local `Path` to the file. This works for remote URLs, such as `syn://`, as well as local files.

7. Register the test with the two steps in the "Registering a New Test" section above. Without them the test never runs.

8. Add a unit test for your class to `tests/test_internal_tests.py`.

### Contributing External Tests

This section tells you how to contribute a DCQC external test. It covers the Python side (the `ExternalBaseTest` subclass, its registration, and its unit tests) and the Docker image (the `Dockerfile`, the entry file, the inputs that the image receives, and the exit codes that it must return).

First, follow the [Code Contributions](CONTRIBUTING.md#code-contributions) steps in CONTRIBUTING.md to set up `py-dcqc` and create your contribution.

Before you make an image, make sure that you need an external test. See [Internal and External Tests] for how to choose between the two kinds.

#### How DCQC Runs an External Test

`py-dcqc` does not run the container. It only describes it. The [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) workflow runs it. Each external test goes through these steps:

1. `dcqc create-process` calls `generate_process()` on the test. That method stages the file and returns a `Process` with four keys: `container`, `command`, `cpus` and `memory`.
2. nf-dcqc links the staged file into a new task directory, and starts `container` with that directory as the working directory.
3. nf-dcqc runs `command` in bash and keeps three outputs in the task directory. The `RUN_PROCESS` step in `modules/local/run_process.nf` does this:

   ```bash
   ( (${command}) > "std_out.txt" 2> "std_err.txt"; echo $? > "exit_code.txt" ) || true
   ```

   The command makes these three files:

   - `exit_code.txt` holds one integer: the exit code of `command`. DCQC reads it for every test, and it is the only file that selects the status. If the file does not contain an integer, `compute-test` stops with an error.
   - `std_out.txt` holds the stdout of `command`. The base class reads it only for a failed test whose class sets `failure_reason_location = "std_out"`. A test class can also read metrics from it, as the example in [Creating the Test Class](#creating-the-test-class) does.
   - `std_err.txt` holds the stderr of `command`. DCQC reads it for a failed test whose class sets `failure_reason_location = "std_err"`, and for every test with the status `error`.

   All three files must exist for every test, even if DCQC does not read a file for that status. If one of them is missing, `compute-test` stops with a `FileNotFoundError` before it reads the exit code. See `_find_process_outputs` in `src/dcqc/tests/base_test.py`.

   Thus Nextflow does not decide the result of the test. It only runs the command and keeps the three files. DCQC decides the result in step 4.

4. `dcqc compute-test` reads `exit_code.txt` and compares it with the `pass_code` and `fail_code` of the test. It copies the text of `std_out.txt` or `std_err.txt` into `status_reason`.

In step 4, the exit code alone selects the status, and the status selects the stream that DCQC copies into `status_reason`:

- For `passed`, DCQC copies no stream. `status_reason` stays empty.
- For `failed`, DCQC copies the stream that `failure_reason_location` names. Each test class sets this value, because some tools write the reason for a failure to stdout and other tools write it to stderr.
- For `error`, DCQC always copies `std_err.txt`. It does not read `failure_reason_location`. An error is a result that is not expected, such as a crash or a file that the tool cannot read, so DCQC cannot know where the tool writes the message. It uses stderr, because that is the usual stream for errors.

Thus the entry file must write its error messages to stderr, for example with `print(message, file=sys.stderr)` in Python or `echo "$message" >&2` in bash. If it writes them to stdout, the status is `error`, but `status_reason` does not tell the user why.

The exit code must also be correct. If a crash returns the same code as `fail_code`, DCQC gives the status `failed`, not `error`, and it reads the reason from `failure_reason_location`, not from stderr. The entry file must use one code for a failed check and a different code for an error. See [Return Codes](#return-codes).

Thus the image has one job: run a command on one file, write a reason, and exit with the correct code. Everything that follows comes from these four steps.

#### Creating the Test Class

The test class tells DCQC which image to use, which command to run, and how to read the exit code.

Put the class in a new module at `src/dcqc/tests/<snake_case>_test.py`, with one test class in it. These modules are package code, not unit tests, although their names end in `_test.py`. Note these points:

- **Import `ExternalBaseTest` from `dcqc.tests.base_test`.** The `dcqc.tests` package does not re-export it. `Process`, `TestStatus` and `TestTier` also come from `dcqc.tests.base_test`. `SingleTarget` and `PairedTarget` come from `dcqc.target`.
- **Give the class a docstring that tells the purpose of the test.** The docstring goes into the Sphinx API documentation. `dcqc list-tests` does not show it: that command prints only the file type, the EDAM identifier, the test name, the tier and the test type.
- **Set `tier` to a `TestTier` value.** The values are `FILE_INTEGRITY`, `INTERNAL_CONFORMANCE`, `EXTERNAL_CONFORMANCE` and `SUBJECTIVE_CONFORMANCE`. See [Contributing Internal Tests] for the meaning of each tier.
- **Set `target` to `SingleTarget`.**
- **Set `pass_code` and `fail_code`.** These are the exit codes of the command for a passed test and for a failed test. See [Return Codes](#return-codes).
- **Set `failure_reason_location` to `"std_out"` or `"std_err"`.** This is the stream that holds the reason for a failure. Any other value raises a `KeyError`, but only when a test fails, so a test on good files does not find the mistake.

The class sets only two exit codes, `pass_code` and `fail_code`. There is no error code. DCQC gives the status `error` to every other exit code, for example 2 from the entry file, 127 when the command is not found, or 137 when the container is killed. See [How DCQC Runs an External Test](#how-dcqc-runs-an-external-test) for the stream that DCQC reads for each status.

The class can also record metrics, as an internal test such as `Md5ChecksumTest` does. The base class does not read metrics from the container, so the metrics of an external test stay `{}` unless the class overrides `compute_status()`. The example below uses stdout to carry the metrics as one JSON object. nf-dcqc already keeps `std_out.txt` for every test, so this needs no change to nf-dcqc. To keep stdout for JSON only, the class sets `failure_reason_location = "std_err"`. The exit code still tells a failure from an error.

```python
import json

from dcqc.target import SingleTarget
from dcqc.tests.base_test import ExternalBaseTest, Process, TestStatus, TestTier


class MyTypeValidatorTest(ExternalBaseTest):
    """Tests if a file is a valid MY-TYPE file."""

    tier = TestTier.INTERNAL_CONFORMANCE
    pass_code = 0
    fail_code = 1
    failure_reason_location = "std_err"
    target: SingleTarget

    def generate_process(self) -> Process:
        path = self.target.file.stage()

        command_args = [
            "validate.py",
            f"'{path.name}'",
        ]
        process = Process(
            container="ghcr.io/sage-bionetworks-workflows/mytype-validator:0.1.0",
            command_args=command_args,
        )
        return process

    def compute_status(self) -> TestStatus:
        outputs = self._find_process_outputs()
        status = self._interpret_process_outputs(outputs)
        if status in (TestStatus.PASS, TestStatus.FAIL):
            text = outputs["std_out"].read_text().strip()
            if text:
                try:
                    metrics = json.loads(text)
                except json.JSONDecodeError:
                    metrics = None
                if not isinstance(metrics, dict):
                    reason = "Tool wrote output that is not a JSON object"
                    std_err = outputs["std_err"].read_text()
                    self.status_reason = f"{reason}\n{std_err}" if std_err else reason
                    return TestStatus.ERROR
                self.metrics = metrics
        return status
```

The class reads the metrics only for `passed` and `failed`. After an error, stdout can hold a part of the output, so the class does not read it. If stdout is not a JSON object, the status becomes `error`, because DCQC cannot trust the result of the tool. The class adds the text of stderr to `status_reason`, so that a user does not lose the failure reason. DCQC writes the metrics to `suites.json`, and to the `dcqc_metrics` column of the output CSV under the name of the test.

The example calls `_find_process_outputs()` and `_interpret_process_outputs()`. These are private methods of `ExternalTestMixin` in `src/dcqc/tests/base_test.py`. They are not a stable API. If you change their names or signatures, also update this example and every test class that overrides `compute_status()`.

##### Registering the Test Class

Register the class with the two steps in [Registering a New Test]. Without them the test never runs, and nothing tells you.

##### Unit Testing the Test Class

Add a unit test for your class to `tests/test_external_tests.py`. The business logic is in the container, so a unit test can check only two things: the `Process` that `generate_process()` returns, and the status that the class gives to each exit code. If the class overrides `compute_status()`, as the example does, also test that it reads the metrics, and that stdout that is not a JSON object gives the status `error`. To test the container itself, see [Testing the Image](#testing-the-image).

#### Creating the Dockerfile

Use this `Dockerfile` as a start point. It installs a Python validator, but the same rules apply to a tool in any language.

```dockerfile
FROM python:3.12-slim

# nf-dcqc runs the command with /bin/bash, and uses ps to collect task
# metrics. The slim image has bash but not ps.
RUN apt-get update \
    && apt-get install -y --no-install-recommends procps \
    && rm -rf /var/lib/apt/lists/*

# The entry file. Put it on the PATH and make it executable.
COPY validate.py /usr/local/bin/validate.py
RUN chmod 0755 /usr/local/bin/validate.py

# nf-dcqc runs the container as the user who runs the workflow, not as root.
# That user has no home directory in the image. Libraries that write config
# and cache files under HOME fail if it is not writable, so point HOME at a
# directory that all users can write to.
ENV HOME=/tmp

# Python writes .pyc files into __pycache__ directories in the image. The
# user cannot write there, and Singularity images are read-only. Stop Python
# from writing them, so that the tool writes nothing into the image.
ENV PYTHONDONTWRITEBYTECODE=1

# Do not set an ENTRYPOINT or a CMD. See the rules below.
```

Obey these rules:

- **Include `/bin/bash`.** The nf-dcqc `nextflow.config` sets `process.shell = ['/bin/bash', '-euo', 'pipefail']`. An image without bash, such as a plain Alpine image, cannot run.
- **Include `ps`.** Nextflow uses `ps` to collect task metrics, such as CPU and memory use. Without it, the test still runs, but the metrics are lost. On Debian-based images, install the `procps` package.
- **Do not set an `ENTRYPOINT` or a `CMD`.** The workflow supplies the full command. An entrypoint puts its own program in front of that command. If your base image sets one, clear it with `ENTRYPOINT []`. A `CMD` has no effect, because every run overrides it.
- **Do not hard-code a working directory.** nf-dcqc starts each container with `-w <task directory>`, and this replaces any `WORKDIR` in the image. Each run has a new task directory, so the path is different each time. The input file is in that directory, and the command gives the tool only the file name, such as `'file.mytype'`, with no directory. Thus the tool must open the name that it receives, relative to the current directory. Do not add a fixed directory, such as `/data`, to the name, and do not change directory before the tool opens the file.
- **Let any user run the tool.** The nf-dcqc `docker` and `arm` profiles pass `-u $(id -u):$(id -g)`, and Singularity runs the container as the calling user by default. Thus the user ID is not known when you build the image. Install files so that all users can read and execute them. Send every cache and temporary file to a directory that all users can write to, such as `/tmp`. Libraries such as matplotlib and numba write a cache under `HOME` by default, and they fail if `HOME` is not writable.
- **Pin the tool version and tag the image with a version.** Pin the tool version in the `Dockerfile`, and use a tag such as `0.1.1` in `generate_process()`, not `latest`. Then a QC result can always be traced to one version of the tool.
- **Put all the reference data into the image.** The tool must not download data when it runs. See [What Makes a Good Test].
- **Keep the image small.** nf-dcqc pulls it for each run on a new machine. Use a slim base image, remove package caches, and install only what the tool needs at run time.

Publish the image to a public registry that nf-dcqc can pull from. The existing tool images are in `quay.io/sagebionetworks` and `ghcr.io/sage-bionetworks-workflows`.

#### Creating the Entry File

The entry file is the program that the command calls. If an existing tool already reads a file and returns a useful exit code, you do not need an entry file. Write one when you must change the exit codes or the output of a tool, or when the check is your own code.

Use a known tool for the format, if one exists. A validator from the format maintainers, such as `tiffinfo` for TIFF or Bio-Formats for OME-TIFF, is better than new code. Write your own entry file around it only to fix the exit codes or the output.

This entry file obeys every rule in this section:

```python
#!/usr/bin/env python3
"""Check that a file is a valid MY-TYPE file.

Exit codes:
    0: The file is valid.
    1: The file is not valid. The reason is on standard error.
    2: The tool could not check the file. The reason is on standard error.

Standard output holds only the metrics, as one JSON object.
"""

import argparse
import json
import os
import sys

PASS = 0
FAIL = 1
ERROR = 2


# Replace the body of this function with your check. Put the metrics in a
# dict that json.dumps can write.
def check(path: str) -> tuple[list[str], dict[str, int | str]]:
    """Example check: test that a file starts with the 8-byte HDF5 signature.

    Replace this check, and this docstring, with the check for your
    format. The check reads only the first 8 bytes of the file and
    compares them with the HDF5 format signature. It also records the
    size of the file as a metric.

    Args:
        path: The path of the file to check, relative to the current
            directory.

    Returns:
        A tuple of two items. The first item is a list of problems, one
        string for each problem that the check found. An empty list means
        that the file is valid. The second item is a dict of metrics that
        json.dumps can write. It has one key, size_bytes, which is the
        size of the file in bytes.
    """

    # Record the metrics first, so that a failed file also reports them.
    metrics = {"size_bytes": os.path.getsize(path)}
    problems = []

    # Replace this check with your own. Add one string to problems for each
    # problem that you find.
    expected = b"\x89HDF\r\n\x1a\n"
    with open(path, "rb") as file:
        header = file.read(len(expected))
    if header != expected:
        problems.append("file does not start with the HDF5 signature")

    return problems, metrics


def main() -> int:
    """Run the check on one file and select the exit code.

    The function reads the file path from the command line and runs
    check() on it.

    The function dumps the metrics dict to standard output as one JSON
    object, with json.dumps. It does this for a pass and for a failure,
    before it examines the problems. It writes nothing to standard output
    if the metrics dict is empty or if check() raised an exception.

    The function writes the problems to standard error, one line for each
    problem, and each line starts with the file path. DCQC copies this
    text into status_reason when the test fails. If check() raises an
    exception, the function writes one line with the reason for the error
    to standard error instead. It writes nothing to standard error for a
    pass.

    Returns:
        The exit code for the process. PASS (0) means that the file is
        valid. FAIL (1) means that check() found one or more problems.
        ERROR (2) means that check() raised an exception, so the check
        did not complete.
    """
    parser = argparse.ArgumentParser(description="Validate a MY-TYPE file.")
    parser.add_argument("path", help="File to validate")
    args = parser.parse_args()

    # Catch every exception. An exception that is not caught exits with code
    # 1, which is FAIL, so a crash would look like an invalid file.
    try:
        problems, metrics = check(args.path)
        # Serialize here, so that a metric that is not a JSON type is an
        # error, not a failure.
        metrics_text = json.dumps(metrics) if metrics else ""
    except Exception as error:
        # The check did not complete. This is an error, not a failure.
        print(f"{args.path}: cannot check file: {error}", file=sys.stderr)
        return ERROR

    # Remove this if the test records no metrics.
    if metrics_text:
        print(metrics_text)

    if problems:
        for problem in problems:
            print(f"{args.path}: {problem}", file=sys.stderr)
        return FAIL

    return PASS


if __name__ == "__main__":
    sys.exit(main())
```

Note these points:

- **Catch every exception yourself.** Python exits with code 1 when an exception is not caught. If 1 is also your `fail_code`, a crash in the tool looks like an invalid file. The `try` block above turns every crash into code 2.
- **Write the failure reason to one stream only.** The test class names that stream in `failure_reason_location`. Usually, write progress messages and warnings to the other stream, or do not write them. The example is different: its reason goes to stderr, and stdout holds only the metrics. Any other text on stdout makes the JSON not valid, and the status becomes `error`. Thus do not write progress messages. If you must, write them to stderr, but then they are part of the failure reason.
- **Write metrics as one JSON object on stdout.** Use JSON types only: a string, a number, a boolean, a list or an object. Encode bytes, for example with `hex()`. Like `Md5ChecksumTest`, record the value that the check found, so that a user can compare it with the value that the check expected.
- **Write a reason that a user can act on.** DCQC copies the whole stream into `status_reason`, and from there into `suites.json`. The output CSV does not contain the reason. Its `dcqc_failed_tests` column has only the test names, and its `dcqc_metrics` column has only the metrics, so a user must open `suites.json` to find the reason. Name the file and the problem in one or two lines. Do not write a stack trace or a full dump of the file.
- **Start the file with a shebang line and make it executable.** Then the command can call it by name. The `Dockerfile` above does the `chmod`.

#### Inputs

The image receives these inputs and nothing more:

| Input | Value |
|---|---|
| Command | The `command` string from the `Process`. It is the `command_args` list that `generate_process()` gives to the `Process`, joined with spaces. |
| Input file | The staged file, in the working directory, with its original file name. In nf-dcqc it is a symbolic link. |
| Working directory | A new task directory for each run. The path is different each time. |
| User | The user ID and group ID of the person who runs the workflow. It is not root, and it has no entry in `/etc/passwd`. |
| Resources | `cpus` and `memory` from the `Process`. The defaults are `cpus=1` and `memory=2`. py-dcqc means GB, but nf-dcqc does not apply a memory limit. See the note below. |

Note these points:

- **The file name is the only argument that identifies the file.** The command uses `path.name`, not a full path. `generate_process()` puts single quotes around it (`f"'{path.name}'"`), and bash removes them, so the tool receives the plain name. Names with spaces work. A name that contains a single quote does not.
- **Follow symbolic links.** nf-dcqc links the file into the task directory. A tool that refuses a symbolic link, or that checks the link instead of its target, gives a wrong result.
- **Read the file only.** Do not change, move or delete it. `examples/external.sh` mounts the directory read-only (`:ro`), so a write fails there.
- **Do not expect other metadata.** The tool does not receive the manifest columns.
- **Do not expect credentials.** nf-dcqc gives `SYNAPSE_AUTH_TOKEN` to the `dcqc` steps only, not to the tool container. The file is already local when the tool starts, so the tool does not need to download it.

Every existing external test uses a `SingleTarget`. A `PairedTarget` test would put two file names into the command, from `self.target.files`. No test does this today, so test it end to end in nf-dcqc before you depend on it.

#### Return Codes

DCQC gets only one value from the container: the exit code of the command. `ExternalTestMixin._interpret_process_outputs` in `src/dcqc/tests/base_test.py` maps it to a status:

| Exit code | Status | `status_reason` |
|---|---|---|
| Equal to `pass_code` | `passed` | Empty |
| Equal to `fail_code` | `failed` | Text of the stream in `failure_reason_location` |
| Any other code | `error` | Text of `std_err.txt` |

Use these codes:

| Code | Meaning |
|---|---|
| `0` | The file passed the check. |
| `1` | The file failed the check. |
| `2` or higher | The tool could not do the check. |

A `failed` status and an `error` status are not the same. `failed` means the file is bad. `error` means that DCQC does not know, because the tool had a problem. Only a tool that returns different codes lets DCQC tell the two apart. Several existing tests return the same code for both, so a tool crash is reported as a bad file. Do not add to that problem. Use three different codes, and catch the crashes of the tool, as the entry file in [Creating the Entry File](#creating-the-entry-file) does.

Note these points:

- **The shell makes codes too.** Bash returns `126` if the command is not executable and `127` if it does not exist. A process that the kernel stops for lack of memory returns `137`. All of these become `error`, which is correct. Do not choose them as your `pass_code` or `fail_code`.
- **The codes can be inverted.** `GrepDateTest`, `TiffDateTimeTest` and `TiffTag306DateTimeTest` use `pass_code = 1` and `fail_code = 0`, because `grep` and `jq -e` return 0 when they find a match, and for PHI detection a match is a failure. This works, but it is fragile. With inverted codes, 1 means `passed`, and many tools also return 1 when they fail. In `TiffDateTimeTest`, if `tifftools` crashes, `grep` receives no input and returns 1, so a file that was not checked is reported as `passed`. A tool of your own can return 0 for a pass.
- **A pipeline has a different exit code in nf-dcqc and in `examples/external.sh`.** nf-dcqc runs bash with `-o pipefail`, so a pipeline returns the code of the last command that failed. `examples/external.sh` runs `sh -c`, which has no `pipefail`, so a pipeline returns the code of the last command. Put the logic into the entry file instead of a `|` in the command. Then there is one exit code, and both runners get the same one from the command. But `examples/external.sh` records the exit code of `docker run`, not of the command. If Docker itself fails, the code is one of its own, such as `125`, and `std_err.txt` holds a Docker message, not a message from the tool. To run the image exactly as nf-dcqc does, use the command in [Testing the Image](#testing-the-image).
- **Exit with the code. Do not only print it.** `dcqc compute-test` reads `exit_code.txt`, which comes from `$?`. Text on standard output has no effect on the status.

#### Testing the Image

Before you use the image in nf-dcqc, run it the same way that nf-dcqc runs it. Put a file that must pass and a file that must fail in an empty directory, and run these commands in that directory for each file:

```bash
image=ghcr.io/sage-bionetworks-workflows/mytype-validator:0.1.0
command="validate.py 'good.mytype'"

docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$PWD":"$PWD" -w "$PWD" \
  "$image" \
  /bin/bash -euo pipefail -c "( ($command) > std_out.txt 2> std_err.txt; echo \$? > exit_code.txt ) || true"

cat exit_code.txt std_out.txt std_err.txt
```

This command runs the image as the nf-dcqc `docker` profile does. The nf-dcqc `arm` profile also adds `--platform=linux/amd64`. Add that option after `-u` if you test the `arm` profile behavior, or if the image is published only for `linux/amd64`.

Make sure that:

- the good file gives `pass_code`, and the bad file gives `fail_code`,
- a file that the tool cannot read, such as an empty file or a truncated file, gives a code that is neither,
- the failure reason is in the stream that `failure_reason_location` names,
- if the class reads metrics, `std_out.txt` is empty or holds one JSON object and nothing else (`python3 -m json.tool std_out.txt` reads it with no error),
- nothing is written into the directory other than the three output files.

Do not use `dcqc qc-file` to test an external test. `qc-file` does not run containers, so it always gives external tests the status `skipped`.

Then give the test JSON and the three output files to `dcqc compute-test` to see the status that DCQC reports, as `examples/external.sh` does in its steps 6 to 9. For the full end-to-end test in nf-dcqc, see [Testing Your Changes] in CONTRIBUTING.md.

[core concepts]: https://github.com/Sage-Bionetworks-Workflows/py-dcqc#core-concepts
[edam]: https://edamontology.github.io/edam-browser/
[files and filetypes]: https://github.com/Sage-Bionetworks-Workflows/py-dcqc#files-and-filetypes
[contributing internal tests]: #contributing-internal-tests
[internal and external tests]: #internal-and-external-tests
[what makes a good test]: #what-makes-a-good-test
[registering a new test]: #registering-a-new-test
[testing your changes]: CONTRIBUTING.md#testing-your-changes
