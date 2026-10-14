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

In `py-dcqc`, any test where the primary business logic is executed within the package itself is considered "internal". One example is the `Md5ChecksumTest`.

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

In `py-dcqc`, any test where the primary business logic is executed outside of this package itself is considered to be external. One example is the `LibTiffInfoTest`. For these tests, `py-dcqc` is responsible for packaging up a Nextflow process which is then executed in an [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) workflow run. Such tests are not possible to run in `py-dcqc` alone at this time. This makes contributing, testing, debugging, and using external tests a little more complicated than internal tests such as the `Md5ChecksumTest` which has all of its logic built into this package.

When contributing an external test be sure to do the following:

1. Follow the [Code Contributions](CONTRIBUTING.md#code-contributions) steps in CONTRIBUTING.md to set up `py-dcqc` and create your contribution.

2. Add a new module at `src/dcqc/tests/<snake_case>_test.py`, with one test class in it, as for an internal test.

3. Subclass `ExternalBaseTest`, and import it from `dcqc.tests.base_test`. The `dcqc.tests` package does not re-export it:

   ```python
   from dcqc.tests.base_test import ExternalBaseTest


   class MyNewTest(ExternalBaseTest):
       """Tests that ..."""
   ```

4. Include a class docstring that describes the purpose of the test. The
   docstring goes into the Sphinx API documentation. `dcqc list-tests` does not
   show it: that command prints only the file type, the EDAM identifier, the
   test name, the tier and the test type.

5. Include the following class attributes:

   - `tier`: A `TestTier` enum describing the complexity of the validation. Valid `tier` values include:
     - `FILE_INTEGRITY`
     - `INTERNAL_CONFORMANCE`
     - `EXTERNAL_CONFORMANCE`
     - `SUBJECTIVE_CONFORMANCE`
   - `pass_code`: The exit code that will be returned by the command indicating a passed test.
   - `fail_code`: The exit code that will be returned by the command indicating a failed test.
   - `failure_reason_location`: The file (either `"std_out"` or `"std_err"`) that will contain the reason for a failed test.
   - `target`: The target class that the test will be applied to. This value will be `SingleTarget` for individual files and `PairedTarget` for paired files.

6. Implement the `generate_process` method. It does not run the command. It returns a `Process` object that describes the container and the command for `nf-dcqc` to run:

   ```python
   def generate_process(self) -> Process:
       path = self.target.file.stage()

       command_args = [
           "my-tool",
           f"'{path.name}'",
       ]
       process = Process(
           container="quay.io/sagebionetworks/my-tool:1.0",
           command_args=command_args,
       )
       return process
   ```

   Note these two points:

   - Call `self.target.file.stage()` first. The workflow needs a local copy of the file.
   - Build `command_args` from `path.name`, not from the full path. The workflow mounts the file in the working directory of the container, so a full local path is not valid there.

7. Register the test with the two steps in the "Registering a New Test" section above. Without them the test never runs.

8. Add a unit test for your class to `tests/test_external_tests.py`. Because the business logic is in a container, you can only test the `Process` that `generate_process` returns, and the interpretation of the exit codes. To test the container itself, see [Testing Your Changes](CONTRIBUTING.md#testing-your-changes) in CONTRIBUTING.md.

9. If possible, contribute an external test that returns different codes when it fails and when it errors out. Currently, a limitation of DCQC is that several external tests return the same `exit_code` when they fail and encounter an error. This will be addressed in future work that will add finer grained result interpretation.

[core concepts]: https://github.com/Sage-Bionetworks-Workflows/py-dcqc#core-concepts
[edam]: https://edamontology.github.io/edam-browser/
[files and filetypes]: https://github.com/Sage-Bionetworks-Workflows/py-dcqc#files-and-filetypes
