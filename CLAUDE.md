# CLAUDE.md

## Project

`py-dcqc` runs tiered quality-control checks on data files. It is both a library and a Typer CLI (distribution name `dcqc`, import name `dcqc`, repo directory `py-dcqc`).

The CLI is deliberately split into many small commands that each read and write JSON. This exists so the sibling Nextflow workflow [nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) can fan the steps out in parallel. Keep new commands in that shape.

Checks are divided into **internal tests** (business logic runs in Python, here) and **external tests** (business logic runs in a Docker container that *nf-dcqc* executes). `py-dcqc` cannot run an external test on its own — it only emits a `Process` descriptor. See `src/dcqc/tests/CLAUDE.md`.

See README.md for concepts and CLI usage, CONTRIBUTING.md for setup.

## Stack

- Python `>=3.11, <3.15` (setup.cfg `[options] python_requires`). CI matrix: 3.11–3.14 on ubuntu and macos. Windows is intentionally disabled (.github/workflows/CI.yml, the `test` job's platform matrix, ORCA-348).
- Typer + Click CLI; entry point `dcqc = dcqc.main:app` (setup.cfg `[options.entry_points]`). Also runnable as `python -m dcqc`.
- fsspec for all I/O, with `fs-synapse` providing the `syn://` protocol. Every path argument accepts an fsspec URL, not just a local path.
- tox for task running, pytest for tests, Sphinx + MyST for docs. The dev environment is pipenv-based (`Pipfile` plus a committed `Pipfile.lock`) — see Commands.
- Container published to `ghcr.io/sage-bionetworks-workflows/py-dcqc`. Docker Hub publishing was removed in PR #66.

## Commands

Setup — CONTRIBUTING.md steps 4 and 5:

```console
pipenv install --dev
pipenv run pre-commit install
```

The `Pipfile` does nothing more than install the project editable with three extras, so `pip install -e '.[all,testing,dev]'` into a virtualenv of your own is an equivalent fallback. Prefer pipenv, because `Pipfile.lock` is committed and the rest of the repo assumes it: README.md, `examples/internal.sh` and `examples/external.sh` all activate with `source "$(pipenv --venv)/bin/activate"`, and CONTRIBUTING.md tells you to run the fast tests with `pipenv run pytest`.

`Pipfile` and `Pipfile.lock` are updated together — regenerate the lock with `tox -e pipenv` after changing `setup.cfg` dependencies, never by hand.

| Command | What it does |
|---|---|
| `tox` | Run tests on every supported Python. **Runs slow tests too** — see Constraints. |
| `tox -av` | List all available tox environments |
| `tox -e lint` | `pre-commit run --all-files` |
| `tox -e clean` | Remove `build`, `dist`, `docs/_build`, `src/*.egg-info` |
| `tox -e build` | `python -m build` |
| `tox -e docs` | Sphinx HTML into `docs/_build/html` |
| `tox -e doctests` / `tox -e linkcheck` | Same builder, different Sphinx target |
| `tox -e publish` | Twine upload; **defaults to testpypi**, pass `-- --repository pypi` for the real thing |
| `tox -e pipenv` | Refresh `Pipfile.lock` after changing `setup.cfg` dependencies (`pipenv lock --dev` then `pipenv install --dev`) |
| `src/docker/build.sh` | Build the local `dcqc` image. Requires a running Docker daemon and `pipx`; it runs `tox -e clean,build` first because the Dockerfile installs the tarball out of `dist/`. |

Serve built docs: `python3 -m http.server --directory 'docs/_build/html'`.

Debugging a single test: `tox -- -k <TEST NAME> --pdb`. Note the CAUTION comment in setup.cfg `[tool:pytest] addopts` — the `--cov` flags there can prevent breakpoints from being hit; comment them out locally if `--pdb` misbehaves.

Release (CONTRIBUTING.md "Releases"): bump `version` in setup.cfg `[metadata]` and merge it, tag `vX.Y.Z`, push the tag. The `v*` tag starts the `pypi-publish` job in CI and that normally completes the release — confirm PyPI serves the new version. `tox -e clean`, `tox -e build`, `tox -e publish -- --repository pypi` is the manual fallback for when CI does not run or fails, not the routine path.

## Data Models

Four shapes flow through the whole system. All are defined in `src/dcqc/` and all serialize to JSON — see `src/dcqc/CLAUDE.md` for the serialization rules, which have sharp edges.

```
Suite  ── target ──> Target ── files ──> [File]
  └──── tests ────> [Test]   (each Test's own `target` key is stripped when nested in a Suite)
```

**Input** is a CSV manifest. A `url` column is required; every other column becomes `File.metadata`. Only two metadata keys are consumed by code: `file_type` (read by `File`, `file.py:263`) and `md5_checksum` (read by `Md5ChecksumTest`).

**Output** is the input CSV plus five appended columns, written by `src/dcqc/updaters.py:45-57`: `dcqc_status`, `dcqc_required_tests`, `dcqc_skipped_tests`, `dcqc_failed_tests`, `dcqc_errored_tests`. The four list columns are comma-joined inside a single cell.

**Statuses** are two distinct enums — do not mix them. `TestStatus` (`base_test.py:20`) is `pending`/`passed`/`failed`/`skipped`/`error`; note the member is `NONE` but the serialized value is `"pending"`. `SuiteStatus` (`suite_abc.py:17`) is `NONE`/`GREEN`/`RED`/`AMBER`/`GREY`.

**The CLI pipeline order is mandatory.** Each step validates the incoming JSON against an expected class, so a wrong-order input fails with `ValueError: JSON file (...) is not expected type (...)`:

```
create-targets -> create-tests -> [create-process -> nf-dcqc runs container] -> compute-test
               -> create-suite -> combine-suites -> update-csv
```

`qc-file` is a one-shot shortcut through that pipeline, but it force-skips every external test (`main.py:198-203`), so external results always come back `"skipped"`.

## Conventions

- **Command names are hyphenated, not underscored.** Typer derives them from the function name, so `def create_targets` is invoked as `dcqc create-targets`. README.md used underscores in its command list for a long time — a reviewer flagged it in PR #69 and it was corrected on branch DPE-1643. Use the hyphenated form in any new doc or example.
- Commit subjects use a Jira prefix and a PR suffix: `[DPE-1571] Updated FS-Synapse... (#72)`. Older history uses `ORCA-###` or no prefix at all. Not conventional commits.
- Branches: bare ticket ID (`DPE-1643`), `<author>/<TICKET>/<desc>`, or kebab-case description. All three are in use.
- PR bodies must have **Problem / Solution / Testing** sections (.github/pull_request_template.md), and must not paste test results containing sensitive data.
- Docs are Markdown via MyST, not reStructuredText.
- Google-style docstrings (napoleon). `interrogate` reports docstring coverage but is set to `--fail-under=0`, so it never fails a commit.

## Architecture

`src/dcqc/` holds the object model and CLI. Two subpackages have their own CLAUDE.md because their registration rules are easy to get wrong:

- `src/dcqc/tests/` — one module per QC check. **This is production code, not the pytest suite.**
- `src/dcqc/suites/` — one suite class per file type, composed by inheritance.

`tests/` is the pytest suite. See `tests/CLAUDE.md`.

### Rolled-up subdirectories

- **`docs/`** — Sphinx site. `docs/api/` is deleted and regenerated by `docs/conf.py:36-53` on *every* build, so never hand-edit it. `docs/readme.md`, `contributing.md`, `authors.md`, `changelog.md` are MyST `{include}` shims — edit the corresponding file at the repo root instead. `docs/index.md` and `CHANGELOG.md` are still untouched PyScaffold placeholders.
- **`src/docker/`** — `Dockerfile` installs `${TARBALL_PATH}[all]` from `dist/`; its `CMD` is only an `import dcqc` smoke test, so you must pass a real `dcqc ...` command when running the image. `build.sh` wraps the build.
- **`.github/`** — CI builds the distribution once in the `prepare` job and every later job reuses that artifact, so the tested package is byte-identical to the published one. `docker-publish` fires on *every* push to main, not just tags.
- **`examples/`** — three runnable end-to-end pipelines (`internal.sh`, `external.sh`, `docker.sh`) plus the manifests they read. README.md references them by name, so keep the two in step when you change either. All three need `SYNAPSE_AUTH_TOKEN`; `external.sh` also needs `docker`, `jq` and the `synapse` CLI, and `docker.sh` needs only `docker`. Each script writes to a `<name>_example/` directory at the repo root (`internal_example/`, `external_example/`, `docker_example/`, all gitignored) and refuses to start if that directory exists, because the `dcqc` commands will not overwrite their output. `examples/data.csv` has no `url` column — it is a file to run `qc-file` *on*, not a manifest.

## Constraints

- **`tox` and bare `pytest` do not run the same tests.** setup.cfg `[tool:pytest] addopts` sets `-m "not slow"`; tox.ini `[testenv] commands` overrides it with `-m ""`. Slow tests hit live Synapse and need `SYNAPSE_AUTH_TOKEN` — because there is no fixture that skips when the token is absent (that was tried and deliberately removed in `eb67219`).
- **Never work on `main`** (CONTRIBUTING.md "Implement your changes"). Branch first.
- **Adding a runtime dependency means editing two files.** Add it to `install_requires` in setup.cfg *and* to `docs/requirements.txt`, or the API docs fail to build — the comment above `install_requires` in `[options]` says so.
- **Do not drop the explicit `click>=8.0` dependency.** Newer Typer no longer pulls Click in transitively, and `tests/test_main.py` imports `click.testing` directly (setup.cfg `[options] install_requires`).
- **Do not loosen `requests`.** 2.22.0 and 2.23.0 have security issues (setup.cfg `[options] install_requires`).
- **Do not touch the `[pyscaffold]` block** in setup.cfg — it is consumed by PyScaffold's updater, and the block itself says "This will be used when updating. Do not change!".
- **Do not remove the `sphinx-apidoc` call from `docs/conf.py`.** Read the Docs does not run apidoc itself, so the module reference disappears without it (conf.py:23-29).
- **Do not rename the `SYNAPSE_AUTH_TOKEN` CI secret.** That rename was made and reverted in `1cd983a`.
- **Version lives in two places.** setup.cfg `[metadata] version` carries the static value, while setup.py and `[tool.setuptools_scm]` also derive one from git. CI needs `fetch-depth: 0` for that. Bump setup.cfg when releasing; the tag alone is not enough.

## Anti-Patterns — Do NOT

- **Do NOT commit an intentionally broken path or command to force a test failure** — because `fd09758` had to revert exactly that in `tiff_tag_306_date_time_test.py`, where the real argument `f"'{path.name}'"` had been swapped for a literal `"bad_file.file"`.
- **Do NOT migrate the dataclasses to pydantic** — because it was tried and abandoned; it breaks `test_that_paths_are_unchanged_when_not_using_serialize_paths_relative_to`. The reason is recorded at `src/dcqc/target.py:138-141`.
- **Do NOT change the test name in `test_that_skipped_tests_are_skipped_when_building_suite_from_tests`** — it must stay `LibTiffInfoTest`; swapping it was reverted in `9971463`.
- **Do NOT add auth-token presence checks to CI** — added in `39e4795`, removed in `eb67219`.
- **Do NOT re-enable Windows in the CI matrix casually** — it has been toggled on and off repeatedly and is currently parked behind ORCA-348.
- **Do NOT reword a `status_reason` string without grepping the tests** — several are asserted verbatim, for example `tests/test_internal_tests.py:153` pins "FASTQ files do not have the same number of lines".
- **Do NOT rename a `BaseTest`, `SuiteABC`, or `BaseTarget` subclass casually** — the serialized `"type"` field is the bare class name with no aliasing or migration table, so every previously written JSON and every `nf-dcqc` run that references it breaks.

## Known Broken / Stale

Do not treat these as things you introduced, and do not "fix" them as drive-by changes.

- The confirmed bugs in the object model are listed in `src/dcqc/CLAUDE.md`.
- **Issue #71** — `tests/test_acceptance.py::test_json_report_generation` fails on every CI run with `UnsupportedProtocol: protocol 'syn' is not supported`, because tox installs from the built wheel.
- `.readthedocs.yml` still declares Python 3.9 under the deprecated `python.version` key.
- setup.cfg `[tool:pytest] testpaths` is `tests demos`, but there is no `demos/` directory.
- `src/docker/build.sh` pins `tox~=3.0` while CI uses `tox!=3.0`.

## Related Systems

- **[nf-dcqc](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc)** — the Nextflow workflow that consumes this package's JSON and actually executes external tests. Its default branch is `dev`, not `main`. External-test changes can only be validated end to end by building the image with `src/docker/build.sh` and running nf-dcqc with the `local` profile (CONTRIBUTING.md "Testing Your Changes").
- **fs-synapse** — supplies the `syn://` fsspec protocol. Synapse access goes through it; this repo no longer has its own filesystem layer.
- **Tool containers** referenced by external tests: `quay.io/sagebionetworks/{libtiff,bftools}`, `quay.io/biocontainers/coreutils`, `ghcr.io/sage-bionetworks-workflows/{tifftools,htan-h5ad-validator}`.
- Jira is the tracker of record (`DPE-` current, `ORCA-` historical) at `https://sagebionetworks.jira.com`.
