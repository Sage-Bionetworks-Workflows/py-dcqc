# CLAUDE.md — `src/dcqc/tests`

**This directory is production code: one QC check per module. It is not the pytest suite.** The pytest suite is `/tests/`. Modules here use the suffix `*_test.py`; pytest files use the prefix `test_*.py`, and `testpaths` never collects this directory.

When asked to "add a test", first decide which is meant: a QC check belongs here, a unit test belongs in `/tests/`.

## Adding a QC test — the full checklist

CONTRIBUTING.md "Contributing New Tests" now covers registration too, in its "Registering a New Test" subsection.

1. Create `src/dcqc/tests/<snake_case>_test.py`.
2. Subclass `InternalBaseTest` or `ExternalBaseTest`, imported from `dcqc.tests.base_test`. Neither is re-exported from `__init__.py`, so import them from the module directly — every existing test does.
3. Set `tier` to a `TestTier` enum member, never a bare int.
4. Annotate `target: SingleTarget` or `target: PairedTarget`.
5. **Add an import line to `src/dcqc/tests/__init__.py`** (alphabetized, one per test).
6. **Add the class to a suite's `add_tests` tuple in `src/dcqc/suites/suites.py`**, or nothing will ever run it. See `src/dcqc/suites/CLAUDE.md`.

## Required attributes fail late, not at class definition

`tier`, and for external tests `pass_code` / `fail_code` / `failure_reason_location`, are **annotations with no defaults**. Omitting one is silent at import and class-definition time; you get an `AttributeError` only when something reads it — `to_dict()`, the default-required-tests calculation, `dcqc list-tests`, or status interpretation.

`failure_reason_location` is stringly typed and must be exactly `"std_out"` or `"std_err"`. A typo raises `KeyError` **only on a failing test**, so it passes CI against healthy files.

Also note: the `BaseTest` docstring claims a `ValueError` when a single-file test gets a multi-file target. **That validation does not exist.** Arity is enforced only by `SingleTarget.__post_init__` and `PairedTarget.__post_init__`.

## Internal tests

Implement `compute_status()` returning `TestStatus.PASS` or `TestStatus.FAIL`. On the failure path, set `self.status_reason` to a user-facing explanation before returning — that string reaches the `suites.json` report and the output CSV.

Several `status_reason` strings are asserted verbatim by unit tests (for example `tests/test_internal_tests.py:204`). Grep before rewording one.

## External tests

`py-dcqc` never invokes Docker or `subprocess` in production code. It only emits a `Process` descriptor; *nf-dcqc* executes it. You therefore cannot fully test an external test from this repo alone — see CONTRIBUTING.md "Testing Your Changes".

`ExternalBaseTest` is `class ExternalBaseTest(ExternalTestMixin, BaseTest)`. **The MRO order is load-bearing and asserted** by `tests/test_external_tests.py:14-21`; reversing it silently breaks `compute_status` dispatch.

`generate_process()` follows the same three steps in every existing test:

1. `path = self.target.file.stage()` — mandatory; the container needs a local file.
2. Build `command_args` using **`path.name` only**, never the full path, because the file is mounted at the container's working directory.
3. Return `Process(container=..., command_args=...)`.

Conventions to match:

- Filenames are hand-quoted as `f"'{path.name}'"`, not passed through `shlex.quote`. A filename containing a single quote breaks the command.
- Several commands contain a bare `|` as a list element, so the executor must run them through a shell. `Process.command` merely space-joins.
- `Process` defaults to `cpus=1`, `memory=2` (GB).

### Exit codes are inverted for the grep-style tests

| `pass_code` / `fail_code` | Tests |
|---|---|
| `0` / `1` | `LibTiffInfoTest`, `BioFormatsInfoTest`, `OmeXmlSchemaTest`, `H5adHtanValidatorTest` |
| **`1` / `0`** | `GrepDateTest`, `TiffDateTimeTest`, `TiffTag306DateTimeTest` |

The inversion is correct: these wrap `grep`/`jq`, where "no match" (exit 1) is the desired outcome for PHI detection. Any code that is neither `pass_code` nor `fail_code` becomes `TestStatus.ERROR`.

**`GrepDateTest` is orphaned — it is the live example of skipping step 7 above.** It is imported in `__init__.py:10`, so it registers and deserializes fine, but it appears in no suite's `add_tests` (`suites.py` attaches only the other two date tests to `TiffSuite`). It therefore never shows up in `dcqc list-tests`, and no CSV manifest can trigger it; only the library and `tests/test_external_tests.py:268-324` reach it. `tests/data/suites.json` still contains a `GrepDateTest` entry inside a `TiffSuite`, which is stale for the same reason. Do not treat its absence from `list-tests` as a bug in the registry.

Prefer contributing a tool whose failure and error exit codes differ. Many current tests return the same code for both, so an error is reported as a failure (CONTRIBUTING.md "Contributing External Tests", item 9).

### Status computation reads the current working directory

`ExternalTestMixin.compute_status` reads `./std_out.txt`, `./std_err.txt` and `./exit_code.txt` from `Path(".")` and **ignores the target entirely** (`base_test.py:208-234`). Those three filenames are a contract with nf-dcqc — renaming them breaks the pipeline and `tests/data/tiffinfo/`.

If the files are absent, `FileNotFoundError` propagates and crashes `dcqc compute-test`; it does not degrade to `TestStatus.ERROR`.

Serialized external tests deliberately **omit** their `Process` — the override is commented out at `base_test.py:250-255`, and `dcqc create-process` regenerates it on demand.

## Naming

Module names are `<snake_case>_test.py`, but the existing set is inconsistent: `jsonld_load_test.py` versus `json_load_test.py`, and `tiff_tag_306_date_time_test.py` splits the number. Class names are inconsistent too — `H5adHtanValidatorTest` uses lowercase `ad` while the corresponding suite is `H5ADSuite`. Match the neighbouring files rather than "correcting" them.

## Duplicated constants

Keep these in sync when touching them: `quay.io/sagebionetworks/bftools:latest` appears in `bioformats_info_test.py` and `ome_xml_schema_test.py`; `ghcr.io/sage-bionetworks-workflows/tifftools:latest` appears in `tiff_date_time_test.py` and `tiff_tag_306_date_time_test.py`.

The odd quoting at `tiff_date_time_test.py:28` (`"'.[].ifds[].tags[]'.data"`, with `.data` outside the quotes) looks wrong but determines the current exit codes. Do not change it without re-running the Docker tests.
