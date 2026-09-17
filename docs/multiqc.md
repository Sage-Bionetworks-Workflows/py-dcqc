# MultiQC plugin

`dcqc.multiqc_plugin` is a [MultiQC](https://multiqc.info) module that renders
DCQC validation results from a `suites.json` file. It ships in py-dcqc and is
registered with MultiQC via the `multiqc.modules.v1` entry point, so installing
py-dcqc with the optional `multiqc` extra is all that is needed — no separate
plugin package, no runtime `pip install`.

## Installation

```bash
pip install "dcqc[multiqc]"
```

This pulls in MultiQC (>= 1.30) and registers the `dcqc_validation` module.
Verify the entry point is visible to your interpreter:

```python
from importlib.metadata import entry_points
print([ep.name for ep in entry_points(group="multiqc.modules.v1") if ep.name == "dcqc_validation"])
```

## Running MultiQC against a `suites.json`

The plugin looks for files literally named `suites.json`. The search pattern is
registered by passing a small MultiQC config file:

```yaml
# multiqc_config.yaml
sp:
  dcqc_validation:
    fn: "suites.json"
```

Then:

```bash
multiqc --force --config multiqc_config.yaml --module dcqc_validation .
```

The `--module dcqc_validation` flag is optional but skips MultiQC's other ~180
modules and speeds up the search. Running without it still works.

The same `multiqc_config.yaml` is what
[`nf-dcqc`](https://github.com/Sage-Bionetworks-Workflows/nf-dcqc) ships under
`assets/` for its `MULTIQC` Nextflow process.

## What you get in the report

| Section | Where it shows up | Built from |
|---|---|---|
| General statistics columns | MultiQC's top general-stats table | Per-suite overall status + pass/fail/total counts |
| `<SuiteType> Validation` | One section per suite type | Per-sample summary table |
| `<SuiteType> Test Details` | One section per suite type | Per-test rows (name, tier, status, external Yes/No) |
| `<SuiteType> Failed Tests` | Only when failures exist | HTML block with full `status_reason` text per failed test |

Suite types are taken from the `type` field of each suite (e.g. `H5ADSuite`,
`TiffSuite`, `OmeTiffSuite`, `FastqSuite`, …). Each distinct suite type gets
its own set of sections so reports stay readable when a single run validates
multiple file types.

## `suites.json` schema

`suites.json` is a JSON array of suite objects, produced by `dcqc
combine-suites`. The plugin reads each suite permissively — it skips any
suite missing a `target.files` entry, and falls back to a default for every
other field. The table below lists what the plugin reads and which fields
must be present for that suite to appear in the report.

### Suite object

| Field | Required | Default if missing | Notes |
|---|---|---|---|
| `type` | optional | `"Unknown"` | Suite type; drives section headers (e.g. `H5ADSuite`). |
| `target` | **required** | — | Object describing the file(s) under test. |
| `target.id` | optional | filename of the first file | Becomes the MultiQC sample ID after `clean_s_name`. |
| `target.files` | **required, non-empty** | suite is skipped | List of file objects. The plugin reads only `files[0]`. |
| `target.files[0].name` | optional | `"Unknown"` | Displayed in summary and failed-test sections. |
| `suite_status` | optional | `{}` | Overall suite verdict. |
| `suite_status.status` | optional | `"UNKNOWN"` | One of `GREEN` / `AMBER` / `RED` / `GREY`; drives the conditional color. |
| `suite_status.required_tests` | optional | `[]` | Used only for the per-sample required-test count. |
| `tests` | optional | `[]` | List of individual test results. |

### Test object (each entry in `tests`)

| Field | Required | Default if missing | Notes |
|---|---|---|---|
| `type` | optional | `"Unknown"` | Test class name, shown in the details table. |
| `tier` | optional | `"-"` | Test tier label. |
| `status` | optional | `"unknown"` | One of `passed` / `failed` / `skipped`; drives pass/fail counts and conditional color. |
| `status_reason` | optional | `""` | Free-form failure message; rendered in the **Failed Tests** section when `status == "failed"`. Newlines are preserved up to 50 lines, then truncated. |
| `is_external_test` | optional | `false` | Renders as Yes/No in the details table. |

In practice the only fields the plugin **needs** are `target.files` (non-empty)
and at least one test entry — every other field has a sensible fallback so
partial or in-progress suites still render without errors.

## Sample output

> _Screenshot placeholder — drop a render of an example report here. To
> regenerate locally, run the smoke pipeline below and screenshot the
> `<SuiteType> Validation` and `<SuiteType> Failed Tests` sections._

A minimal reproduction without the Nextflow pipeline:

```bash
mkdir mqc-demo && cd mqc-demo
cat > suites.json <<'EOF'
[
  {
    "type": "H5ADSuite",
    "target": {"id": "sample_001", "files": [{"name": "sample_001.h5ad"}]},
    "suite_status": {"status": "RED", "required_tests": ["H5adHtanValidatorTest"]},
    "tests": [
      {"type": "FileExtensionTest", "tier": "1", "status": "passed"},
      {"type": "H5adHtanValidatorTest", "tier": "2", "status": "failed",
       "status_reason": "schema mismatch: missing 'cell_type'", "is_external_test": true}
    ]
  }
]
EOF
cat > multiqc_config.yaml <<'EOF'
sp:
  dcqc_validation:
    fn: "suites.json"
EOF
multiqc --force --config multiqc_config.yaml --module dcqc_validation .
```

## Caveats

- Search patterns must be registered via `multiqc_config.yaml`. The module's
  package init also calls `config.sp[...] = ...` as a fallback, but MultiQC's
  file-search phase runs before that import in most invocation paths, so the
  YAML config is the reliable mechanism.
- The plugin only reads `files[0]` from each `target.files` array. Multi-file
  targets (e.g. paired FASTQ) are summarized by their first file.
- Failed-test `status_reason` text is HTML-escaped only by what MultiQC's
  template normally does for `add_section(content=...)`. Avoid embedding
  untrusted HTML in `status_reason`.
