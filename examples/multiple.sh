#!/usr/bin/env bash
#
# Run the full pipeline on examples/example_manifest_multiple.csv, which holds
# two TXT rows (internal tests only) and two TIFF rows (internal + external
# tests). This generalizes examples/internal.sh and examples/external.sh to a
# manifest of several rows.
#
# Every artifact is written to `multiple_example/`, and the result is
# `multiple_example/results.csv`.
#
# Requirements: dcqc, synapse, docker, jq, and SYNAPSE_AUTH_TOKEN.
#
# `dcqc` and `synapse` come from the project environment, so activate it first:
#
#   source "$(pipenv --venv)/bin/activate"
#   export SYNAPSE_AUTH_TOKEN=<your personal access token>
#   SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" bash examples/multiple.sh

set -euo pipefail

MANIFEST="examples/example_manifest_multiple.csv"
WORK_DIR="multiple_example"

# Every path below is relative to the repository root.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# 1. SYNAPSE_AUTH_TOKEN must already be exported, because every URL in the
#    example manifest is a synapse URL. Check it here rather than let a
#    download or a compute-test fail on its own.
if [[ -z "${SYNAPSE_AUTH_TOKEN:-}" ]]; then
  echo "error: SYNAPSE_AUTH_TOKEN is not set in this environment" >&2
  exit 1
fi

# 2. Make the working directory and enter it. The manifest is now the one
#    path that points outside, as ../examples/example_manifest_multiple.csv.
if [[ -e "$WORK_DIR" ]]; then
  echo "error: $WORK_DIR already exists; remove it and run again" >&2
  exit 1
fi
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 3. Create one target per manifest row. Writes targets/target-0001.json
#    through targets/target-0004.json, numbered in row order.
dcqc create-targets "../$MANIFEST" targets/

mkdir -p tests computed suites downloads

# 4. Run the rest of the pipeline once per target.
for target_json in targets/*.json; do
  target_name="$(basename "$target_json" .json)"
  echo "=== $target_name ==="

  # 5. Create tests for this target. Writes one JSON file per test of the
  #    file type's suite: two files for a TXT target, five for a TIFF one.
  dcqc create-tests "$target_json" tests/

  # The url is read once per target, not per test, so a TIFF target's file is
  # downloaded only once even though it has three external tests.
  url="$(jq -r '.files[0].url' "$target_json")"
  download_dir="downloads/$target_name"

  # 6. Compute each test of this target, dispatching on is_external_test
  #    rather than on file_type. This is what lets one loop work for TXT and
  #    TIFF rows alike, and for any other file type mixed into the manifest.
  for test_json in tests/"$target_name".*.json; do
    test_base="$(basename "$test_json" .json)"
    test_name="${test_base#"$target_name".}"
    computed_json="computed/$target_name.$test_name.json"

    is_external="$(jq -r .is_external_test "$test_json")"
    if [[ "$is_external" != "true" ]]; then
      # 6a. Internal test: no container needed, dcqc fetches the file itself.
      dcqc compute-test "$test_json" "$computed_json" \
        || echo "not computed: $test_json"
      continue
    fi

    # 6b. External test: write the process descriptor, run the container,
    #     then compute the status from its three output files.
    #
    #     The mounted file is downloaded here rather than left to the
    #     create-process step's own staging, because that stages to a
    #     temporary directory elsewhere, not one this script can mount. Only
    #     the bare filename is downloaded, matching the bare path.name that
    #     generate_process() puts in the container command.
    mkdir -p "$download_dir"
    if [[ -z "$(ls -A "$download_dir")" ]]; then
      synapse get "${url#syn://}" --downloadLocation "$download_dir"
    fi

    dcqc create-process "$test_json" process.json
    container="$(jq -er .container process.json)"
    process_command="$(jq -er .command process.json)"

    # Pull first, because docker writes its pull progress to standard error,
    # and on a first run that progress would land in std_err.txt and be
    # reported as the status_reason of a failing test.
    docker pull "$container"
    (
      cd "$download_dir"
      docker run --rm -v "$PWD":/data:ro -w /data "$container" sh -c "$process_command" \
        > std_out.txt 2> std_err.txt \
        && echo 0 > exit_code.txt \
        || echo $? > exit_code.txt
    )

    # compute-test reads ./std_out.txt, ./std_err.txt and ./exit_code.txt
    # from the current directory, so run it from download_dir.
    (
      cd "$download_dir"
      dcqc compute-test "../../$test_json" "../../$computed_json"
    )

    # create-process refuses to write over an existing file, and the three
    # output files would otherwise be picked up by the next external test's
    # compute-test, so delete all four before the next pass.
    rm -f "$download_dir"/std_out.txt "$download_dir"/std_err.txt \
      "$download_dir"/exit_code.txt process.json
  done

  # 7. Collect this target's computed tests into a suite. A test that step 6
  #    could not compute is absent from computed/, and the suite status is
  #    then derived from the remaining tests only.
  shopt -s nullglob
  computed_tests=(computed/"$target_name".*.json)
  shopt -u nullglob
  if [[ ${#computed_tests[@]} -eq 0 ]]; then
    echo "error: no test was computed for $target_name; see the errors above" >&2
    exit 1
  fi
  dcqc create-suite "suites/$target_name.json" "${computed_tests[@]}"
done

# 8. Combine every target's suite into a single JSON report.
dcqc combine-suites all_suites.json suites/*.json

# 9. Write the results CSV, then leave the directory. Every row of the input
#    CSV must have a suite in all_suites.json, because the command looks each
#    row up by its url.
dcqc update-csv all_suites.json "../$MANIFEST" results.csv
cd ..

echo "wrote $WORK_DIR/results.csv"
