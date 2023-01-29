#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

pipx run --spec 'tox~=3.0' tox -e clean,build

docker build -t dcqc -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/../.."
