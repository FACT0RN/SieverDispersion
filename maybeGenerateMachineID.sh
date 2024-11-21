#!/bin/bash

# If machineID.txt does not exist, generate a new one
if [ ! -f machineID.txt ]; then
    # Use UUID v4
    uuid=$(python3 -c 'import uuid; print(uuid.uuid4())')
    echo "$uuid" > machineID.txt
    echo "Machine ID generated and saved to machineID.txt"
    echo "Please remove machineID.txt (or move it somewhere else) if you need to move this machine to another account."
    sleep 3
fi
