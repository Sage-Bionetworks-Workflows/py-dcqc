# CLAUDE.md — `src/dcqc/suites`

One suite class per file type. `suite_abc.py` holds the base class and the registry; `suites.py` holds the concrete suites.

## `add_tests` is additive across the MRO, not an override

`list_test_classes` (`suite_abc.py:202-216`) walks `reversed(cls.__mro__)` and unions each class's `add_tests`. So `JsonLdSuite` yields `FileExtensionTest`, `Md5ChecksumTest`, `JsonLoadTest` **and** `JsonLdLoadTest`.

The union is a `set`, so the result is sorted by class name before it is returned (`suite_abc.py:216`). That order is the one that reaches `init_test_classes`, the `"tests"` array of a serialized suite, and `dcqc list-tests`. Do not drop the sort. Without it, the order changes between runs. The cause is not `PYTHONHASHSEED`: a class hashes by `id()`, so the order changes with the memory layout, for example when a different module is imported first.

Suites compose by inheritance. To make a subtype inherit a parent's checks, subclass it — `H5ADSuite(HDF5Suite)`, `OmeTiffSuite(TiffSuite)`, `JsonLdSuite(JsonSuite)`. Writing `add_tests = (...)` expecting to replace the parent's list is wrong.

`del_tests` exists but is never assigned anywhere in `src/`, and for good reason: the loop uses `hasattr`, so a subclass that does not declare its own `del_tests` still re-applies an ancestor's deletion at its own MRO position, which can silently wipe that subclass's `add_tests`. Restructure the hierarchy instead of using it.

## Adding a suite

1. Define the class in `src/dcqc/suites/suites.py`. `src/dcqc/suites/__init__.py` is empty and imports nothing — registration works only because `src/dcqc/__init__.py:19-21` imports this module. A **new** suites module would have to be added there too.
2. Set `file_type = FileType.get_file_type("<NAME>")`, which resolves against the eager `FileType` registry at class-definition time. Register the file type in `src/dcqc/file.py` first if it does not exist.
3. Give a target class only if the suite needs one other than the inherited one, and give it as the type argument of the base class, for example `class FastqSuite(FileSuite[PairedTarget])`. `SuiteABC.__init_subclass__` copies it into the `target_cls` class attribute, with the same helper as `BaseTest` (`dcqc.target.get_target_type_argument`). Do not write a `target_cls =` line in the class body. `SuiteABC` sets a default of `SingleTarget`, so `target_cls` always exists and the import-time check below always runs. `FileSuite` is `FileSuite(SuiteABC[Target])`: it stays generic, so it inherits that default, and a subclass can still give a type argument. Thus only a direct subclass of `FileSuite` (or of `SuiteABC`) can give a type argument. A subclass of `TiffSuite`, for example, is not generic and inherits `SingleTarget`. A type argument that is not a `BaseTarget` subclass, for example a Union, raises `TypeError` at class definition. The helper reads only a base whose origin is a subclass of the anchor class (`SuiteABC` or `BaseTest`), so an unrelated generic base such as `SomeMixin[int]` is ignored. Two bases that both give a target class raise `TypeError`.
4. Optionally set `add_tests`. Several suites omit it (`TSVSuite`, `BAMSuite`, `TXTSuite`, `CSVSuite`, `HDF5Suite`) and just inherit `FileSuite`.
   Every test, inherited ones included, must accept the suite's `target_cls`: the suite's `target_cls` must be the test's `target_cls` (a `BaseTest` class attribute, default `BaseTarget`) or a subclass of it. `SuiteABC.__init_subclass__` checks this and raises `TypeError` at import time, so a `PairedTarget` suite cannot inherit a `SingleTarget` test. The target class is checked as well, by the classmethod `SuiteABC.ensure_accepts_target_cls`: `SuiteABC.from_target` raises `ValueError` when the target is not an instance of the selected suite's `target_cls`, and `CsvParser.create_targets` runs the same check before it stages a file. So a grouped TIFF row or an ungrouped FASTQ row fails in `create-targets`, before any download.
5. A new suites *module* also needs its own `[[tool.mypy.overrides]]` block in pyproject.toml with `disable_error_code = "assignment"`, because subclasses reassign inherited `ClassVar`s.

`SuiteABC` has **no abstract methods** — the contract is class attributes only, so nothing warns you at class definition. Omitting `file_type` is the worst case: it raises inside `get_subclass_by_file_type` and `list_test_classes_by_file_type`, which **breaks the registry for every other suite** and breaks `dcqc list-tests`.

Class naming is genuinely inconsistent — ALL-CAPS acronyms (`TSVSuite`, `BAMSuite`, `TXTSuite`, `CSVSuite`, `HDF5Suite`, `H5ADSuite`) sit next to PascalCase (`JsonSuite`, `JsonLdSuite`, `TiffSuite`, `OmeTiffSuite`, `FastqSuite`). Check `suites.py` and match its neighbours; there is no rule to derive.

## Silent failure modes

- **An unrecognized file type *name* silently falls back to the `"*"` suite.** `get_subclass_by_file_type` takes a `FileType` or a name; given a name it catches the `ValueError` from `FileType.get_file_type` and substitutes `"*"` (`suite_abc.py:252-256`), so the caller asked for one suite and gets a generic `FileSuite`. **This is not reachable from the CLI**, because a typo'd file type raises when the target is built, before any suite lookup. `qc-file` builds `SingleTarget([file])` (`main.py:196`), and `__post_init__` → `validate_files` (`target.py:59`, `:101`) calls `File.get_file_type` (`file.py:331`), which exits with `ValueError: File type (...) not among available options` from `file.py:138`. `create-targets` catches the same error in `CsvParser._plan_targets` and reports `Row N has an unknown file type.` (`parsers.py:218`). `SuiteABC.from_target` also passes a `FileType` object, not a name (`suite_abc.py:152`). Only a library caller that passes a name reaches the fallback. Do not confuse it with the second fallback in the same method (`suite_abc.py:260-264`), which returns `registry["*"]` for a file type that *is* registered but that no suite claims; that one is correct and is covered by `test_that_the_generic_file_suite_is_retrieved_for_an_unpaired_file_type`. The current behaviour is pinned by `test_that_the_generic_file_suite_is_retrieved_for_a_random_file_type` (`tests/test_suites.py:195-197`), so removing the `except` means deleting that test. Whether to remove it is an open decision, not a settled fix.
- **Two suites claiming the same `file_type` collide silently.** The registry is a dict keyed by `file_type.name` (`suite_abc.py:259`); the last one wins, with no warning.
- **Unknown names in `required_tests` / `skipped_tests` are silently dropped,** because the sets are computed with `.intersection(test_names)`. A typo'd `--required-tests` is not rejected.

## Serializing a suite runs QC

`SuiteABC.to_dict()` calls `compute_status()` on its first line (`suite_abc.py:341-342`), which calls `compute_tests()`, which calls `self.target.stage()` and then every test. **Serializing a suite downloads files and executes checks.** There is no side-effect-free way to serialize one, and staging happens on every call even when all statuses are already terminal.

Related asymmetries with `BaseTest`, worth knowing before you copy a pattern across:

- `BaseTest.get_status(compute_ok=True)` takes a flag; `SuiteABC.get_status()` takes none (`suite_abc.py:399-403`), so a suite still at `SuiteStatus.NONE` cannot be read without triggering computation. A suite already carrying a terminal status returns it untouched — and so does `to_dict()`, which still re-runs `compute_tests()` and re-stages the target, but returns the memoized status unchanged.
- `SuiteABC.compute_status` memoizes internally, but the memo check (`suite_abc.py:323`) sits *below* the `compute_tests()` call (`:322`), so staging escapes it while the status derivation at `:325-339` does not. `BaseTest.compute_status` does not memoize at all; `BaseTest.get_status` guards it instead (`base_test.py:98`), so terminal tests never re-run their check.
- `list_test_classes()` returns a tuple, but `list_test_classes_by_file_type()` returns dict values that are lists.
- `init_test_classes()` returns test **instances** despite the name.

## Status derivation

`compute_status` (`suite_abc.py:320-339`) returns on the **first** `TestStatus.ERROR` with `GREY`, so remaining tests are never evaluated and `RED`/`AMBER` are never reported for that suite. Otherwise `RED` (a required test failed) takes precedence over `AMBER` (only optional tests failed).

By default the required set is every test with `tier.value <= 2`, i.e. `FILE_INTEGRITY` and `INTERNAL_CONFORMANCE` only (`suite_abc.py:232`). Tier 3 and 4 checks — including all the PHI-detection tests — are optional unless named explicitly, so they can only produce `AMBER`.

## Skipping is persisted, not re-derived

`skipped_tests` is honoured when `init_test_classes` constructs the tests, and then discarded: `from_dict` rebuilds the test list from JSON and overwrites `suite.tests` (`suite_abc.py:385-390`). A skip survives round-tripping only through the persisted `"status": "skipped"` value.

Likewise, a deserialized test whose JSON already records a terminal status **never re-runs** — only `"pending"` triggers recomputation. Do not expect `compute-test` to refresh a completed result.

`from_tests` requires every test to share one target, of any target class, and it builds a test list via `from_target` only to immediately replace it (`suite_abc.py:160-199`). Because it goes through `from_target`, the target class must still suit the suite for its file type.
