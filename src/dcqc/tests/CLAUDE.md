# CLAUDE.md — `src/dcqc/tests`

**This directory is production code: one QC check per module. It is not the pytest suite.** The pytest suite is `/tests/`. QC checks here use the suffix `*_test.py`; pytest files use the prefix `test_*.py`, and `testpaths` never collects this directory. The one module that is not a QC check is `constants.py`, which holds the container images.

When asked to "add a test", first decide which is meant: a QC check belongs here, a unit test belongs in `/tests/`.

## Adding a QC test — the full checklist

ARCHITECTURE.md "Contributing New Tests" now covers registration too, in its "Registering a New Test" subsection.

1. Create `src/dcqc/tests/<snake_case>_test.py`.
2. Subclass `InternalBaseTest` or `ExternalBaseTest`, imported from `dcqc.tests.base_test`. Neither is re-exported from `__init__.py`, so import them from the module directly — every existing test does.
3. Set `tier` to a `TestTier` enum member, never a bare int.
4. Give the target class the test accepts as the type argument of the base class, for example `InternalBaseTest[SingleTarget]`. Use `SingleTarget` if it uses `self.target.file`, `PairedTarget` if it needs exactly two files, or `BaseTarget` if it only loops over `self.target.files` and accepts any target (`Md5ChecksumTest`, `FileExtensionTest`). This one value does two jobs. mypy reads it as the type of `self.target`. `BaseTest.__init_subclass__` copies it into the `target_cls` class attribute, which `SuiteABC.__init_subclass__` checks against the `target_cls` of each suite at import time (`SuiteABC.ensure_tests_match_target_cls`, `suite_abc.py:137`), for every test the suite lists, inherited ones included. It raises `TypeError` unless the suite's `target_cls` is a subclass of the test's, so a `BaseTarget` test fits every suite. Do not also write a `target:` annotation or a `target_cls =` line in the class body — that brings back the two copies that can disagree. A type argument that is not a `BaseTarget` subclass, for example a Union, raises `TypeError` at class definition. A subclass of a concrete test inherits its parent's `target_cls`.
   The `Target` type variable is invariant, so for mypy `BaseTest[SingleTarget]` and `BaseTest[BaseTarget]` are unrelated types. A list with no annotation that holds tests with different type arguments is inferred as `list[object]`, and calling a `BaseTest` method on an item fails type checking. Annotate such a list as `list[BaseTest]`, as `test_list` and `suite_tests` in `tests/data/generate.py:56,60` are.
5. **Add an import line to `src/dcqc/tests/__init__.py`** (alphabetized, one per test).
6. **Add the class to a suite's `add_tests` tuple in `src/dcqc/suites/suites.py`**, or nothing will ever run it. See `src/dcqc/suites/CLAUDE.md`.

## Required attributes fail late, not at class definition

`tier`, and for external tests `pass_code` / `fail_code` / `failure_reason_location`, are **annotations with no defaults**. Omitting one is silent at import and class-definition time; you get an `AttributeError` only when something reads it — `to_dict()`, the default-required-tests calculation, `dcqc list-tests`, or status interpretation.

`failure_reason_location` is stringly typed and must be exactly `"std_out"` or `"std_err"`. A typo raises `KeyError` **only on a failing test**, so it passes CI against healthy files.

Also note: the `BaseTest` docstring claims a `ValueError` when a single-file test gets a multi-file target. **That validation does not exist.** Arity is enforced only by `BaseTarget.__post_init__`, which calls `BaseTarget.validate_files` with the `n_files` of the target class.

## Internal tests

Implement `compute_status()` returning `TestStatus.PASS` or `TestStatus.FAIL`. On the failure path, set `self.status_reason` to a user-facing explanation before returning — that string reaches the `suites.json` report and the output CSV.

A test can also record extra values in `self.metrics`, a dict that `BaseTest.__init__` sets to `{}`. Set it inside `compute_status()`. The values must be JSON-serializable. They are written to `suites.json` and, keyed by test name, to the `dcqc_metrics` column of the output CSV. `Md5ChecksumTest` is the example: only on the failure path, it records `md5_checksum` as a dict that maps the URL of each file that does not match to its computed checksum.

Several `status_reason` strings are asserted verbatim by unit tests (for example `tests/test_internal_tests.py:274`). Grep before rewording one.

## External tests

`py-dcqc` never invokes Docker or `subprocess` in production code. It only emits a `Process` descriptor; *nf-dcqc* executes it. You therefore cannot fully test an external test from this repo alone — see CONTRIBUTING.md "Testing Your Changes".

`ExternalBaseTest` is `class ExternalBaseTest(ExternalTestMixin[Target])` (`base_test.py:289`), and the mixin itself subclasses `BaseTest[Target]` (`base_test.py:216`), so the MRO is `ExternalBaseTest, ExternalTestMixin, BaseTest, ...`. **The mixin must come before `BaseTest`**, because its `compute_status` overrides the base one; `tests/test_external_tests.py:14-21` asserts this for every external test. Do not add `BaseTest` back as a second base of a test class — listing it before the mixin is now an MRO error.

`generate_process()` follows the same three steps in every existing test:

1. `path = self.target.file.stage()` — mandatory; the container needs a local file.
2. Build `command_args` using **`path.name` only**, never the full path, because the file is mounted at the container's working directory.
3. Return `Process(container=..., command_args=...)`, with the container taken from `constants.py` — see Container images.

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

**`GrepDateTest` is orphaned — it is the live example of skipping step 6 above.** It is imported in `__init__.py:10`, so it registers and deserializes fine, but it appears in no suite's `add_tests` (`suites.py` attaches only the other two date tests to `TiffSuite`). It therefore never shows up in `dcqc list-tests`, and no CSV manifest can trigger it; only the library and `tests/test_external_tests.py:268-324` reach it. `tests/data/suites.json` still contains a `GrepDateTest` entry inside a `TiffSuite`, which is stale for the same reason. Do not treat its absence from `list-tests` as a bug in the registry.

Prefer contributing a tool whose failure and error exit codes differ. Many current tests return the same code for both, so an error is reported as a failure (ARCHITECTURE.md "Return Codes", under "Contributing External Tests").

### Status computation reads the current working directory

`ExternalTestMixin.compute_status` reads `./std_out.txt`, `./std_err.txt` and `./exit_code.txt` from `Path(".")` and **ignores the target entirely** (`base_test.py:235-275`). Those three filenames are a contract with nf-dcqc — renaming them breaks the pipeline and `tests/data/tiffinfo/`.

If the files are absent, `FileNotFoundError` propagates and crashes `dcqc compute-test`; it does not degrade to `TestStatus.ERROR`.

Serialized external tests deliberately **omit** their `Process` — the override is commented out at `base_test.py:277-282`, and `dcqc create-process` regenerates it on demand.

The base class does not read `metrics` from the container. `_interpret_process_outputs()` reads only the exit code, `std_out` and `std_err`, so `metrics` stays `{}` unless the class overrides `compute_status()` and fills it, for example from one JSON object on stdout. That needs no change to nf-dcqc, which already keeps `std_out.txt` (ARCHITECTURE.md "Creating the Test Class").

## Naming

Module names are `<snake_case>_test.py`, but the existing set is inconsistent: `jsonld_load_test.py` versus `json_load_test.py`, and `tiff_tag_306_date_time_test.py` splits the number. Class names are inconsistent too — `H5adHtanValidatorTest` uses lowercase `ad` while the corresponding suite is `H5ADSuite`. Match the neighbouring files rather than "correcting" them.

## Container images

Every container image lives in `constants.py`, one module-level constant per image. No test module holds an image literal — a new external test imports its constant from there, and adds one if the image is new.

Two images are shared: `BFTOOLS_CONTAINER` by `bioformats_info_test.py` and `ome_xml_schema_test.py`, `TIFFTOOLS_CONTAINER` by `tiff_date_time_test.py` and `tiff_tag_306_date_time_test.py`. Changing either constant changes both tests.

The odd quoting at `tiff_date_time_test.py:28` (`"'.[].ifds[].tags[]'.data"`, with `.data` outside the quotes) looks wrong but has no effect: `sh` joins it into the same word as `'.[].ifds[].tags[].data'`, and both forms give the same exit codes in the tifftools container. You can quote the whole filter, but re-run the Docker tests after you change any command.
