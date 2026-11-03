# CLAUDE.md — `tests`

The pytest suite. Not to be confused with `src/dcqc/tests/`, which is production QC-check code.

## `pytest` and `tox` run different sets

setup.cfg `[tool:pytest] addopts` puts `-m "not slow"` there, so a bare `pytest` **skips every slow test**. tox.ini `[testenv] commands` overrides it with `-m ""` and runs them. Slow tests hit live Synapse.

`slow` is the only registered marker (setup.cfg `[tool:pytest] markers`). A commented-out `acceptance` marker was removed from that list; do not reintroduce it — the end-to-end test `test_acceptance.py::test_json_report_generation` is marked `slow`.

**The suite runs in one process.** The `testing` extra in setup.cfg is deliberately small — pytest, pytest-cov, pytest-mock and docker. pytest-xdist, hypothesis and nbmake were removed: xdist was installed but never used, because its `--numprocesses` flag sat commented out in `[tool:pytest] addopts`, and hypothesis and nbmake had no callers at all. Do not add xdist back without first isolating the shared state under **Side effects to be aware of** — `tests/outputs/` and the module-level `outputs` set that `get_output` guards (`conftest.py:36,158-165`) all assume a single process, so workers would race on the same paths.

There is **no fixture that skips when `SYNAPSE_AUTH_TOKEN` is missing**; asserts on the token in the `tests/test_acceptance.py` fixture were added in `39e4795` and deliberately removed in `eb67219`. A slow test without credentials errors rather than skipping.

## Fixtures (`conftest.py`)

All function-scoped. They form a chain — `get_data` feeds `test_files`, which feeds `test_targets`, which feeds `test_suites`. Request the highest-level one you need rather than rebuilding it.

| Fixture | Returns |
|---|---|
| `get_data` | factory `(filename) -> Path` under `tests/data`; raises if absent |
| `get_output` | factory `(filename) -> Path` under `tests/outputs`; **raises if another test in the session already claimed that name** |
| `test_files` | `dict[str, File]` — 15 keyed files; all but `good_fastq` and `good_compressed_fastq` carry hardcoded md5 metadata |
| `test_targets` | `dict[str, SingleTarget]` wrapping each of the above |
| `test_suites` | `dict[str, SuiteABC]` via `SuiteABC.from_target`. Has no entry for the two FASTQ targets, because `FastqSuite` rejects a `SingleTarget` |
| `run_id` | session-stable id string |
| `mocked_suites_single_targets` | 4 `MagicMock` suites returning GREEN/RED/AMBER/NONE in that order |

Every test must use a **unique** `get_output` name, enforced by a module-level set.

Fixture keys follow `good_<type>` for valid files and `<reason_it_is_bad>_<type>` for invalid ones (established in PR #52): `good_txt`, `good_tiff`, `wrong_file_type_and_md5_txt`, `invalid_xml_tiff`, `htan_bad_h5ad`, and so on.

`RUN_ID` deliberately replaces the colon in its ISO timestamp, because Synapse folder names only allow `[A-Za-z0-9 .+'()_-]` (`conftest.py:32`).

`mocked_suites_single_targets` returns statuses in an order that must stay in lockstep with `tests/data/test_output.csv`.

## Helpers outside conftest — reuse these

- **`docker_enabled_test`** (`test_external_tests.py:49-54`) — the project's Docker gate. It skips when the platform is not Linux. Every Docker-touching test must use it. Note it does **not** check whether the daemon is running, so on a Linux box with no reachable Docker daemon the tests fail with `DockerException` rather than skipping.
- **`DockerExecutor`** (`test_external_tests.py:57-88`) — runs a command in a container with the file bind-mounted read-only, wrapping it in `sh -c` (necessary because several `Process` commands contain shell pipes). Do not hand-roll `docker` SDK calls.
- **`run_command` / `check_command_result`** (`test_main.py:18-32`) — the CliRunner pair every CLI test uses.
- **`create_duplicate_files` / `remove_staged_files`** (`test_file.py:14-51`) — simulate and clean up `dcqc-staged-*` dirs. **There is no autouse cleanup fixture**; `remove_staged_files()` must be called manually at the end of any test that stages files.

## Test style

- Classes are `Test<ClassUnderTest>` with an `autouse` fixture conventionally named `setup_method` that assigns `self.<name>_target` / `self.<name>_test`.
- Functions are long full sentences: `test_that_...` for behaviour, `test_for_an_error_when_...` / `test_for_an_error_if_...` for expected raises. `test_main.py` mostly drops this and uses plain `test_<cli_command>`; the exceptions are `test_that_the_package_version_can_be_printed`, `test_pipeline_with_single_targets` and `test_pipeline_with_grouped_targets`.
- Every new test has `# GIVEN`, `# WHEN` and `# THEN` comments. Put `# WHEN` and `# THEN` together above a `pytest.raises` block. Many older tests do not have them; do not add them to an old test as a drive-by change.
- `parametrize` is reserved for pure input-to-expected-classification tables; everything else uses class grouping.
- The external-test exit-code pattern (write `"0"`/`"1"` to temp files, then `mocker.patch.object(test, "_find_process_outputs", ...)`) is repeated for each test. Copy the nearest neighbour, and check whether that test's codes are inverted — see `src/dcqc/tests/CLAUDE.md`.

**A class must start with `Test` to be collected.** pytest silently ignores a class with any other name, so its tests never run.

## `tests/data`

Four distinct categories. Treat them differently.

1. **Generated JSON — regenerate, do not hand-edit.** `file.json`, `target.json`, `test.internal.json`, `test.external.json`, `test.computed.json`, `tests.json`, `suite.json`, `suites.json` all come from `tests/data/generate.py`. **Run it from the repo root** — it emits repo-relative paths via `paths_relative_to=Path.cwd()`, and running it elsewhere changes the fixture shape (that relativity was a deliberate fix in `9c2935d`). The last step, `suites.json`, needs Synapse credentials (`SYNAPSE_AUTH_TOKEN` or `~/.synapseConfig`), because serializing a suite calls `compute_status` -> `compute_tests` -> `target.stage()` (`suite_abc.py:371`) and the inputs name `syn://` files. The seven earlier exports need no credentials. **That staging also puts absolute paths in the output:** a regenerated `suites.json` holds `"local_path": "/tmp/dcqc-staged-.../circuit.tif"` for each file, because `serialize_paths_relative_to` does not recurse (see `src/dcqc/CLAUDE.md`). The committed file holds `null` there. Set those values back to `null` before you commit a regenerated `suites.json`. Note also that `required_tests` is a `set` serialized with `list()` (`suite_abc.py:407`), so its order in a regenerated `suites.json` moves between runs; no test reads that order.
2. **`suites_files/` are hand-maintained *inputs* to `generate.py`, not outputs.** Editing them changes the generated `suites.json`, which `test_main.py`'s `update-csv` test depends on. Their `local_path` values are `null`, which is correct for an unstaged remote file — they used to hold stale machine-specific absolute paths such as `/tmp/dcqc-staged-.../circuit.tif`. Keep the key present and set it to `null`; do not delete it, because `File.from_dict` indexes it directly (`file.py:481`). `metrics` is optional there, because `BaseTest.from_dict` defaults it to `{}` (`base_test.py:140`). Every test entry needs a `status_reason` for the same reason — `BaseTest.from_dict` indexes `dictionary["status_reason"]` (`base_test.py:138`), so omitting it raises `KeyError` and the `suites.json` step of the generator dies. Use `"test failed"` where `status` is `failed` and `""` otherwise, which is what the generated `suites.json` holds.
3. **`tiffinfo/` is a hand-captured real process output triple** — `std_out.txt`, `std_err.txt` (intentionally empty), `exit_code.txt`. Those three filenames are the contract with `ExternalTestMixin._find_process_outputs`; renaming them breaks discovery.
4. **Binary samples are committed as-is** with no generator and no LFS, including three ~11 MB h5ad files. `example.bam`, `example.fastq` and `example.fastq.gz` are 7-byte **placeholders**, not real format files. Fixture md5 checksums are copied into many files. The placeholders hold `foobar\n`, the same bytes as `test.txt`, so all four share `14758f1a...`: it is in `conftest.py:76`, `generate.py:34`, every CSV in `tests/data/` (`files.csv`, `files_ungrouped.csv`, `small.csv`, both `pipeline_*.csv`) and the generated JSON. `circuit.tif`'s `c7b08f6d...` is in `conftest.py:96`, `test_main.py:154,169,186`, the CSVs, `suites_files/suites_1.json` and `suites.json`. **Grep `tests/` for the hex string before changing any fixture byte.**

Note that `files.csv` contains a `syn://` row, so parsing it can touch the network. Its two FASTQ rows share the `dcqc_grouping` value `fastq_pair`, because an ungrouped FASTQ row is an error in `create_targets` and `create_suites`. `files_ungrouped.csv` holds the same rows with no `dcqc_grouping` column and without the two FASTQ rows, for the tests of a manifest without one.

`pipeline_single.csv` and `pipeline_grouped.csv` are the inputs of the two end-to-end CLI tests, `test_pipeline_with_single_targets` and `test_pipeline_with_grouped_targets` in `test_main.py`. They hold only local files, so they need no credentials. `pipeline_grouped.csv` pairs `fastq1.fastq` and `fastq2.fastq.gz`, which are real FASTQ files with different line counts. Thus `PairedFastqParityTest` fails and both rows are RED, and the test asserts that. These manifests also hold copies of the md5 values, so include them when you grep.

## Side effects to be aware of

- `tests/outputs/` is created at conftest import time (gitignored).
- `test_updaters.py` rewrites `tests/data/test_output.csv`, a **committed fixture**, on every run. What it writes is byte-identical today, so `git status` stays clean and only the mtime moves — but change the fixture statuses or `mocked_suites_single_targets` and the suite starts dirtying the working tree. For the same reason, `test_that_csv_updater_writes_test_metrics_keyed_by_test_name` writes to `tmp_path`, so that its non-empty metrics do not go into the tracked fixture.
- Every `CsvParser(stage_files=True)` test now builds its manifest under `tmp_path`, and `CsvParser` stages next to the manifest (`parsers.py:130`), so no test writes `tests/data/staged_files/` any more. A copy left by an older run may still be there; it is invisible to `git status` only because `.gitignore` carries a bare `test.txt` pattern, which is accidental rather than deliberate — that same pattern shadows the tracked `tests/data/test.txt`. Delete it by hand.
- `test_suites.py:24-25` registers `FileType("None", ())` and `FileType("Unpaired", ())` at import time. `FileType` registration is global and duplicates raise, so those two names are taken for the whole session.
- Slow tests create and delete real folders under `syn://syn50696607` and resolve `syn://syn50555279`.

## Known gaps

- `TestH5adHtanValidatorTest`'s exit-code test instantiates `TiffDateTimeTest` (`test_external_tests.py:509,516`), so h5ad status interpretation is untested.
- The `python -m dcqc` versus `dcqc` equivalence test is commented out inside a string literal at `test_main.py:36-42`, parked behind ORCA-349.
