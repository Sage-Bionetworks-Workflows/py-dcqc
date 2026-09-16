#!/usr/bin/env bash
#
# Run an external test by hand, as described in the "External Test by Hand"
# section of README.md.
#
# It does the work that nf-dcqc would do: one `docker run` for each of the
# three external tests of a TIFF suite, plus the same dcqc commands as the
# internal pipeline. Every artifact is written to `external_example/`, and the
# result is `external_example/results.csv`.
#
# Requirements: dcqc, synapse, docker, jq, and SYNAPSE_AUTH_TOKEN.
#
# `dcqc` and `synapse` come from the project environment, so activate it first:
#
#   source "$(pipenv --venv)/bin/activate"
#   export SYNAPSE_AUTH_TOKEN=<your personal access token>
#   SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" bash examples/external.sh

set -euo pipefail

MANIFEST="examples/external_target.csv"
WORK_DIR="external_example"
SYNAPSE_ID="syn43716055"
TARGET="target-0001"

EXTERNAL_TESTS=(
  LibTiffInfoTest
  TiffDateTimeTest
  TiffTag306DateTimeTest
)

INTERNAL_TESTS=(
  Md5ChecksumTest
  FileExtensionTest
)

# Every path below is relative to the repository root.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# 1. SYNAPSE_AUTH_TOKEN must already be exported, because every URL in the
#    example manifest is a synapse URL. Check it here rather than let the
#    synapse download and each compute-test fail on their own.
if [[ -z "${SYNAPSE_AUTH_TOKEN:-}" ]]; then
  echo "error: SYNAPSE_AUTH_TOKEN is not set in this environment" >&2
  exit 1
fi

# 2. Make the working directory and enter it. The manifest is now the one path
#    that points outside, as ../examples/external_target.csv.
if [[ -e "$WORK_DIR" ]]; then
  echo "error: $WORK_DIR already exists; remove it and run again" >&2
  exit 1
fi
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# 3. Create targets from the CSV file. Writes targets/target-0001.json.
dcqc create-targets "../$MANIFEST" targets/

# 4. Create tests for the target. Writes one JSON file per test of the suite,
#    which for a TIFF file is three external tests and two internal ones.
dcqc create-tests "targets/$TARGET.json" tests/

# 5. Download the file here. The generated command names the file by its bare
#    filename and nothing else, so the file must sit in the directory that is
#    mounted into the container.
synapse get "$SYNAPSE_ID" --downloadLocation .

# Create both output directories in advance. The current code creates a missing
# parent itself, so this is not strictly needed, but an older dcqc raises
# `fs.errors.CreateFailed: root path '.../suites' does not exist`. Creating them
# costs nothing and keeps the pipeline working on any version.
mkdir -p computed suites

# Steps 6 to 10, once per external test.
for test_name in "${EXTERNAL_TESTS[@]}"; do
  echo "=== $test_name ==="

  # 6. Write the process descriptor. It holds four keys: container, command,
  #    cpus and memory.
  dcqc create-process "tests/$TARGET.$test_name.json" process.json

  # 7. Read the container and the command out of it. `-e` makes jq exit
  #    non-zero if either key is missing, so `set -e` stops here rather than
  #    letting the string "null" reach `sh -c` below. The variable is not
  #    named `command`, because that is a shell builtin.
  container=$(jq -er .container process.json)
  process_command=$(jq -er .command process.json)

  # 8. Run the container, keeping all three outputs. $PWD is external/, so that
  #    is what gets mounted.
  #
  #    Pull first, because docker writes its pull progress to standard error,
  #    and on a first run that progress would land in std_err.txt and be
  #    reported as the status_reason of a failing test.
  #
  #    `sh -c` is required, not a convenience. Two of the three TIFF commands
  #    pipe tifftools into jq and grep, and the descriptor stores the command
  #    as one space-joined string, so without a shell the `|` reaches the tool
  #    as a literal argument.
  #
  #    The mount is read-only. All three TIFF commands only read the file, and
  #    std_out.txt, std_err.txt and exit_code.txt are written by the shell
  #    redirection below, on the host, not inside the container. Relax the flag
  #    to `-v "$PWD":/data` if you add an external test whose tool writes an
  #    output file of its own.
  docker pull "$container"
  docker run --rm -v "$PWD":/data:ro -w /data "$container" sh -c "$process_command" \
    > std_out.txt 2> std_err.txt \
    && echo 0 > exit_code.txt \
    || echo $? > exit_code.txt

  # 9. Compute the status. compute-test reads the three output files from the
  #    current directory, so run it here.
  dcqc compute-test "tests/$TARGET.$test_name.json" \
    "computed/$TARGET.$test_name.json"

  # 10. Delete the container output before the next pass. create-process
  #     refuses to write over an existing file, so leaving process.json in
  #     place would stop the next pass with FileExistsError.
  rm std_out.txt std_err.txt exit_code.txt process.json
done

# 11. Compute the two internal tests of the suite. They need no container, and
#     step 5 has already put the file in place.
#
#     Name these two tests, rather than globbing tests/*.json. A glob puts the
#     three external tests through compute-test a second time, and each one
#     stops with FileNotFoundError, because step 10 deleted the container
#     output that it reads.
for test_name in "${INTERNAL_TESTS[@]}"; do
  dcqc compute-test "tests/$TARGET.$test_name.json" \
    "computed/$TARGET.$test_name.json"
done

# 12. Collect all five computed tests into a suite. Any test missing from
#     computed/ is missing from the suite as well, and the suite status is then
#     derived from the remaining tests only.
dcqc create-suite "suites/$TARGET.json" computed/$TARGET.*.json

# 13. Combine every suite into a single JSON report. This manifest holds one
#     row, so suites/ holds one file.
dcqc combine-suites all_suites.json suites/*.json

# 14. Write the results CSV, then leave the directory. Each row is joined to
#     its suite by the raw url value, which is a synapse URL here and therefore
#     passes through unchanged.
dcqc update-csv all_suites.json "../$MANIFEST" results.csv
cd ..

echo "wrote $WORK_DIR/results.csv"
