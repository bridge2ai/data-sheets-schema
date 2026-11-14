#!/usr/bin/env python3
"""Check Synapse test collection isolation, H1-CI-F1, 2026-11-12.

Input: this checkout and its installed test dependencies in a fresh interpreter.
Output: a new JSON witness named by --out. Import then run two local serializer
tests to check the actual fixture teardown. No provider, native executable or
network operation. The parent test supplies the offline sandbox and isolated
environment. Keep this helper with the regression tests.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    if not sys.dont_write_bytecode or not sys.flags.safe_path:
        parser.error("invoke with -P -B")
    if args.out.exists() or args.out.is_symlink():
        parser.error("preserve existing evidence")
    local_paths = [str(root), str(root / "src")]
    sys.path[:] = local_paths + [value for value in sys.path if value not in local_paths]
    original = json.JSONEncoder.default
    module = importlib.import_module("tests.test_d4d_to_synapse_table")
    first = json.JSONEncoder.default is original
    importlib.reload(module)  # SDK modules are cached on this second import.
    cached = json.JSONEncoder.default is original
    import data_sheets_schema
    from data_sheets_schema import native_catalog_reuse
    expected = root / "src/data_sheets_schema"
    origins = (Path(module.__file__).resolve() == root / "tests/test_d4d_to_synapse_table.py"
               and {Path(value).resolve() for value in data_sheets_schema.__path__} == {expected}
               and Path(native_catalog_reuse.__file__).resolve() == expected / "native_catalog_reuse.py")
    import pytest
    code = int(pytest.main([
        "-q", "-p", "no:cacheprovider", "-o", "addopts=",
        "--basetemp", str(args.out.parent / "scoped-sdk-cases"),
        str(root / "tests/test_d4d_to_synapse_table.py") + "::test_scoped_sdk_encoder_keeps_real_serialization",
        str(root / "tests/test_d4d_to_synapse_table.py") + "::test_sdk_encoder_scope_restores_entry_binding_after_exception",
    ]))
    restored = json.JSONEncoder.default is original
    evidence = {
        "root": str(root), "python": sys.version,
        "fresh_import_preserved_encoder": first,
        "cached_import_preserved_encoder": cached,
        "native_registry_ready": native_catalog_reuse._FUNCTIONS.ready,
        "source_origins_verified": origins,
        "scoped_tests_exitcode": code,
        "fixture_teardown_preserved_encoder": restored,
        "scope": "Fresh-process import, registry and actual fixture teardown checks; no native or scientific acceptance.",
    }
    raw = (json.dumps(evidence, indent=2, sort_keys=True) + "\n").encode()
    with args.out.open("xb") as stream:
        stream.write(raw)
    if args.out.read_bytes() != raw:
        raise RuntimeError("isolation evidence readback differs")
    print(json.dumps({"path": str(args.out), "sha256": hashlib.sha256(raw).hexdigest()}))
    return 0 if first and cached and origins and code == 0 and restored and evidence["native_registry_ready"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
