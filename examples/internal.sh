#!/usr/bin/env bash
#
# Run the internal pipeline, as described in the "Internal Test by Hand"
# section of README.md.
#
# Every test of the example manifest is an internal one, so no container is
# needed and the whole pipeline runs in Python. Every artifact is written to
# `internal_example/`, and the result is `internal_example/results.csv`.
#
# Requirements: dcqc and SYNAPSE_AUTH_TOKEN.
#
# `dcqc` comes from the project environment, so activate it first:
#
#   source "$(pipenv --venv)/bin/activate"
#   export SYNAPSE_AUTH_TOKEN=<your personal access token>
#   SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" bash examples/internal.sh

set -euo pipefail

MANIFEST="examples/internal_target.csv"
WORK_DIR="internal_example"
TARGET="target-0001"

# Every path below is relative to the repository root.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# 1. SYNAPSE_AUTH_TOKEN must already be exported, because every URL in the
#    example manifest is a synapse URL. Check it here rather than let each
#    compute-test fail with a SynapseNoCredentialsError traceback.
if [[ -z "${SYNAPSE_AUTH_TOKEN:-}" ]]; then
  echo "error: SYNAPSE_AUTH_TOKEN is not set in this environment" >&2
  exit 1
fi

# 2. Make the working directory and enter it. The manifest is now the one path
#    that points outside, as ../examples/internal_target.csv.
if [[ -e "$WORK_DIR" ]]; then
  echo "error: $WORK_DIR already exists; remove it and run again" >&2
  exit 1
fi
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 3. Create targets from the CSV file. Each row becomes one target, numbered
#    from 0001, and relative URLs resolve against the directory of the CSV.
dcqc create-targets "../$MANIFEST" targets/

# 4. Create tests for the target. Writes one JSON file per test of the file
#    type's suite. Pass --required-tests to create-suite in step 6, not here.
dcqc create-tests "targets/$TARGET.json" tests/

# 5. Compute the status of each test. This is the step that nf-dcqc fans out,
#    one call per test.
#
#    Run in this way, compute-test succeeds for internal tests only. For an
#    external test it reads std_out.txt, std_err.txt and exit_code.txt from the
#    current directory, and stops with FileNotFoundError when they are absent.
#    The `|| echo` branch keeps the loop going and names what it could not
#    compute. See examples/external.sh for how to produce those three files.
mkdir -p computed suites
for test_json in tests/$TARGET.*.json; do
  dcqc compute-test "$test_json" "computed/$(basename "$test_json")" \
    || echo "not computed: $test_json"
done

# 6. Collect the computed tests of the target into a suite. The glob matches
#    only the files that step 5 wrote, so a test it could not compute is absent
#    from the suite, and the status is derived from the remaining tests only.
#
#    Name the target in the glob. A bare computed/*.json matches the tests of
#    every target processed so far, and create-suite then stops with
#    `ValueError: Not all tests refer to the same target`.
#
#    Expand the glob here and stop if it matches nothing. Step 5 keeps going
#    when a test cannot be computed, so without this check an unmatched glob
#    reaches create-suite as a literal argument, and the run ends in a
#    `FileNotFoundError: computed/target-0001.*.json` that hides the real cause.
shopt -s nullglob
computed_tests=(computed/$TARGET.*.json)
shopt -u nullglob
if [[ ${#computed_tests[@]} -eq 0 ]]; then
  echo "error: step 5 computed no test; see the errors above" >&2
  exit 1
fi
dcqc create-suite "suites/$TARGET.json" "${computed_tests[@]}"

# 7. Combine every suite into a single JSON report. Repeat steps 4 to 6 for
#    each target first, so that suites/ holds one file per target. This
#    manifest holds one row, so suites/ holds one file.
dcqc combine-suites all_suites.json suites/*.json

# 8. Write the results CSV, then leave the directory. Every row of the input
#    CSV must have a suite in all_suites.json, because the command looks each
#    row up by its url.
dcqc update-csv all_suites.json "../$MANIFEST" results.csv
cd ..

echo "wrote $WORK_DIR/results.csv"
