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

## Table of Contents

- [Issue Reports](#issue-reports)
- [Documentation Improvements](#documentation-improvements)
- [Code Contributions](#code-contributions)
  - [Prerequisites](#prerequisites)
  - [Submit an issue](#submit-an-issue)
  - [Clone the repository](#clone-the-repository)
  - [Implement your changes](#implement-your-changes)
  - [Submit your contribution](#submit-your-contribution)
  - [Adding a Dependency](#adding-a-dependency)
  - [Testing Your Changes](#testing-your-changes)
  - [Troubleshooting](#troubleshooting)
- [Maintainer tasks](#maintainer-tasks)
  - [Releases](#releases)

Adding a new file type, suite, or test (internal or external) is a separate,
longer document: [ARCHITECTURE.md](ARCHITECTURE.md).

## Issue Reports

If you experience bugs or general issues with `dcqc`, please have a look
on the [issue tracker].

- **External contributors:** if you don't see anything useful there, please
  feel free to fire an issue report.
- **Sage Bionetworks employees:** file a ticket in the [DPE Jira project]
  instead of opening a GitHub issue.

> [!TIP]
> Please don't forget to include the closed issues in your search.
> Sometimes a solution was already reported, and the problem is considered
> **solved**.

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

> [!TIP]
> Please notice that the [GitHub web interface] provides a quick way of
> propose changes in `dcqc`'s files. While this mechanism can
> be tricky for normal code contributions, it works perfectly fine for
> contributing to the docs, and can be quite handy.
>
> If you are interested in trying this method out, please navigate to
> the `docs` folder in the source [repository], find which file you
> would like to propose changes and click in the little pencil icon at the
> top, to open [GitHub's code editor]. Once you finish editing the file,
> please write a message in the form at the bottom of the page describing
> which changes have you made and what are the motivations behind them and
> submit your proposal.

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

Adding a new file type, a new suite, or a new test (internal or external) is
covered in [ARCHITECTURE.md](ARCHITECTURE.md), not in this document.

### Prerequisites

Before you set up the project, install these tools:

- **Python `>=3.11, <3.15`.** CI tests 3.11 through 3.14.
- **[pipenv].** It manages the development environment. `Pipfile.lock` is
  committed, and the rest of the repo assumes that environment. The setup below
  uses `pipenv install --dev`.
- **[tox].** It runs the tests, the linters (`tox -e lint`) and the docs build
  (`tox -e docs`). Run `tox -av` to list every task.
- **[pre-commit].** Installed by the `--dev` extra; you activate it with
  `pipenv run pre-commit install` (see below).

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

   > **Important:**
   > Don't forget to add unit tests and documentation in case your
   > contribution adds an additional feature and is not just a bugfix.
   >
   > Moreover, writing a [descriptive commit message] is highly recommended.
   > In case of doubt, you can check the commit history with:
   >
   > ```console
   > git log --graph --decorate --pretty=oneline --abbrev-commit --all
   > ```
   >
   > to look for recurring communication patterns.

5. Please check that your changes don't break any unit tests:

   - Fast tests only: `pipenv run pytest`
   - Full matrix on every supported Python: `tox`
   - List the other pre-configured tasks: `tox -av`

   to look for recurring communication patterns.

5. Please check that your changes don't break any unit tests with:

   ```console
   tox
   ```

   > **Important — notes on the test suite:**
   >
   > - **`tox` runs more tests than `pytest`.** `setup.cfg` excludes the slow
   >   tests with `-m "not slow"`, but `tox.ini` overrides that with `-m ""`. So
   >   `tox` also runs the slow tests.
   > - **The slow tests need Synapse.** They use live Synapse and need a valid
   >   `SYNAPSE_AUTH_TOKEN` in your environment. No fixture skips them when the
   >   token is absent: without it they **fail or error**, and that is not a
   >   defect in your change.
   > - **`tox` always runs the slow tests; you cannot switch them off from the
   >   command line.** `tox.ini` runs `pytest {posargs} -m ""`, and the `-m ""`
   >   clears the marker filter. Whatever you type after `tox --` lands in
   >   `{posargs}`, which comes **before** that `-m ""`, so `tox -- -m "not slow"`
   >   runs as `pytest -m "not slow" -m ""`. `pytest` obeys only the last `-m`.
   >   To run the fast tests only, call `pytest` directly with
   >   `pipenv run pytest`; it reads `-m "not slow"` from `setup.cfg`.
   > - **`tests/test_acceptance.py::test_json_report_generation` is already broken
   >   in CI, and not by your change.** It errors with
   >   `UnsupportedProtocol: protocol 'syn' is not supported`. CI installs `dcqc`
   >   from the built wheel, and under that layout the `fs-synapse` entry point
   >   that registers the `syn://` protocol is not loaded. The editable dev
   >   install (`pipenv install --dev`) does load it, so the test passes locally
   >   with a valid token. See
   >   [issue #71](https://github.com/Sage-Bionetworks-Workflows/py-dcqc/issues/71)
   >   and [DPE-1795](https://sagebionetworks.jira.com/browse/DPE-1795).

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
All dependencies are declared in `setup.cfg`. Pick the case that matches your
dependency, then follow its steps in order.

#### A non-runtime dependency (tests or dev tools only)

1. Add the package to the `testing` or the `dev` extra under
   `[options.extras_require]` in `setup.cfg`.
2. Regenerate the lock file:

   ```console
   tox -e pipenv
   ```

3. Commit the updated `Pipfile.lock` together with your `setup.cfg` change.

#### A runtime dependency (imported by `dcqc` itself)

1. Add the package to `install_requires` under `[options]` in `setup.cfg`.
2. Add the **same** package to `docs/requirements.txt`. Read the Docs installs
   that file to build the module reference, so the API documentation fails to
   build if the package is missing from it. Both files carry a comment that says
   so.
3. Regenerate the lock file:

   ```console
   tox -e pipenv
   ```

4. Commit `setup.cfg`, `docs/requirements.txt` and `Pipfile.lock` together.

The `all`, `testing` and `dev` extras are exempt from step 2, because the API
documentation does not import them.

> [!IMPORTANT]
> `tox -e pipenv` runs `pipenv lock --dev` and then `pipenv install --dev`.
> `Pipfile.lock` is committed. Never edit `Pipfile.lock` by hand.

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
   Python version (see [Prerequisites](#prerequisites)). When in doubt you can
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
[pipenv]: https://pipenv.pypa.io/
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
[dpe jira project]: https://sagebionetworks.jira.com/browse/DPE
