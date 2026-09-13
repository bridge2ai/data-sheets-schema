"""Resolve preserved inputs for the completed September 12 CBORG condition.

The original manifest, measurements and audit inventory are unchanged. Only
the named, hash-verified input files resolve to copies; outputs and receipts
always resolve to their original paths. This is historical report replay,
not a registration or an authorization to execute another measurement.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

PLAN = "notes/reference_rescore_2026-09-12_cborg_runtime"
ARCHIVE = f"{PLAN}/registrations/measured_inputs_1381"
PRESERVATION_SHA256 = "9894f0e42ce94d2e5d404c02b95dea10b0a91e62f39384d99c2d72860c05e901"


def _verified(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"preserved measurement input changed: {path}")
    return raw


class EvidenceRoot(os.PathLike):
    """Path joins read frozen inputs; filesystem identity stays the checkout's.

    No global monkeypatch and no falsified digest: every returned path names
    the actual file being read. Paths used to publish derived reports or
    inspect attempts retain their original locations.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.preservation = json.loads(_verified(
            self.root / ARCHIVE / "preservation.json", PRESERVATION_SHA256))
        record = self.preservation
        _verified(self.root / PLAN / "manifest.json", record["manifest_sha256"])
        inventory = json.loads(_verified(self.root / PLAN / "measurement_file_hashes.json",
                                         record["measurement_index_sha256"]))["files"]
        self.paths = {}
        for relative, entry in record["files"].items():
            if inventory.get(relative) != entry["sha256"]:
                raise ValueError(f"input archive differs from the original audit: {relative}")
            self.paths[relative] = self._archived(entry)
        self.previous_definitions = {
            name: self._archived(entry) for name, entry in record["previous_definitions"].items()
        }

    def _archived(self, entry):
        path = self.root / entry["path"]
        if not path.resolve().is_relative_to((self.root / ARCHIVE).resolve()):
            raise ValueError("preserved input escapes its archive")
        _verified(path, entry["sha256"])
        return path

    def __fspath__(self):
        return str(self.root)

    def __str__(self):
        return str(self.root)

    def __truediv__(self, relative):
        return self.paths.get(str(relative), self.root / relative)

    def load_module(self, relative, name):
        """Load a verified historical helper without replacing public modules."""
        spec = importlib.util.spec_from_file_location(name, self / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def agent_pin(self):
        pin = self.load_module("src/data_sheets_schema/agent_pin.py", "cborg_measured_agent_pin")
        pin.AGENT_DIR = self.root / ARCHIVE / "files/.claude/agents"
        # Definition history is measured evidence too. A future edit or a
        # shallow checkout must not change the historical check-echo challenge.
        pin._previous_text = lambda name: self.previous_definitions[name].read_text(encoding="utf-8")
        return pin
