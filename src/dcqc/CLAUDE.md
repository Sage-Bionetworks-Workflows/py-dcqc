# CLAUDE.md — `src/dcqc`

Core object model and CLI. See the root CLAUDE.md for stack, commands, and the end-to-end data flow. Subpackages `tests/` and `suites/` have their own CLAUDE.md.

## Two registries, opposite behaviour

**`FileType` is eager.** Constructing a `FileType` registers it as a side effect (`file.py:58`), so the 12 built-in types are bare module-level statements at `file.py:106-117`. Registering a duplicate name raises `ValueError` at import time (`file.py:68-70`), which also means `importlib.reload(dcqc.file)` crashes. Lookup is case-insensitive but `FileType.name` preserves case, and the suite registry keys off that original case.

**`BaseTest`, `SuiteABC` and `BaseTarget` are lazy.** `SubclassRegistryMixin.list_subclasses` (`mixins.py:149-155`) walks `__subclasses__()` **recursively**, so the full transitive subclass tree is registered and deduped — but **a class exists only if its module has been imported.** There is no importlib scan, no entry point, no decorator. `src/dcqc/__init__.py:19-21` imports `tests`, `suite_abc` and `suites` for exactly this reason, and carries `# isort: skip_file` at line 3 because the import order avoids a circular import. Do not reorder it.

Registry gotchas that fail silently:

- `list_subclasses()` includes abstract intermediates, so `JsonParser.get_class("ExternalTestMixin")` returns an abstract class rather than erroring.
- The base class is not in its own subclass list — `BaseTarget.get_subclass_by_name("BaseTarget")` raises.
- A new registry root must implement `get_base_class()` (`mixins.py:145`), because `get_subclass_by_name` always resolves through the base, never through `cls`.

## Serialization

`SerializableMixin` (`mixins.py:18`) gives you `to_dict()` for free, but **only if the subclass is a dataclass** — the generic implementation calls `dataclasses.fields(self)`. `File`, `Process` and `BaseTarget` are dataclasses. `BaseTest` and `SuiteABC` are not, so they hand-write `to_dict()`. Add a non-dataclass subclass without overriding `to_dict` and you get `TypeError: asdict() should be called on dataclass instances`.

To include a `@property` in the output, list its name in `_serialized_properties` (`mixins.py:20`), as `File` does with `["name", "local_path"]`.

### `"type"` means two different things

| Class | `"type"` holds |
|---|---|
| `File` | the **FileType name** (`"TIFF"`, `"JSON-LD"`) |
| `BaseTarget`, `BaseTest`, `SuiteABC` subclasses | the **class name** |
| `Process` | no `type` key at all — it cannot round-trip through `JsonParser` |

`JsonParser.get_class` (`parsers.py:80-104`) probes targets, then tests, then suites, then FileType names. **Never give a new `FileType` the same name as a Test, Suite or Target class** — the class wins and polymorphic dispatch silently resolves to the wrong thing.

### Rules that are easy to violate

- **`BaseTest.from_dict` mutates its argument** (`base_test.py:103` pops `"type"`), unlike every other `from_dict`, which deepcopies first. Calling it twice on the same dict raises `KeyError: 'type'`.
- **`serialize_paths_relative_to` must be called before `to_dict`, and it does not recurse.** `serialize_value` calls `to_dict()` on nested objects without propagating the setting (`mixins.py:61-62`), so only top-level paths get relativized. `tests/data/suites.json` still contains an absolute `/tmp/dcqc-staged-.../circuit.tif` because of this.
- **A property that raises serializes as `null`,** not as an error — `mixins.py:104-107` swallows every exception. This is how an unstaged `File` gets `"local_path": null`.
- **`Process` round-trips lossily.** `command` is emitted space-joined and re-split with `shlex.split`, which strips the hand-written quotes around filenames.
- **`from_dict_prepare`** (which validates `"type"` against the class name) is called only by `BaseTarget.from_dict`. The other three `from_dict` implementations do no type checking.
- `File.from_dict` requires a `local_path` key and discards the serialized `name`, because `name` is a computed property.
- Use the `SerializedObject` alias (`mixins.py:11`) in signatures rather than a raw dict type.

## Reusable utilities — use these, do not reimplement

- `dcqc.utils.is_url_local(url)` — local means a `file://` prefix or no `://` at all. Deliberately permissive; the real guard is `File._validate_url`, which rejects host-bearing `file://host/path` forms (added in PR #72). The docstring at `utils.py:8-13` explains the split. Do not tighten one without the other.
- `File.stage(destination=None, overwrite=False) -> Path` — the only correct way to get a usable local path. Reuses an existing staged copy, otherwise creates a `mkdtemp(prefix="dcqc-staged-")`. A local file is **symlinked** rather than copied only when `_local_path` is already set (`file.py:420`); a local file that has never had `local_path` accessed falls through to `fs.get()` and is copied.
- `File.already_staged() -> list[Path]` — returns a list, not an `Optional[Path]`; empty means not staged. It globs the whole temp dir, so a leftover copy from a *previous run* is silently reused, and more than one match raises `FileExistsError` to pre-empt a Nextflow name collision (added in PR #43).
- `File.get_metadata(key)` — raises a helpful `KeyError`; prefer it to `file.metadata[key]`.
- `File.is_file_local()` returns a bool, but `File.local_path` **raises** `FileNotFoundError` for the same condition. Check the former before touching the latter.
- `File.name` issues an `fs.info()` network call on remote files, then caches.
- `BaseTest.import_module(name)` — use for optional extras instead of a top-level import, so the error tells the user to `pip install dcqc[all]`.
- `JsonParser.from_dict(dictionary)` — the polymorphic factory. Use it when the concrete class is not known.
- `JsonReport(paths_relative_to=None)` with `.generate()`, `.save()`, `.save_many()`. All accept fsspec URLs. `save` refuses to overwrite unless told.
- `CsvParser(path, stage_files=False)` — `create_files`, `create_targets` and `create_suites` return **generators**, not lists. `list_rows()` indexes from 1.
- MD5 chunking (`md5_checksum_test.py:25-31`) and compression-agnostic FASTQ opening (`paired_fastq_parity_test.py:49-63`) already exist.

## Naming traps

- The base classes are `BaseTest`, `BaseTarget` — but `SuiteABC`. There is no `BaseSuite`.
- `File.tmp_dir` is a filename **prefix**, not a directory.
- `init_test_classes()` returns instances, not classes.
- `BaseTest.skip` is both an `__init__` kwarg and a method.
- Private attributes map to public keys: `_status` to `"status"`, `_local_path` to `"local_path"`, `Process._command_args` to `"command"`.

## Known bugs in this directory

Documented so you do not trust the behaviour or "fix" the symptom. None of these are yours to fix as a drive-by.

- **`file.py:112,113,114,117` are missing trailing commas.** `(".tsv")` is a string, so `tuple(...)` yields `('.','t','s','v')` and `FileExtensionTest` accepts any name ending in `.`, `t`, `s` or `v`. TSV, CSV, BAM and H5AD extension checks are effectively disabled. TXT, JSON, JSON-LD, TIFF, OME-TIFF, FASTQ and HDF5 are correct.
- **`FileType("*", (), ...)`** has an empty extension tuple, and `str.endswith(())` is always `False`. Any file without a `file_type` falls back to `"*"`, lands in `FileSuite`, and therefore **always fails** `FileExtensionTest`.
- **`PairedTarget` cannot be deserialized.** `BaseTarget.from_dict` calls `target_cls(*files, id=id)` (`target.py:85`) against an `__init__` of `(file_or_files, id=None)`, so two files raise `TypeError`. No test covers it.
- **`CsvUpdater.parser` is declared but never assigned** (`updaters.py:17` vs the `__init__` at 19-21). Touching `self.parser` raises `AttributeError`; `update()` builds a local one instead.
- **`update-csv` joins suites to CSV rows by raw URL string.** `CsvParser` rewrites relative local URLs via `relative_to=self.path.parent` (`parsers.py:36`), but `CsvUpdater` looks up the unrewritten column value (`updaters.py:45`), so the two keys diverge and the lookup raises `KeyError`. Confirmed by running it, not just by reading: a manifest at `manifests/input.csv` holding `url=test.txt` fails with `KeyError: 'test.txt'` while every earlier pipeline step succeeds. The precise trigger is the manifest living in a **different directory from the URL base** — it works with remote URLs, with absolute paths, and also with relative paths when the CSV is in the current working directory, because `path.parent` is then `.` and the rewrite is a no-op. The README pipeline examples pass despite reading `../examples/*.csv` from a working directory of their own, because those manifests hold `syn://` URLs; every fixture using `syn://` hides the bug the same way. The README documents the limitation without naming the cause ("A manifest of relative local paths does not survive this join from another directory").
- **`CsvUpdater` reads only `files[0]`**, so multi-file targets collapse to their first file (`updaters.py:25-27`).
- `BaseTest.import_module`'s error message is accidentally a tuple (a stray trailing comma at `base_test.py:121-125`).
- `dcqc list-tests` indexes `rows[0]` unguarded (`main.py:174`) and crashes if nothing is registered.

## CLI notes (`main.py`)

- Typer returns `[]`, not `None`, for an unset multi-value option, and `SuiteABC` treats the two differently — `None` means "derive the default", `[]` means "empty". Every command therefore normalizes with the `# Interpret empty lists from CLI as None` idiom at `main.py:77`, `:134` and `:189`. Copy it in new commands (background: PR #24).
- The app is `Typer(invoke_without_command=True)` so that `dcqc --version` works without a subcommand.
