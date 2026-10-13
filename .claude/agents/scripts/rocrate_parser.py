#!/usr/bin/env python3
"""Compatibility entry point for the packaged RO-Crate parser.

Legacy scripts can be run directly from outside the checkout, so expose
this checkout's ``src`` only when its packaged implementation is present.
The installed parser itself has no dependency on these source-only scripts.
"""

from pathlib import Path
import sys

_source = Path(__file__).resolve().parents[3] / "src"
if (_source / "fairscape_integration/utils/rocrate_parser.py").is_file():
    if str(_source) not in sys.path:
        sys.path.insert(0, str(_source))

from fairscape_integration.utils.rocrate_parser import (
    ROCrateParser as _PackagedROCrateParser,
    graph_entities,
)


class ROCrateParser(_PackagedROCrateParser):
    """Retain the legacy parser's default progress messages."""

    def __init__(self, rocrate_path: str, verbose: bool = True):
        super().__init__(rocrate_path, verbose=verbose)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rocrate_parser.py <path_to_rocrate_json>")
        sys.exit(1)

    parser = ROCrateParser(sys.argv[1])

    print("\n=== Root Dataset ===")
    if parser.root_dataset:
        print(f"@id: {parser.root_dataset.get('@id')}")
        print(f"@type: {parser.root_dataset.get('@type')}")
        print(f"name: {parser.get_property('name')}")
        print(f"description: {parser.get_property('description')}")

    print(f"\n=== All Properties ({len(parser.all_properties)}) ===")
    for key in list(parser.all_properties.keys())[:20]:
        value = parser.all_properties[key]
        value_str = str(value)[:50]
        if len(str(value)) > 50:
            value_str += "..."
        print(f"  {key}: {value_str}")

    print("\n=== Entities by Type ===")
    persons = parser.get_entities_by_type('Person')
    print(f"Person entities: {len(persons)}")
    if persons:
        print(f"  Sample: {persons[0].get('name', 'N/A')}")
