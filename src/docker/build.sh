#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pipx run --spec 'tox~=3.0' tox -e clean,build

TARBALL_PATH=$(ls dist/*.tar.gz)
export TARBALL_PATH

docker build \
    -t bwmac03570/dcqc \
    -f "${SCRIPT_DIR}/Dockerfile" \
    --platform linux/amd64 \
    --build-arg TARBALL_PATH \
    "${SCRIPT_DIR}/../.."
