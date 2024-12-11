#!/bin/bash
set -e

pushd -- "$(dirname "$0")"
./maybeGenerateMachineID.py
SIEVER_MODE=0 ./SieverDispersion
popd
