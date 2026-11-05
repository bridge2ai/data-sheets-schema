#!/usr/bin/env python3
# Purpose: record live shared-generation pins and dependency identity for G1V-1/G1V-2.
# Inputs: selected checkout through the offline launcher; output: JSON on stdout.
# Date: 2026-11-03. Reads only; no historical registration is regenerated.
from importlib.metadata import distributions
import json
from pathlib import Path
import sys

from data_sheets_schema import shared_generation as shared
from data_sheets_schema.source_heading_runtime import MODES

assert Path.cwd().resolve() == Path(shared.__file__).resolve().parents[2]
descriptors = {"generic_v10": shared.descriptor()}
descriptors.update({condition: shared.descriptor(version=2, condition=condition)
                    for condition in MODES.values()})
print(json.dumps({
    "python": sys.version,
    "packages": sorted((dist.metadata["Name"], dist.version) for dist in distributions()
                       if dist.metadata["Name"]),
    "descriptors": descriptors,
    "descriptor_sha256": {name: shared.sha(shared.canonical(value))
                          for name, value in descriptors.items()},
}, indent=2, sort_keys=True))
