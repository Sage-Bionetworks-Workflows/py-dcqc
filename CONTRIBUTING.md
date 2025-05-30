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

<!---
#TODO: Include a reference or explanation about the internals of the project.

An architecture description, design principles or at least a summary of the
main concepts will make it easy for potential contributors to get started
quickly.
--->

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
   cd dcqc
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

### Contributing New Tests

#### Contributing Internal Tests

In `py-dcqc`, any test where the primary business logic is executed within the package itself is considered "internal". One example is the `Md5ChecksumTest`.

When contributing an internal test be sure to do the following:

1. Follow the steps above to set up `py-dcqc` and create your contribution.

1. Include a class docstring that describes the purpose of the test.

1. Include the following class attributes:

   - `tier`: A `TestTier` enum describing the complexity of the validation. Valid `tier` values include:
     - `FILE_INTEGRITY`: Validates basic file integrity and availability. Requires additional information for MD5 verification, file extension validation, format-specific checks, and decompression verification.
     - `INTERNAL_CONFORMANCE`: Ensures file internal consistency and format compliance. Only needs the files themselves and their format specification for validation against schema and internal metadata checks.
     - `EXTERNAL_CONFORMANCE`: Verifies file features against separately submitted metadata. Uses additional information while remaining objective/quantitative for validating channel counts, file sizes, nomenclature, and required companion files.
     - `SUBJECTIVE_CONFORMANCE`: Evaluates files using qualitative criteria that may need expert review. Uses metrics, heuristics, or models for tasks like sample swap detection, PHI detection, and outlier identification.
   - `target`: The target class that the test will be applied to. This value will be `SingleTarget` for individual files and `PairedTarget` for paired files.

1. Implement the major logic of the test in the `compute_status` method. This should include a condition for returning a `status` of `TestStatus.PASS` when the test conditions are met and `TestStatus.FAIL` when they are not.
   - For failing cases be sure to include a line setting the class' `status_reason` to a helpful string that will tell users why the test failed before returning the `status`.

#### Contributing External Tests

In `py-dcqc`, any test where the primary business logic is executed outside of this package itself is considered to be external. One example is the `LibTiffInfoTest`. For these tests, `py-dcqc` is responsible for packaging up a Nextflow process which is then executed in an [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) workflow run. Such tests are not possible to run in `py-dcqc` alone at this time. This makes contributing, testing, debugging, and using external tests a little more complicated that internal tests such as the `Md5ChecksumTest` which has all of its logic built into this package.

When contributing an internal test be sure to do the following:

1. Follow the steps above to set up `py-dcqc` and create your contribution.

1. Include a class docstring that describes the purpose of the test.

1. Include the following class attributes:

   - `tier`: A `TestTier` enum describing the complexity of the validation. Valid `tier` values include:
     - `FILE_INTEGRITY`
     - `INTERNAL_CONFORMANCE`
     - `EXTERNAL_CONFORMANCE`
     - `SUBJECTIVE_CONFORMANCE`
   - `pass_code`: The exit code that will be returned by the command indicating a passed test.
   - `fail_code`: The exit code that will be returned by the command indicating a failed test.
   - `failure_reason_location`: The file (either `"std_out"` or `"std_err"`) that will contain the reason for a failed test.
   - `target`: The target class that the test will be applied to. This value will be `SingleTarget` for individual files and `PairedTarget` for paired files.

1. If possible, contribute an external test that returns different codes when it fails and when it errors out. Currently, a limitation of DCQC is that several external tests return the same `exit_code` when they fail and encounter an error. This will be addressed in future work that will add finer grained result interpretation.

### Testing Your Changes

1. Follow the instructions in the [README.md](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc/blob/dev/README.md)
   file in the `nf-dcqc` respository to set up the workflow on your local machine.

   - Run `git checkout dev` to switch to the developer branch

1. Build your local version of `py-dcqc` with your new changes with:

   ```console
   src/docker/build.sh
   ```

   NOTE: This step assumes that you have docker installed and that it is running, and that you have `pipx` installed.

1. Follow `nf-dcqc` instructions to create a `nextflow run` command that tests your contribution.

   - You should include at least two files in your `nf-dcqc` input file ([example](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc/blob/dev/testdata/input_full.csv)), one that you expect to pass your contributed test, and one that you expect to fail.
   - Include the `local` profile so that the workflow leverages your locally built `py-orca` container

   Example command (executed from within your local `nf-dcqc` repo clone):

   ```
   nextflow run main.nf -profile local,docker --input path/to/your/input.csv -- outdir output --required_tests <YOUR_TEST_NAME>
   ```

1. Examine the final `output.csv` and `suites.json` files exported by the Nextflow workflow, if your contributed test bahaved as
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

3. Make sure to have a reliable [tox] installation that uses the correct
   Python version (e.g., 3.7+). When in doubt you can run:

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
   .venv/bin/tox -e all
   ```

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
2. Tag the current commit on the main branch with a release tag, e.g., `v1.2.3`.
3. Push the new tag to the upstream [repository],
   e.g., `git push upstream v1.2.3`
4. Clean up the `dist` and `build` folders with `tox -e clean`
   (or `rm -rf dist build`)
   to avoid confusion with old builds and Sphinx docs.
5. Run `tox -e build` and check that the files in `dist` have
   the correct version (no `.dirty` or [git] hash) according to the [git] tag.
   Also check the sizes of the distributions, if they are too big (e.g., >
   500KB), unwanted clutter may have been accidentally included.
6. Run `tox -e publish -- --repository pypi` and check that everything was
   uploaded to [PyPI] correctly.

[^contrib1]:
    Even though, these resources focus on open source projects and
    communities, the general ideas behind collaborating with other developers
    to collectively create software are general and can be applied to all sorts
    of environments, including private companies and proprietary code bases.

[black]: https://pypi.org/project/black/
[commonmark]: https://commonmark.org/
[contribution-guide.org]: http://www.contribution-guide.org/
[creating a pr]: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request
[descriptive commit message]: https://chris.beams.io/posts/git-commit
[docstrings]: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
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
