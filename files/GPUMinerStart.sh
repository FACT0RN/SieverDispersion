#!/bin/bash
set -e

pushd -- "$(dirname "$0")"
./maybeGenerateMachineID.py
SIEVER_MODE=1 ./SieverDispersion
popd
