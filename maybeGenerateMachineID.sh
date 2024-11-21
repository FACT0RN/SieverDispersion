#!/bin/bash
# Thanks Claude

# Function to generate UUID using Python
generate_python_uuid() {
    python3 -c 'import uuid; print(uuid.uuid4())'
}

# Function to generate UUID using /proc/sys/kernel/random/uuid
generate_proc_uuid() {
    cat /proc/sys/kernel/random/uuid
}

# Function to validate UUID generator and return the first UUID if valid
validate_and_get_uuid() {
    local generator_func=$1
    local uuid1
    local uuid2

    uuid1=$($generator_func)
    uuid2=$($generator_func)

    if [ "$uuid1" = "$uuid2" ]; then
        return 1
    fi

    # Return the first UUID if validation passed
    echo "$uuid1"
    return 0
}

# Generate UUID using preferred method with fallback
generate_uuid_with_fallback() {
    local uuid

    # Try Python UUID first
    if command -v python3 >/dev/null 2>&1; then
        uuid=$(validate_and_get_uuid generate_python_uuid)
        if [ $? -eq 0 ]; then
            echo "$uuid"
            return 0
        fi
        echo "WARNING: Python UUID generation failed validation, falling back to /proc/sys/kernel/random/uuid" >&2
    fi

    # Fallback to /proc/sys/kernel/random/uuid
    if [ -f /proc/sys/kernel/random/uuid ]; then
        uuid=$(validate_and_get_uuid generate_proc_uuid)
        if [ $? -eq 0 ]; then
            echo "$uuid"
            return 0
        fi
        echo "ERROR: Both UUID generation methods failed validation!" >&2
        return 1
    fi

    echo "ERROR: No valid UUID generation method available!" >&2
    return 1
}

# Main script
if [ ! -f machineID.txt ] || [ ! -s machineID.txt ] || ! grep -q '[^[:space:]]' machineID.txt; then
    uuid=$(generate_uuid_with_fallback)

    if [ $? -eq 0 ]; then
        echo "$uuid" > machineID.txt
        echo "Machine ID generated and saved to machineID.txt"
        echo "Please remove machineID.txt (or move it somewhere else) if you need to move this machine to another account."
        sleep 3
    else
        echo "Failed to generate a valid UUID. Please install python3 and try again."
        exit 1
    fi
fi
