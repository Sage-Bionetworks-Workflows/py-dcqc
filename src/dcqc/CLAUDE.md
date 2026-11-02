# CLAUDE.md — `src/dcqc`

Core object model and CLI. See the root CLAUDE.md for stack, commands, and the end-to-end data flow. Subpackages `tests/` and `suites/` have their own CLAUDE.md.

## Two registries, opposite behaviour

**`FileType` is eager.** Constructing a `FileType` registers it as a side effect (`file.py:63`), so the 12 built-in types are bare module-level statements at `file.py:144-155`. Registering a duplicate name raises `ValueError` at import time (`file.py:106-108`). `importlib.reload(dcqc.file)` does not hit this, because the class body runs again and creates a new, empty `_registry` (`file.py:35-36`); but any code that still holds the old `FileType` class then sees a different registry. `__init__` validates the extensions before it registers anything (`_validate_file_extensions`, `file.py:65-96`), so **a single extension must carry its trailing comma** — a bare string such as `".tsv"`, or a collection holding a non-string, raises `TypeError` at import time. A `str` satisfies the declared `Collection[str]`, so mypy will not catch the missing comma for you; this guard is the only thing that does. Lookup is case-insensitive but `FileType.name` preserves case, and the suite registry keys off that original case.

**An empty extension tuple is deliberately valid**, because `FileType("*", (), ...)` (`file.py:144`) needs one — do not make `_validate_file_extensions` reject an empty collection, or the package fails at import. Any file with no `file_type` metadata falls back to `"*"` (`file.py:263`) and lands in `FileSuite`, so `FileExtensionTest.compute_status` passes over a file type that declares no extensions (`tests/file_extension_test.py:30-31`). Before that guard every untyped file failed a tier 1 check with the unactionable reason `File extension does not match one of: ()`.

**`BaseTest`, `SuiteABC` and `BaseTarget` are lazy.** `SubclassRegistryMixin.list_subclasses` (`mixins.py:153-177`) walks `__subclasses__()` **recursively**, so the full transitive subclass tree is registered and deduped — but **a class exists only if its module has been imported.** There is no importlib scan, no entry point, no decorator. `src/dcqc/__init__.py:19-21` imports `tests`, `suite_abc` and `suites` for exactly this reason, and carries `# isort: skip_file` at line 3 because the import order avoids a circular import. Do not reorder it.

**Two list methods, and name resolution must use the concrete one.** `list_subclasses` returns the whole tree, abstract intermediates included — `ExternalTestMixin`, `InternalBaseTest` and `ExternalBaseTest` are all in it. `list_concrete_subclasses` (`mixins.py:190-207`) drops anything with an unimplemented `@abstractmethod`, via `inspect.isabstract`. Every lookup by class name goes through the latter: `get_subclass_by_name` (`mixins.py:210`) and all three maps in `JsonParser.get_class` (`parsers.py:405-411`). Do not switch one of those back to `list_subclasses`, or a `"type"` of `"ExternalTestMixin"` resolves, and the failure moves to `test_cls(target)` at `base_test.py:134` as `TypeError: Can't instantiate abstract class ... 'generate_process'` instead of a `ValueError` about an unrecognized type. Guards: `tests/test_parsers.py::test_for_an_error_when_parsing_an_abstract_type` and the two abstract-name tests at `tests/test_internal_tests.py:19-30`. The lookups by file type (`SuiteABC.list_test_classes_by_file_type`, `suite_abc.py:219`, and `get_subclass_by_file_type`, `suite_abc.py:248`) still use `list_subclasses()`; that is safe only because no suite is abstract (see below).

Use `list_subclasses` only for introspection over the tree itself, for example `tests/test_external_tests.py:14-21`, which checks the MRO of every subclass of `ExternalTestMixin`.

Registry gotchas that fail silently:

- The base class is not in its own subclass list — `BaseTarget.get_subclass_by_name("BaseTarget")` raises.
- A new registry root must implement `get_base_class()` (`mixins.py:149`), because `get_subclass_by_name` always resolves through the base, never through `cls`.
- `isabstract` catches only an unimplemented `@abstractmethod`. `SuiteABC` declares none, so no suite is ever filtered, and an intermediate class that implements everything stays in the concrete list.
- **A class whose `__init_subclass__` raises is still in `__subclasses__()`** until it is garbage collected, because `type.__new__` adds it before `__init_subclass__` runs. Changing the order of the `super().__init_subclass__()` call does not help. A check that raises must call `cls.mark_registration_failed()` first, as `BaseTest` and `SuiteABC` do; `list_subclasses` then leaves the class out. Without the mark, a failed suite can take the place of a real suite in `get_subclass_by_file_type`.

## Serialization

`SerializableMixin` (`mixins.py:19`) gives you `to_dict()` for free, but **only if the subclass is a dataclass** — the generic implementation calls `dataclasses.fields(self)`. `File`, `Process` and `BaseTarget` are dataclasses. `BaseTest` and `SuiteABC` are not, so they hand-write `to_dict()`. Add a non-dataclass subclass without overriding `to_dict` and you get `TypeError: must be called with a dataclass type or instance`.

To include a `@property` in the output, list its name in `_serialized_properties` (`mixins.py:21`), as `File` does with `["name", "local_path"]`.

### `"type"` means two different things

| Class | `"type"` holds |
|---|---|
| `File` | the **FileType name** (`"TIFF"`, `"JSON-LD"`) |
| `BaseTarget`, `BaseTest`, `SuiteABC` subclasses | the **class name** |
| `Process` | no `type` key at all — it cannot round-trip through `JsonParser` |

`JsonParser.get_class` (`parsers.py:403-426`) probes targets, then tests, then suites, then FileType names. **Never give a new `FileType` the same name as a Test, Suite or Target class** — the class wins and polymorphic dispatch silently resolves to the wrong thing.

### Rules that are easy to violate

- **`BaseTest.from_dict` mutates its argument** (`base_test.py:128` pops `"type"`), unlike every other `from_dict`, which deepcopies first. Calling it twice on the same dict raises `KeyError: 'type'`. It also keeps a reference to the `metrics` dict of its input, not a copy.
- **`serialize_paths_relative_to` must be called before `to_dict`, and it does not recurse.** `serialize_value` calls `to_dict()` on nested objects without propagating the setting (`mixins.py:63`), so only top-level paths get relativized. A nested `File` keeps its absolute `local_path` (for example `/tmp/dcqc-staged-.../circuit.tif`). This is why a `suites.json` regenerated by `tests/data/generate.py` holds such absolute paths. The committed copy holds `null` there.
- **A property that raises serializes as `null`,** not as an error — `mixins.py:105-108` swallows every exception. This is how an unstaged `File` gets `"local_path": null`.
- **`Process` round-trips lossily.** `command` is emitted space-joined and re-split with `shlex.split`, which strips the hand-written quotes around filenames.
- **`BaseTarget.from_dict` passes the file list as one argument** — `target_cls(files, id=id)` (`target.py:181`). Do not "tidy" it into `target_cls(*files, id=id)`. The constructor is `(files, id=None)`, so unpacking put the second file in the `id` position and every `PairedTarget` failed to load with `TypeError: got multiple values for argument 'id'`. That was the bug fixed in `caacef7`; the guard is `tests/test_target.py::test_that_a_paired_target_can_be_saved_and_restored_without_changing`. `files` must be a list for every subclass, also for `SingleTarget` — `__post_init__` raises `TypeError` for a lone `File` (`target.py:48-61`).
- **The file rules of a target are in one place, `BaseTarget.validate_files`** (`target.py:68`). It checks the count against the `n_files` class attribute (`SingleTarget` 1, `PairedTarget` 2, `BaseTarget` `None` = any count but at least one), and then that all files have the same file type. It returns messages that start with "has", and raises only for an unknown file type, so the parser checks the file types first. `__post_init__` raises a `ValueError` that puts the class name in front, and `CsvParser._check_plan` puts the rows in front. A new target class sets only `n_files`. Do not add a second count or file-type check in a subclass `__post_init__`. `get_file_type` is implemented one time, in `BaseTarget`.
- **`from_dict_prepare`** (which validates `"type"` against the class name) is called only by `BaseTarget.from_dict`. Of the other four `from_dict` implementations, `BaseTest.from_dict` and `SuiteABC.from_dict` resolve `"type"` with `get_subclass_by_name` (an unknown name raises `ValueError`) but never compare it to `cls`; `File.from_dict` and `Process.from_dict` do no type checking.
- `File.from_dict` requires a `local_path` key and discards the serialized `name`, because `name` is a computed property.
- Use the `SerializedObject` alias (`mixins.py:12`) in signatures rather than a raw dict type.

## Reusable utilities — use these, do not reimplement

- `dcqc.utils.is_url_local(url)` — local means a `file://` prefix or no `://` at all. Deliberately permissive; the real guard is `File._validate_url`, which rejects host-bearing `file://host/path` forms (added in PR #72). The docstring at `utils.py:8-13` explains the split. Do not tighten one without the other.
- `File.stage(destination=None, overwrite=False) -> Path` — the only correct way to get a usable local path. Reuses an existing staged copy, otherwise creates a `mkdtemp(prefix="dcqc-staged-")`. With no destination, a set `_local_path` is returned as-is (`file.py:427-429`). With a destination, a local file is **symlinked** rather than copied only when `_local_path` is already set (`file.py:458`); a local file that has never had `local_path` accessed falls through to `fs.get()` and is copied.
- `File.already_staged() -> list[Path]` — returns a list, not an `Optional[Path]`; empty means not staged. It globs the whole temp dir by file name only, so a leftover copy from a *previous run* is silently reused, and more than one match raises `FileExistsError` to pre-empt a Nextflow name collision (added in PR #43). This also applies to a **local** file: `stage()` with no destination checks `already_staged()` when `_local_path` is not set, so a local file that has the same name as a leftover copy is replaced by that copy. See Known bugs.
- `File.get_metadata(key)` — raises a helpful `KeyError`; prefer it to `file.metadata[key]`.
- `File.is_file_local()` returns `_local_path is not None` (`file.py:378`), so it is `False` for a local URL until `local_path` is first read. `File.local_path` fills `_local_path` from `fs_path` for a local URL (`file.py:291-292`), and **raises** `FileNotFoundError` only for a remote file that is not staged. Check `is_url_local()` or `is_file_local()` before you read `local_path` on a remote file.
- `File.name` issues an `fs.info()` network call on remote files, then caches.
- `BaseTest.import_module(name)` — use for optional extras instead of a top-level import, so the error tells the user to `pip install dcqc[all]`.
- `JsonParser.from_dict(dictionary)` — the polymorphic factory. Use it when the concrete class is not known.
- `list_concrete_subclasses()` — the registry list to build a name lookup from. `list_subclasses()` also holds the abstract intermediates; see the registry section above.
- `JsonReport(paths_relative_to=None)` with `.generate()`, `.save()`, `.save_many()`. All accept fsspec URLs. `save` refuses to overwrite unless told.
- `CsvParser(path, stage_files=False)` — `create_targets` and `create_suites` return **generators**, not lists. `list_rows()` indexes from 1. `create_targets` and `create_suites` read and check every row, and every `dcqc_grouping` group, before they stage a file, so a bad manifest fails before any download. The checks include the suite target class, so an ungrouped FASTQ row fails in `create_targets` too. All checks are in `_plan_targets`, which collects every error into one `ValueError`. `create_suites` is `create_targets` plus one `SuiteABC.from_target` call for each target, and it builds every suite before it yields the first one. The single-row targets come first, then the groups.
- **`CsvParser.list_rows_and_files()` (`parsers.py:102`) is the single source of the URL of a manifest row.** It yields `(index, row, file)`, where `row` still has its `url` column and `file.url` is relative to the manifest directory. `create_targets`, `create_suites` and `CsvUpdater.update` all go through it. Do not pair `list_rows()` with your own `File`: that duplicate was the `update-csv` `KeyError: 'test.txt'` bug, where a manifest of relative local paths in another directory could not be joined to its suites. Every `syn://` fixture hid it, so the guard is `tests/test_updaters.py::test_that_csv_updater_joins_a_manifest_of_relative_local_paths`.
- MD5 chunking (`Md5ChecksumTest._compute_md5_checksum`, `md5_checksum_test.py:37-43`) and compression-agnostic FASTQ opening (`paired_fastq_parity_test.py:48-62`) already exist.

## Naming traps

- The base classes are `BaseTest`, `BaseTarget` — but `SuiteABC`. There is no `BaseSuite`.
- `File.tmp_dir` is a filename **prefix**, not a directory.
- `init_test_classes()` returns instances, not classes.
- `BaseTest.skip` is both an `__init__` kwarg and a method.
- Private attributes map to public keys: `_status` to `"status"`, `_local_path` to `"local_path"`, `Process._command_args` to `"command"`.

## Known bugs in this directory

Documented so you do not trust the behaviour or "fix" the symptom. None of these are yours to fix as a drive-by.

- `dcqc list-tests` indexes `rows[0]` unguarded (`main.py:174`) and crashes if nothing is registered.
- **QC can run on the wrong bytes.** A local file whose `local_path` was not read yet is staged through `already_staged()` (`file.py:427-437`), which matches any `/tmp/dcqc-staged-*/<name>`. For example, a manifest row `test.txt` that holds "Hello world!" was checked against a leftover `/tmp/dcqc-staged-*/test.txt` that holds `foobar\n`, and `Md5ChecksumTest` failed with the MD5 of the leftover copy. Such directories, named after the `tests/data` fixtures, can stay in `/tmp` after earlier runs. Delete them before you trust a local run.

## CLI notes (`main.py`)

- `SuiteABC` treats `None` and `[]` differently for the test lists — `None` means "derive the default", `[]` means "empty". Older Typer returned `[]` for an unset multi-value option; the installed Typer (0.27.2) returns `None`. Every command still normalizes with the `# Interpret empty lists from CLI as None` idiom at `main.py:77`, `:134` and `:189`. Copy it in new commands (background: PR #24).
- The app is `Typer(invoke_without_command=True)` so that `dcqc --version` works without a subcommand.
