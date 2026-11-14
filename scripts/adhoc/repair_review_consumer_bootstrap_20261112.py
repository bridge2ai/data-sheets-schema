#!/usr/bin/env python3
"""Repair helper-2 v3 source verification inside the input-only consumer.
Inputs/outputs: review validator and source-mutation regression, 2026-11-12.
Preserve exact registered script hashing without importing verifier bootstrap.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[2]
p=root/'src/data_sheets_schema/native_launch_review.py'; raw=p.read_text()
old="SEQUENCE_SOURCE = 'src/data_sheets_schema/native_launch_sequence.py'"
assert raw.count(old)==1
raw=raw.replace(old,old+"\nSOURCE_ROOT = Path(__file__).resolve().parents[2]")
old='''            from . import native_execution_authority_v2 as authority
            authority._verified_source_bytes(authority.ROOT / SEQUENCE_SOURCE, digest)'''
new='''            # This reader also runs inside the verified input-only consumer,
            # which must never import the verifier bootstrap. Its own pinned
            # physical source location selects the checkout; the stable regular
            # read independently checks the registered script's actual bytes.
            script = wire.read_regular(SOURCE_ROOT / SEQUENCE_SOURCE)
            if wire.sha(script) != digest:
                raise ValueError('sequence source bytes differ from their registered pin')'''
assert raw.count(old)==1;p.write_text(raw.replace(old,new))
p=root/'tests/test_native_review_bundle_v3.py';raw=p.read_text()
old="    monkeypatch.setattr(authority, 'ROOT', tmp_path / 'source')"
assert raw.count(old)==1
p.write_text(raw.replace(old,"    monkeypatch.setattr(review, 'SOURCE_ROOT', tmp_path / 'source')"))
