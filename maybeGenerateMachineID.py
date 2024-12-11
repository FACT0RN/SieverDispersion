#!/usr/bin/env python3
# Thanks Claude
import os
import uuid
import json
import traceback
import base64


def generate_and_save_uuid(machine_id_file):    
    # Check if file doesn't exist, is empty, or contains effectively nothing
    should_generate = (
        not os.path.exists(machine_id_file) or 
        os.path.getsize(machine_id_file) == 0 or
        not open(machine_id_file).read().strip()
    )

    if should_generate:
        new_uuid = str(uuid.uuid4())

        with open(machine_id_file, "w") as f:
            f.write(new_uuid)

        print(f"Machine ID generated and saved to {machine_id_file}")


if __name__ == "__main__":
    try:
        username = json.loads(base64.urlsafe_b64decode(open("api_token.txt").read().split(".")[1] + "=="))["sub"]
    except Exception:
        traceback.print_exc()
        print("Error: api_token.txt is missing or invalid.")
        print("Please refer to the README for how to obtain a Sister Margaret's API token.")
        exit(1)

    generate_and_save_uuid(f"machineIDs/machineID-{username}.txt")
