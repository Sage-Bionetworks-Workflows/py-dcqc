# CLAUDE.md — `tests`

The pytest suite. Not to be confused with `src/dcqc/tests/`, which is production QC-check code.

## `pytest` and `tox` run different sets

setup.cfg `[tool:pytest] addopts` puts `-m "not slow"` there, so a bare `pytest` **skips every slow test**. tox.ini `[testenv] commands` overrides it with `-m ""` and runs them. Slow tests hit live Synapse.

`slow` is the only registered marker. `acceptance` is commented out in setup.cfg — do not use it.

There is **no fixture that skips when `SYNAPSE_AUTH_TOKEN` is missing**; token presence checks were added in `39e4795` and deliberately removed in `eb67219`. A slow test without credentials errors rather than skipping.

## Fixtures (`conftest.py`)

All function-scoped. They form a chain — `get_data` feeds `test_files`, which feeds `test_targets`, which feeds `test_suites`. Request the highest-level one you need rather than rebuilding it.

| Fixture | Returns |
|---|---|
| `get_data` | factory `(filename) -> Path` under `tests/data`; raises if absent |
| `get_output` | factory `(filename) -> Path` under `tests/outputs`; **raises if another test in the session already claimed that name** |
| `test_files` | `dict[str, File]` — 15 keyed files with hardcoded md5 metadata |
| `test_targets` | `dict[str, SingleTarget]` wrapping each of the above |
| `test_suites` | `dict[str, SuiteABC]` via `SuiteABC.from_target` |
| `run_id` | session-stable id string |
| `mocked_suites_single_targets` | 4 `MagicMock` suites returning GREEN/RED/AMBER/NONE in that order |

Every test must use a **unique** `get_output` name, enforced by a module-level set.

Fixture keys follow `good_<type>` for valid files and `<reason_it_is_bad>_<type>` for invalid ones (established in PR #52): `good_txt`, `good_tiff`, `wrong_file_type_and_md5_txt`, `invalid_xml_tiff`, `htan_bad_h5ad`, and so on.

`RUN_ID` deliberately replaces the colon in its ISO timestamp, because Synapse folder names only allow `[A-Za-z0-9 .+'()_-]` (`conftest.py:32`).

`mocked_suites_single_targets` returns statuses in an order that must stay in lockstep with `tests/data/test_output.csv`.

## Helpers outside conftest — reuse these

- **`docker_enabled_test`** (`test_external_tests.py:49-54`) — the project's Docker gate. It skips when the platform is not Linux. Every Docker-touching test must use it. Note it does **not** check whether the daemon is running, so a Linux box without Docker errors rather than skipping.
- **`DockerExecutor`** (`test_external_tests.py:57-88`) — runs a command in a container with the file bind-mounted read-only, wrapping it in `sh -c` (necessary because several `Process` commands contain shell pipes). Do not hand-roll `docker` SDK calls.
- **`run_command` / `check_command_result`** (`test_main.py:13-27`) — the CliRunner pair every CLI test uses.
- **`create_duplicate_files` / `remove_staged_files`** (`test_file.py:14-51`) — simulate and clean up `dcqc-staged-*` dirs. **There is no autouse cleanup fixture**; `remove_staged_files()` must be called manually at the end of any test that stages files.

## Test style

- Classes are `Test<ClassUnderTest>` with an `autouse` fixture conventionally named `setup_method` that assigns `self.<name>_target` / `self.<name>_test`.
- Functions are long full sentences: `test_that_...` for behaviour, `test_for_an_error_when_...` / `test_for_an_error_if_...` for expected raises. `test_main.py` drops this and uses plain `test_<cli_command>`.
- `parametrize` is reserved for pure input-to-expected-classification tables; everything else uses class grouping.
- The external-test exit-code pattern (write `"0"`/`"1"` to temp files, then `mocker.patch.object(test, "_find_process_outputs", ...)`) is repeated for each test. Copy the nearest neighbour, and check whether that test's codes are inverted — see `src/dcqc/tests/CLAUDE.md`.

**A class must start with `Test` to be collected.** `test_internal_tests.py:112` defines `class Md5ChecksumTest:` and pytest therefore never runs its two tests — a real, currently-unfixed gap, not a pattern to copy.

## `tests/data`

Four distinct categories. Treat them differently.

1. **Generated JSON — regenerate, do not hand-edit.** `file.json`, `target.json`, `test.internal.json`, `test.external.json`, `test.computed.json`, `tests.json`, `suite.json`, `suites.json` all come from `tests/data/generate.py`. **Run it from the repo root** — it emits repo-relative paths via `paths_relative_to=Path.cwd()`, and running it elsewhere changes the fixture shape (that relativity was a deliberate fix in `9c2935d`).
2. **`suites_files/` are hand-maintained *inputs* to `generate.py`, not outputs.** Editing them changes the generated `suites.json`, which `test_main.py`'s `update-csv` test depends on. They contain stale machine-specific absolute paths such as `/tmp/dcqc-staged-.../circuit.tif` — harmless today because nothing dereferences them, but a trap if you start resolving those paths.
3. **`tiffinfo/` is a hand-captured real process output triple** — `std_out.txt`, `std_err.txt` (intentionally empty), `exit_code.txt`. Those three filenames are the contract with `ExternalTestMixin._find_process_outputs`; renaming them breaks discovery.
4. **Binary samples are committed as-is** with no generator and no LFS, including three ~11 MB h5ad files. `example.bam`, `example.fastq` and `example.fastq.gz` are 7-byte **placeholders**, not real format files. Fixture md5 checksums are duplicated across up to three places: the placeholders share `14758f1a...`, recorded in `conftest.py:76` and `files.csv:9-11`, while `circuit.tif`'s `c7b08f6d...` additionally appears in `test_main.py:133,148,165`. **Grep the hex string before changing any fixture byte.**

Note that `files.csv` contains a `syn://` row, so parsing it can touch the network.

## Side effects to be aware of

- `tests/outputs/` is created at conftest import time (gitignored).
- `test_updaters.py` rewrites `tests/data/test_output.csv`, a **committed fixture**, on every run. What it writes is byte-identical today, so `git status` stays clean and only the mtime moves — but change the fixture statuses or `mocked_suites_single_targets` and the suite starts dirtying the working tree.
- `tests/data/staged_files/` is created by the tests that use `CsvParser(stage_files=True)`. It is invisible to `git status` only because `.gitignore` carries a bare `test.txt` pattern, which is accidental rather than deliberate — that same pattern shadows the tracked `tests/data/test.txt`. Clean it up by hand; nothing removes it.
- `test_suites.py:17-18` registers `FileType("None", ())` and `FileType("Unpaired", ())` at import time. `FileType` registration is global and duplicates raise, so those two names are taken for the whole session.
- Slow tests create and delete real folders under `syn://syn50696607` and resolve `syn://syn50555279`.

## Known gaps

- **`test_acceptance.py::test_json_report_generation` fails on every CI run** — open issue #71, `protocol 'syn' is not supported` under a wheel install. Not something you broke.
- `TestH5adHtanValidatorTest`'s exit-code test instantiates `TiffDateTimeTest` (`test_external_tests.py:509,516`), so h5ad status interpretation is untested.
- The `python -m dcqc` versus `dcqc` equivalence test is commented out inside a string literal at `test_main.py:31-37`, parked behind ORCA-349.
- Multi-target fixtures and their tests are commented out in `conftest.py:185-200` and `test_updaters.py`, pending multi-file target support.
- pytest-xdist is installed but parallelism is off on purpose: at the current test count the overhead makes the suite slower (the commented-out `--numprocesses` line in setup.cfg `[tool:pytest] addopts`). hypothesis and nbmake are declared but unused.
