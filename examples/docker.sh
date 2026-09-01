#!/usr/bin/env bash
#
# Run the internal pipeline in the published image, as described in the
# "Internal Test in the py-dcqc Docker Image" section of README.md.
#
# It runs the same six commands as examples/internal.sh and ends in the same
# GREEN row, but every command runs in a container instead of in a local Python
# environment. Every artifact is written to `docker_example/`, which is a
# directory of its own so that this pipeline can run beside `internal_example/`.
# The result is `docker_example/results.csv`.
#
# Requirements: docker and SYNAPSE_AUTH_TOKEN. `dcqc` itself is not needed on
# your PATH, so no environment has to be activated:
#
#   export SYNAPSE_AUTH_TOKEN=<your personal access token>
#   SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" bash examples/docker.sh

set -euo pipefail

MANIFEST="examples/internal_target.csv"
WORK_DIR="docker_example"
TARGET="target-0001"
IMAGE="ghcr.io/sage-bionetworks-workflows/py-dcqc:main"

# Every path below is relative to the repository root.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# 1. SYNAPSE_AUTH_TOKEN must already be exported, because every URL in the
#    example manifest is a synapse URL. Check it here rather than let each
#    compute-test fail with a SynapseNoCredentialsError traceback. Note that
#    plain `sudo bash examples/docker.sh` strips the variable; see the header.
if [[ -z "${SYNAPSE_AUTH_TOKEN:-}" ]]; then
  echo "error: SYNAPSE_AUTH_TOKEN is not set in this environment" >&2
  echo "       under sudo, pass it through:" >&2
  echo "       sudo SYNAPSE_AUTH_TOKEN=\"\$SYNAPSE_AUTH_TOKEN\" bash $0" >&2
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

# 3. Define the wrapper. A bare `docker run` in front of each command does not
#    work, because a container gets a fresh filesystem and exits after one
#    command: step 4 would write targets/target-0001.json inside the container,
#    and that file would be gone before step 5 could read it. Every step
#    therefore needs the same flags.
#
#    -v "$PWD/..":/data mounts the root of the clone, so the intermediate JSON
#    is written to the host and survives between steps. The clone root is
#    mounted rather than docker_example/ itself, because the manifest sits
#    outside docker_example/ and a container sees nothing above its mount.
#
#    -w /data/docker_example makes docker_example/ the working directory inside
#    the container, so every path is written exactly as it is in
#    examples/internal.sh. Without it, relative paths resolve against the
#    image's own WORKDIR of /usr/src/app, and step 4 stops with
#    FileNotFoundError before it writes anything.
#
#    -e SYNAPSE_AUTH_TOKEN forwards the token from step 1. The image's CMD is
#    only an `import dcqc` smoke test, so a real `dcqc ...` command must always
#    be given, as it is on the last line.
#
#    --user "$(id -u):$(id -g)" runs the container as you rather than as root.
#    Without it every file below is written to the host owned by root, and the
#    re-run guard in step 2 then cannot be cleared: `rm -rf docker_example`
#    stops with `Permission denied` for an unprivileged user.
#
#    -e HOME="/data/$WORK_DIR" gives that unmapped user a writable home. The
#    user has no home directory in the image, and synapseclient then stops with
#    `PermissionError: [Errno 13] Permission denied: '/.synapseCache'`. Pointing
#    HOME at the working directory keeps the cache inside docker_example/, which
#    is gitignored.
dcqc_docker() {
  docker run --rm \
    -v "$PWD/..":/data -w "/data/$WORK_DIR" \
    --user "$(id -u):$(id -g)" \
    -e HOME="/data/$WORK_DIR" \
    -e SYNAPSE_AUTH_TOKEN \
    "$IMAGE" \
    dcqc "$@"
}

# Pull first, so that the pull progress does not interleave with the output of
# step 4.
docker pull "$IMAGE"

# 4. Create targets from the CSV file. Writes targets/target-0001.json.
dcqc_docker create-targets "../$MANIFEST" targets/

# 5. Create tests for the target. Writes one JSON file per test of the file
#    type's suite, which for a TXT file is two internal tests.
dcqc_docker create-tests "targets/$TARGET.json" tests/

# 6. Compute the status of each test. The glob is expanded by this shell against
#    the host directory, not by the container, which is why the mount must be in
#    place from step 4 onward.
#
#    Running in the image does not change which tests can complete: an external
#    test still stops with FileNotFoundError here, because the image holds dcqc
#    and not the tool containers that the external tests call. The `|| echo`
#    branch keeps the loop going and names what it could not compute.
#
#    mkdir -p creates both output directories in advance. The current code
#    creates a missing parent itself, so suites/ is not strictly needed with the
#    main image, but an older image raises
#    `fs.errors.CreateFailed: root path '/data/docker_example/suites' does not
#    exist` at step 7.
mkdir -p computed suites
for test_json in tests/$TARGET.*.json; do
  dcqc_docker compute-test "$test_json" "computed/$(basename "$test_json")" \
    || echo "not computed: $test_json"
done

# 7. Collect the computed tests of the target into a suite. Name the target in
#    the glob. A bare computed/*.json matches the tests of every target
#    processed so far, and create-suite then stops with
#    `ValueError: Not all tests refer to the same target`.
#
#    Expand the glob here and stop if it matches nothing. Step 6 keeps going
#    when a test cannot be computed, so without this check an unmatched glob
#    reaches create-suite as a literal argument, and the run ends in a
#    `FileNotFoundError: computed/target-0001.*.json` that hides the real cause.
shopt -s nullglob
computed_tests=(computed/$TARGET.*.json)
shopt -u nullglob
if [[ ${#computed_tests[@]} -eq 0 ]]; then
  echo "error: step 6 computed no test; see the errors above" >&2
  exit 1
fi
dcqc_docker create-suite "suites/$TARGET.json" "${computed_tests[@]}"

# 8. Combine every suite into a single JSON report. This manifest holds one row,
#    so suites/ holds one file.
dcqc_docker combine-suites all_suites.json suites/*.json

# 9. Write the results CSV, then leave the directory. Every row of the input CSV
#    must have a suite in all_suites.json, because the command looks each row up
#    by its url.
dcqc_docker update-csv all_suites.json "../$MANIFEST" results.csv
cd ..

# The image runs as root, so every file above is owned by root on the host. The
# end of the "Internal Test in the py-dcqc Docker Image" section of README.md
# gives the --user and -e HOME flags that keep them owned by you.
echo "wrote $WORK_DIR/results.csv"
