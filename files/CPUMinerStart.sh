#!/bin/bash
set -e

pushd -- "$(dirname "$0")"
./maybeGenerateMachineID.sh
SIEVER_MODE=0 ./SieverDispersion
popd
