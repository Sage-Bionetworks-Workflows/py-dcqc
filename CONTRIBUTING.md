# Contributing

Welcome to `dcqc` contributor's guide.

This document focuses on getting any potential contributor familiarized with
the development processes, but [other kinds of contributions] are also appreciated.

If you are new to using [git] or have never collaborated in a project previously,
please have a look at [contribution-guide.org]. Other resources are also
listed in the excellent [guide created by FreeCodeCamp] [^contrib1].

Please notice, all users and contributors are expected to be **open,
considerate, reasonable, and respectful**. When in doubt,
[Python Software Foundation's Code of Conduct] is a good reference in terms of
behavior guidelines.

## Issue Reports

If you experience bugs or general issues with `dcqc`, please have a look
on the [issue tracker].
If you don't see anything useful there, please feel free to fire an issue report.

:::{tip}
Please don't forget to include the closed issues in your search.
Sometimes a solution was already reported, and the problem is considered
**solved**.
:::

New issue reports should include information about your programming environment
(e.g., operating system, Python version) and steps to reproduce the problem.
Please try also to simplify the reproduction steps to a very minimal example
that still illustrates the problem you are facing. By removing other factors,
you help us to identify the root cause of the issue.

## Documentation Improvements

You can help improve `dcqc` docs by making them more readable and coherent, or
by adding missing information and correcting mistakes.

`dcqc` documentation uses [Sphinx] as its main documentation compiler.
This means that the docs are kept in the same repository as the project code, and
that any documentation update is done in the same way was a code contribution.
The documentation is written using [CommonMark] with [MyST] extensions.

:::{tip}
Please notice that the [GitHub web interface] provides a quick way of
propose changes in `dcqc`'s files. While this mechanism can
be tricky for normal code contributions, it works perfectly fine for
contributing to the docs, and can be quite handy.

If you are interested in trying this method out, please navigate to
the `docs` folder in the source [repository], find which file you
would like to propose changes and click in the little pencil icon at the
top, to open [GitHub's code editor]. Once you finish editing the file,
please write a message in the form at the bottom of the page describing
which changes have you made and what are the motivations behind them and
submit your proposal.
:::

When working on documentation changes in your local machine, you can
compile them using [tox] :

```
tox -e docs
```

and use Python's built-in web server for a preview in your web browser
(`http://localhost:8000`):

```
python3 -m http.server --directory 'docs/_build/html'
```

## Code Contributions

Before you write code, read the [Core Concepts] section of the `README.md`. It
describes the four objects that move through the whole system (`File`, `Target`,
`Test` and `Suite`), the difference between internal and external tests, and the
order of the command line pipeline.

### Submit an issue

Before you work on any non-trivial code contribution it's best to first create
a report in the [issue tracker] to start a discussion on the subject.
This often provides additional considerations and avoids unnecessary work.

### Clone the repository

1. Create an user account on GitHub if you do not already have one.

2. Fork the project [repository]: click on the _Fork_ button near the top of the
   page. This creates a copy of the code under your account on GitHub.

3. Clone this copy to your local disk:

   ```console
   git clone git@github.com:Sage-Bionetworks-Workflows/py-dcqc.git
   cd py-dcqc
   ```

4. You should run:

   ```console
   pipenv install --dev
   ```

   to create an isolated virtual environment containing package dependencies,
   including those needed for development (_e.g._ testing, documentation).

5. Install [pre-commit] hooks:

   ```
   pipenv run pre-commit install
   ```

   `dcqc` comes with a lot of hooks configured to automatically help the
   developer to check the code being written.

### Implement your changes

1. Create a branch to hold your changes:

   ```console
   git checkout -b my-feature
   ```

   and start making changes. Never work on the main branch!

2. Start your work on this branch. Don't forget to add [docstrings] to new
   functions, modules and classes, especially if they are part of public APIs.

3. Add yourself to the list of contributors in `AUTHORS.md`.

4. When you're done editing, do:

   ```console
   git add <MODIFIED FILES>
   git commit
   ```

   to record your changes in [git].

   Please make sure to see the validation messages from [pre-commit] and fix
   any eventual issues.
   This should automatically use [flake8]/[black] to check/fix the code style
   in a way that is compatible with the project.

   :::{important}
   Don't forget to add unit tests and documentation in case your
   contribution adds an additional feature and is not just a bugfix.

   Moreover, writing a [descriptive commit message] is highly recommended.
   In case of doubt, you can check the commit history with:

   ```console
   git log --graph --decorate --pretty=oneline --abbrev-commit --all
   ```

   to look for recurring communication patterns.
   :::

5. Please check that your changes don't break any unit tests with:

   ```console
   tox
   ```

   :::{important}
   `tox` and a bare `pytest` do not run the same tests. `setup.cfg` excludes the
   slow tests with `-m "not slow"`, but `tox.ini` overrides that with `-m ""`.
   The slow tests use live Synapse, so `tox` needs a valid
   `SYNAPSE_AUTH_TOKEN` in your environment. There is no fixture that skips
   these tests when the token is absent: without the token they **fail or
   error**, and that is not a defect in your change.

   One of the two slow tests,
   `tests/test_acceptance.py::test_json_report_generation`, also fails in CI
   even with a valid token. See
   [issue #71](https://github.com/Sage-Bionetworks-Workflows/py-dcqc/issues/71).

   To run only the fast tests, use `pipenv run pytest`. Do not try to pass the
   marker through `tox`: `tox.ini` puts `{posargs}` **before** its own `-m ""`,
   so `tox -- -m "not slow"` becomes `pytest -m "not slow" -m ""`. `pytest`
   keeps only the last `-m`, and your marker is ignored.
   :::

   You can also use [tox] to run several other pre-configured tasks in the
   repository. Try `tox -av` to see a list of the available checks.

### Submit your contribution

1. If everything works fine, push your local branch to the remote server with:

   ```console
   git push -u origin my-feature
   ```

2. Go to the web page of your fork and click "Create pull request"
   to send your changes for review.

   Find more detailed information in [creating a PR]. You might also want to open
   the PR as a draft first and mark it as ready for review after the feedbacks
   from the continuous integration (CI) system or any required fixes.

### Adding a Dependency

Dependencies live in `setup.cfg`. A runtime dependency goes in `install_requires`
under `[options]`. A dependency that only the tests or the development tools need
goes in the `testing` or the `dev` extra under `[options.extras_require]`.

A **runtime** dependency needs a second edit. Add the same package to
`docs/requirements.txt` as well. Read the Docs installs that file to build the
module reference, so the API documentation fails to build if the package is
absent from it. Both files carry a comment that says this. The `all`, `testing`
and `dev` extras are not part of this rule, because the API documentation does
not import them.

After any change to the dependencies in `setup.cfg`, regenerate the lock file:

```console
tox -e pipenv
```

This runs `pipenv lock --dev` and then `pipenv install --dev`. `Pipfile.lock` is
committed, so commit the new lock file together with your `setup.cfg` change.
Never edit `Pipfile.lock` by hand.

### Contributing New File Types

If you want to add the ability to test a completely new file type, you must add that type first.
The [Files and FileTypes] section of the `README.md` describes what a file type
is and lists the types that exist today. Read it before you add one.

A new file type needs two things: a `FileType` object, and a suite class that
claims it. The `FileType` object gives the type a name, its valid extensions and
its [EDAM] identifier. The suite decides which tests DCQC runs on files of that
type.

A file type without a suite is legal, but it does almost nothing. DCQC gives
files of an unclaimed type the generic `FileSuite`, and the type does not show in
`dcqc list-tests`. Nothing warns you, because `dcqc list-tests` and
`SuiteABC.get_subclass_by_file_type` work from the suites, not from the file type
registry.

Register the file type in `src/dcqc/file.py`. Add one line to the block of
`FileType(...)` statements at the end of the module. Construction of the
object is the registration; there is no separate registry call:

```python
FileType("MY-TYPE", (".mytype", ".mytype.gz"), "format_1234")
```

Note these points:

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

### Contributing New Suites

A suite connects one file type to the tests that DCQC runs on files of that type.
There is one suite class for each file type. All of them are in
`src/dcqc/suites/suites.py`, and all of them come from `SuiteABC` in
`src/dcqc/suites/suite_abc.py`. There is no `BaseSuite`.

Add the class to `src/dcqc/suites/suites.py`. Give it a docstring, the file type
it claims, and the tests that are new at this level:

```python
class MyTypeSuite(FileSuite):
    """Suite class for MY-TYPE files."""

    file_type = FileType.get_file_type("MY-TYPE")
    add_tests = (tests.MyNewTest,)
```

Note these points:

- `FileType.get_file_type` runs when Python defines the class, so register the
   file type first. See the section above. An unregistered name raises a
   `ValueError` at import time.
- Subclass `FileSuite` for a new format. Subclass a more specific suite if your
   type is a subtype of an existing format, as `H5ADSuite(HDF5Suite)`,
   `OmeTiffSuite(TiffSuite)` and `JsonLdSuite(JsonSuite)` do.
- `add_tests` is additive along the class hierarchy. It does not replace the
   list of the parent class. `list_test_classes` unions the `add_tests` of every
   class in the method resolution order, so a subclass also runs the tests of
   its parents. Inheritance is the only way to share tests between suites.
- `add_tests` is optional. `TXTSuite`, `TSVSuite`, `CSVSuite`, `BAMSuite` and
   `HDF5Suite` declare no tests of their own and run only the tests of
   `FileSuite`.
- Write the test names as `tests.MyNewTest`, because `suites.py` imports the
   package with `from dcqc import tests`. Every test in `add_tests` must also
   have an import line in `src/dcqc/tests/__init__.py`. See
   [Registering a New Test](#registering-a-new-test).
- Two suites must not claim the same file type. The registry is a dictionary
   keyed on the file type name, so the second class replaces the first one with
   no warning.
- Do not use `del_tests` to remove an inherited test. Nothing in `src/` uses it.
   The loop that reads it uses `hasattr`, so a subclass that does not declare
   its own `del_tests` applies the `del_tests` of an ancestor again at its own
   position in the method resolution order, and this can remove its own
   `add_tests`. Change the shape of the hierarchy instead.
- Class names in `suites.py` are not consistent. ALL-CAPS acronyms (`TSVSuite`,
   `HDF5Suite`) sit beside PascalCase names (`TiffSuite`, `FastqSuite`). Match
   the classes near yours.

`SuiteABC` has no abstract methods, so Python does not tell you that a class
attribute is absent. If you forget `file_type`, the class still imports, and the
`AttributeError` comes later from `get_subclass_by_file_type` and
`list_test_classes_by_file_type`. Both walk all of the suites, so one incomplete
suite breaks the selection of every other suite and breaks `dcqc list-tests`.

Registration is by import, as it is for tests. `src/dcqc/suites/__init__.py` is
empty, and the suites are registered only because `src/dcqc/__init__.py` imports
`dcqc.suites.suites`. A class in `suites.py` therefore needs no other step. A
new suites *module* needs two more:

- Add an import for it to `src/dcqc/__init__.py`. That file carries an
   `# isort: skip_file` comment, because its import order prevents a circular
   import. Do not reorder the lines.
- Add a `[[tool.mypy.overrides]]` block for the module in `pyproject.toml` with
   `disable_error_code = "assignment"`, as `dcqc.suites.suites` has. Suites
   reassign inherited `ClassVar` attributes, and mypy reports that as an
   assignment error.


### Contributing New Tests

A new test needs two things: a test class, and registration. If you write the class but do not register it, nothing tells you. The class does not fail to import, and `pre-commit` and `tox` stay green. The problem shows later, when `dcqc compute-test` stops with `Subclass (MyNewTest) not available`.

DCQC finds tests by a walk of the subclasses of `BaseTest`. There is no plugin scan, no entry point and no decorator. A test class is visible only if `src/dcqc/tests/__init__.py` imports its module, and DCQC runs it only if a suite lists it.

#### Registering a New Test

Do these two steps for every new test, internal or external.

1. Add an import line for your module to `src/dcqc/tests/__init__.py`, in alphabetical order with the lines that are there:

   ```python
   from dcqc.tests.my_new_test import MyNewTest
   ```

   These imports look unused, but they are the registration. Do not remove them. Two settings in `setup.cfg` keep the linters from removing them for you: `per-file-ignores = */__init__.py:F401` in the `[flake8]` section, and `ignore-init-module-imports=true` in the `[autoflake]` section. Do not change either one.

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

   The first step makes the class known to DCQC. This step makes DCQC run it. A test that is in no suite never runs against a CSV manifest and never shows in `dcqc list-tests`. Pick the suite for the file type that your test applies to, or `FileSuite` if it applies to all file types. `add_tests` is additive along the class hierarchy, so a suite also runs the tests of the suites it inherits from.

#### Contributing Internal Tests

In `py-dcqc`, any test where the primary business logic is executed within the package itself is considered "internal". One example is the `Md5ChecksumTest`.

When contributing an internal test be sure to do the following:

1. Follow the steps above to set up `py-dcqc` and create your contribution.

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
   - Call `self.target.file.stage()` to get a local `Path` to the file. This works for remote URLs, such as `syn://`, as well as local files.

7. Register the test with the two steps in the "Registering a New Test" section above. Without them the test never runs.

8. Add a unit test for your class to `tests/test_internal_tests.py`.

#### Contributing External Tests

In `py-dcqc`, any test where the primary business logic is executed outside of this package itself is considered to be external. One example is the `LibTiffInfoTest`. For these tests, `py-dcqc` is responsible for packaging up a Nextflow process which is then executed in an [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) workflow run. Such tests are not possible to run in `py-dcqc` alone at this time. This makes contributing, testing, debugging, and using external tests a little more complicated than internal tests such as the `Md5ChecksumTest` which has all of its logic built into this package.

When contributing an external test be sure to do the following:

1. Follow the steps above to set up `py-dcqc` and create your contribution.

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

8. Add a unit test for your class to `tests/test_external_tests.py`. Because the business logic is in a container, you can only test the `Process` that `generate_process` returns, and the interpretation of the exit codes. To test the container itself, see [Testing Your Changes](#testing-your-changes) below.

9. If possible, contribute an external test that returns different codes when it fails and when it errors out. Currently, a limitation of DCQC is that several external tests return the same `exit_code` when they fail and encounter an error. This will be addressed in future work that will add finer grained result interpretation.

### Testing Your Changes

1. Follow the instructions in the [README.md](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc/blob/dev/README.md)
   file in the `nf-dcqc` repository to set up the workflow on your local machine.

   - Run `git checkout dev` to switch to the developer branch

2. Build your local version of `py-dcqc` with your new changes with:

   ```console
   src/docker/build.sh
   ```

   NOTE: This step assumes that you have docker installed and that it is running, and that you have `pipx` installed.

3. Follow `nf-dcqc` instructions to create a `nextflow run` command that tests your contribution.

   - You should include at least two files in your `nf-dcqc` input file ([example](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc/blob/dev/testdata/input_full.csv)), one that you expect to pass your contributed test, and one that you expect to fail.
   - Include the `local` profile so that the workflow leverages your locally built `py-dcqc` container

   Example command (executed from within your local `nf-dcqc` repo clone):

   ```
   nextflow run main.nf -profile local,docker --input path/to/your/input.csv --outdir output --required_tests <YOUR_TEST_NAME>
   ```

4. Examine the final `output.csv` and `suites.json` files exported by the Nextflow workflow, if your contributed test behaved as
   expected, you're done! If not, debug and make changes to your contribution and re-run the workflow.

### Troubleshooting

The following tips can be used when facing problems to build or test the
package:

1. Make sure to fetch all the tags from the upstream [repository].
   The command `git describe --abbrev=0 --tags` should return the version you
   are expecting. If you are trying to run CI scripts in a fork repository,
   make sure to push all the tags.
   You can also try to remove all the egg files or the complete egg folder, i.e.,
   `.eggs`, as well as the `*.egg-info` folders in the `src` folder or
   potentially in the root of your project.

2. Sometimes [tox] misses out when new dependencies are added, especially to
   `setup.cfg` and `docs/requirements.txt`. If you find any problems with
   missing dependencies when running a command with [tox], try to recreate the
   `tox` environment using the `-r` flag. For example, instead of:

   ```console
   tox -e docs
   ```

   Try running:

   ```console
   tox -r -e docs
   ```

3. Make sure to have a reliable [tox] installation that uses a supported
   Python version (3.11 or later, but earlier than 3.15). When in doubt you can
   run:

   ```console
   tox --version
   # OR
   which tox
   ```

   If you have trouble and are seeing weird errors upon running [tox], you can
   also try to create a dedicated [virtual environment] with a [tox] binary
   freshly installed. For example:

   ```console
   virtualenv .venv
   source .venv/bin/activate
   .venv/bin/pip install tox
   .venv/bin/tox
   ```

   There is no `all` environment in `tox.ini`. Run `tox -av` for the list of
   the environments that exist.

4. [Pytest can drop you] in an interactive session in the case an error occurs.
   In order to do that you need to pass a `--pdb` option (for example by
   running `tox -- -k <NAME OF THE FALLING TEST> --pdb`).
   You can also setup breakpoints manually instead of using the `--pdb` option.

## Maintainer tasks

### Releases

If you are part of the group of maintainers and have correct user permissions
on [PyPI], the following steps can be used to release a new version for
`dcqc`:

1. Make sure all unit tests are successful.
2. Bump `version` in the `[metadata]` section of `setup.cfg` to the new
   version, e.g., `1.2.3`, and merge that change into the main branch. The
   [git] tag alone does not set the version of the package.
3. Tag the current commit on the main branch with a release tag, e.g., `v1.2.3`.
4. Push the new tag to the upstream [repository],
   e.g., `git push upstream v1.2.3`

   A `v*` tag starts the `pypi-publish` job in `.github/workflows/CI.yml`, which
   builds the distribution and uploads it to [PyPI]. In normal conditions the
   release is complete at this point. Confirm that PyPI serves the new version
   before you go on.

5. If the CI job did not run or did not succeed, do the release manually with
   the steps below.

   1. Clean up the `dist` and `build` folders with `tox -e clean`
      (or `rm -rf dist build`)
      to avoid confusion with old builds and Sphinx docs.
   2. Run `tox -e build` and check that the files in `dist` have
      the correct version (no `.dirty` or [git] hash) according to the [git]
      tag. Also check the sizes of the distributions, if they are too big
      (e.g., > 500KB), unwanted clutter may have been accidentally included.
   3. Run `tox -e publish -- --repository pypi` and check that everything was
      uploaded to [PyPI] correctly. `tox -e publish` alone uploads to
      TestPyPI, so the `--repository pypi` argument is necessary.

[^contrib1]:
    Even though, these resources focus on open source projects and
    communities, the general ideas behind collaborating with other developers
    to collectively create software are general and can be applied to all sorts
    of environments, including private companies and proprietary code bases.

[black]: https://pypi.org/project/black/
[commonmark]: https://commonmark.org/
[contribution-guide.org]: http://www.contribution-guide.org/
[core concepts]: https://github.com/Sage-Bionetworks-Workflows/py-dcqc#core-concepts
[creating a pr]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request
[descriptive commit message]: https://chris.beams.io/posts/git-commit
[docstrings]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
[edam]: https://edamontology.github.io/edam-browser/
[files and filetypes]: https://github.com/Sage-Bionetworks-Workflows/py-dcqc#files-and-filetypes
[first-contributions tutorial]: https://github.com/firstcontributions/first-contributions
[flake8]: https://flake8.pycqa.org/en/stable/
[git]: https://git-scm.com
[github web interface]: https://docs.github.com/en/github/managing-files-in-a-repository/managing-files-on-github/editing-files-in-your-repository
[github's code editor]: https://docs.github.com/en/github/managing-files-in-a-repository/managing-files-on-github/editing-files-in-your-repository
[github's fork and pull request workflow]: https://guides.github.com/activities/forking/
[guide created by freecodecamp]: https://github.com/freecodecamp/how-to-contribute-to-open-source
[miniconda]: https://docs.conda.io/en/latest/miniconda.html
[myst]: https://myst-parser.readthedocs.io/en/latest/syntax/syntax.html
[other kinds of contributions]: https://opensource.guide/how-to-contribute
[pre-commit]: https://pre-commit.com/
[pypi]: https://pypi.org/
[pyscaffold's contributor's guide]: https://pyscaffold.org/en/stable/contributing.html
[pytest can drop you]: https://docs.pytest.org/en/stable/usage.html#dropping-to-pdb-python-debugger-at-the-start-of-a-test
[python software foundation's code of conduct]: https://www.python.org/psf/conduct/
[sphinx]: https://www.sphinx-doc.org/en/master/
[tox]: https://tox.readthedocs.io/en/stable/
[virtual environment]: https://realpython.com/python-virtual-environments-a-primer/
[virtualenv]: https://virtualenv.pypa.io/en/stable/
[repository]: https://github.com/sage-bionetworks-workflows/py-dcqc
[issue tracker]: https://github.com/sage-bionetworks-workflows/py-dcqc/issues
