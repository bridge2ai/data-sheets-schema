#!/usr/bin/env python
"""Register definition preimages for installed check-echo challenges.

Run after committing agent-definition changes. The wheel needs the exact
preimage of each definition to discriminate it without a Git checkout.
"""
from __future__ import annotations

import hashlib
import json
from data_sheets_schema import agent_pin, resources


def main():
    root, kind = resources.resource_root()
    if kind != "checkout":
        raise ValueError("preimage registration requires a selected source checkout")
    directory = root / ".claude/agents"
    target = directory / "_preimages.json"
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("preimage registry must belong to the selected checkout")
    rows = {}
    for path in sorted(directory.glob("*.md")):
        if (not path.resolve().is_relative_to(root.resolve())
                or agent_pin.agent_path(path.stem).resolve() != path.resolve()):
            raise ValueError(f"definition does not belong to the selected checkout: {path}")
        previous = agent_pin._previous_text(path.stem)
        rows[path.stem] = {
            "current_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "previous_text": previous,
            "previous_sha256": hashlib.sha256(previous.encode()).hexdigest() if previous else None,
        }
    target.write_text(json.dumps({"version": 1, "agents": rows}, indent=2, sort_keys=True) + "\n")
    print(f"registered {len(rows)} definition preimages at {target}")


if __name__ == "__main__":
    main()
