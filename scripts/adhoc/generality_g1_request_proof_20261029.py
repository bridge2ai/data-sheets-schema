#!/usr/bin/env python3
# Purpose: capture exact shared-v1 request bytes before/after G1 (F6).
# Inputs: current checkout and retained sizing fixtures; outputs: external JSON.
# No provider calls, run outputs or pin rotations. Generality G1, 2026-10-29.
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from scripts import build_api_registrations as builder
from data_sheets_schema import api_runner as api, shared_generation as sg, receipt_completion as receipts


def capture(output):
    # The same paths and declared identity are used on both sides of the proof.
    fixture = Path('/private/tmp/g1-request-authority')
    fixture.mkdir(exist_ok=True)
    project = 'CHORUS'
    reg = builder.build_registration(project, '2026-10-29_generality-proof',
        registration_path=fixture / 'registration.json', partition='chorus',
        write_to_disk=False)
    raw = sg.canonical(reg)
    Path(reg['registration_path']).write_bytes(raw)
    inputs = reg['inputs']
    spec = api.RunSpec(**reg['run'], bundle=Path(inputs['bundle']['path']),
        chunk_manifest=Path(inputs['chunk_manifest']['path']), manifest=Path(inputs['source_manifest']['path']),
        condition='generic_v10', render_version=25, shared_generation_version=1,
        shared_generation_registration=raw.decode(), api_playbook_version=2,
        receipt_completion_version=2, receipt_completion_registration=sg.canonical(reg['receipt']).decode(),
        profile=inputs['profile']['name'], profile_basis=inputs['profile']['basis'],
        run_date='2026-10-29', out_dir=fixture / 'unused-output', provider=reg['runtime']['provider'])
    settings = api._model_settings(spec.condition)
    spec.bind_api_header_values(settings)
    request = api.build_phase(spec, 'full', carry={})
    payload = receipts.request_payload(request, settings,
        {'max_output_tokens': api.phase_max_tokens(spec, 'full', 128000)})
    document = {'registration': reg, 'request': asdict(request), 'payload': payload,
                'payload_sha256': sg.sha(sg.canonical(payload))}
    output.write_bytes(sg.canonical(document))
    assert output.stat().st_size > 0 and not spec.out_dir.exists()
    print(json.dumps({'bytes': len(sg.canonical(payload)), 'sha256': document['payload_sha256']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    capture(parser.parse_args().output)
