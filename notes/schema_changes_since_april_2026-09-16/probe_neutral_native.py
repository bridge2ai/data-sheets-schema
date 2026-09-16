"""Inspect the current checkout's neutral native schema resources, without a model.

Run with PYTHONPATH=src from the report's reviewed revision (or a descendant
whose runtime/schema files are unchanged). Evidence records exact resource
hashes so a later checkout cannot be mistaken for the reviewed instrument.
"""
import hashlib
import json
import os
from pathlib import Path

os.environ["D4D_PROFILE"] = "neutral"

from data_sheets_schema.agentic_runtime import SCHEMAS, playbook_text, toolchain
from data_sheets_schema.profiles import select_profile


def main():
    environment = toolchain()
    playbook = playbook_text(environment)
    result = {"profile": select_profile(None).profile.name, "schema_resources": {}}
    for logical in SCHEMAS:
        path = Path(environment["resources"][logical])
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        result["schema_resources"][logical] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "named_example_present": "Bridge2AI-Voice Data Access Committee (DACO)" in text,
            "named_description_present": "AI-READI Data Access Committee" in text,
            "path_in_native_playbook": str(path) in playbook,
        }
    Path(__file__).with_name("neutral_native_probe.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
