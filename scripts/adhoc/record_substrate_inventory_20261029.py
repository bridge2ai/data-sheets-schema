#!/usr/bin/env python3
# Purpose: register new F6 digest inventories without changing historical entries.
# Inputs: generated schema 3.1.0 and profiles; output: digest_inventory.yaml.
# Generality F6, 2026-10-29.
import json
from data_sheets_schema import schema_digest as digest
from data_sheets_schema.profiles import PROFILES

for name, profile in PROFILES.items():
    digest.record_inventory(profile=profile)
    fingerprint = digest.fingerprint(digest.digest_text('Dataset', profile=profile))
    assert digest.slot_existed_at(fingerprint, 'Dataset', 'instances') is True
    print(json.dumps({'profile': name, 'digest_md5': fingerprint}))
