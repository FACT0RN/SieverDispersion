#!/bin/bash
set -e

# If the command unbuffer doesn't exist
if ! command -v unbuffer >/dev/null 2>&1; then
    echo "The 'unbuffer' command is not installed. Please install it. You can do this by installing the 'expect' package using your distro's package manager."
    exit 1
fi

pushd -- "$(dirname "$0")"
./maybeGenerateMachineID.py
SIEVER_MODE=1 ./SieverDispersion
popd
