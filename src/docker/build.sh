#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pipx run --spec 'tox~=3.0' tox -e clean,build

TARBALL_PATH=$(ls dist/*.tar.gz)
export TARBALL_PATH

docker build \
    -t bwmac03570/py-dcqc-test:hdf5_suite \
    --platform linux/amd64 \
    -f "${SCRIPT_DIR}/Dockerfile" \
    --build-arg TARBALL_PATH \
    "${SCRIPT_DIR}/../.."
