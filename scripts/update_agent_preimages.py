#!/usr/bin/env python
"""Register definition preimages for installed check-echo challenges.

Run after committing agent-definition changes. The wheel needs the exact
preimage of each definition to discriminate it without a Git checkout.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from data_sheets_schema import agent_pin


def main():
    rows = {}
    for path in sorted(agent_pin.AGENT_DIR.glob("*.md")):
        previous = agent_pin._previous_text(path.stem)
        rows[path.stem] = {
            "current_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "previous_text": previous,
            "previous_sha256": hashlib.sha256(previous.encode()).hexdigest() if previous else None,
        }
    target = agent_pin.AGENT_DIR / "_preimages.json"
    target.write_text(json.dumps({"version": 1, "agents": rows}, indent=2, sort_keys=True) + "\n")
    print(f"registered {len(rows)} definition preimages at {target}")


if __name__ == "__main__":
    main()
