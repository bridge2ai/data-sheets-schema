#!/usr/bin/env python3
"""Bind C18 envelope comparison to saved C10 evidence, PR6294, 2026-11-19.

Inputs: an exact e772 checkout, genuine saved observation, pinned measurements.
Output: one fresh comparison or refusal receipt; never overwrite an existing file.
No native/provider/network execution. Old comparator and measurements are preserved.
Saved probe validation proves byte consistency, not human or account authentication.
Retained helper copy for the explicit model-label amendment; source gates remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
TARGET = 'e7721b603763ec131540c5e1a8a1d4ab16df5a1c'
DEFAULT_CHECKOUT = Path('/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/native-production-e7721b603763')
COMPARATOR = Path(__file__).resolve().with_name('codex196_compare_envelopes_20261119.py')
COMPARATOR_SHA256 = 'faa4d121888f096fa1f1f1737fb991d697fd2fb19635cc3cf89118f6f59f8560'
MAX_JSON_BYTES = 32_000_000


def observed_model_usage(runtime, terminal):
    from data_sheets_schema import native_model_aliases as aliases
    pair = aliases.model_aliases(runtime)
    aliases.require_model_usage(terminal, pair)
    return terminal['modelUsage'][aliases.reported_model(pair)]


def physical(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or path.resolve() != path:
        raise ValueError('expected a canonical absolute path: ' + str(path))
    return path


def pin_file(path):
    path = physical(path)
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('expected an ordinary file: ' + str(path))
    digest = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(262144), b''):
            digest.update(chunk)
            size += len(chunk)
    after = path.lstat()
    stable_fields = ('st_dev', 'st_ino', 'st_mode', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    if size != info.st_size or any(getattr(after, key) != getattr(info, key) for key in stable_fields):
        raise ValueError('file changed while hashing: ' + str(path))
    return {'path': str(path), 'bytes': size, 'sha256': digest.hexdigest()}


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def load_pinned(path, limit=MAX_JSON_BYTES):
    pin = pin_file(path)
    if not 0 < pin['bytes'] <= limit:
        raise ValueError('JSON evidence exceeds the nonempty size bound')
    raw = Path(path).read_bytes()
    if len(raw) != pin['bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']:
        raise ValueError('JSON evidence changed while reading')
    return json.loads(raw, object_pairs_hook=object_pairs), pin


def git(checkout, *args):
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1',
                       GIT_TERMINAL_PROMPT='0', GIT_ALLOW_PROTOCOL='file')
    completed = subprocess.run(['/usr/bin/git', '--no-replace-objects',
        '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
        '-C', str(checkout), *args], check=True, capture_output=True,
        timeout=30, env=environment)
    return completed.stdout


def verify_source(checkout):
    checkout = physical(checkout)
    if git(checkout, 'rev-parse', 'HEAD').decode().strip() != TARGET:
        raise ValueError('checkout is not the fixed e772 source')
    if git(checkout, 'diff', '--no-ext-diff', '--no-textconv', '--name-only', 'HEAD').strip():
        raise ValueError('tracked checkout bytes differ from e772')
    return checkout


def measurement_pins(evidence):
    declared = evidence.get('verified_artifact_pins')
    if type(declared) is not list or not declared:
        raise ValueError('measurement/source pins are required')
    pins = {}

    def visit(value):
        if type(value) is dict:
            if {'path', 'bytes', 'sha256'} <= set(value):
                selected = {key: value[key] for key in ('path', 'bytes', 'sha256')}
                if (type(selected['path']) is not str or type(selected['bytes']) is not int
                        or selected['bytes'] < 0 or type(selected['sha256']) is not str
                        or re.fullmatch('[0-9a-f]{64}', selected['sha256']) is None):
                    raise ValueError('malformed measurement pin')
                if pin_file(selected['path']) != selected:
                    raise ValueError('measurement/source bytes changed: ' + selected['path'])
                if selected['path'] in pins and pins[selected['path']] != selected:
                    raise ValueError('conflicting measurement pins')
                pins[selected['path']] = selected
            for child in value.values():
                visit(child)
        elif type(value) is list:
            for child in value:
                visit(child)

    for item in declared:
        if type(item) is not dict or not {'path', 'bytes', 'sha256'} <= set(item):
            raise ValueError('invalid declared measurement/source pin')
    visit(evidence)
    return sorted(pins.values(), key=lambda item: item['path'])


def import_comparator():
    pin = pin_file(COMPARATOR)
    if pin['sha256'] != COMPARATOR_SHA256:
        raise ValueError('the frozen original comparator changed')
    spec = importlib.util.spec_from_file_location('c18_frozen_comparator', COMPARATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, pin


def native_source_pins(checkout):
    source = checkout / 'src'
    pins = []
    for name, module in sorted(sys.modules.items()):
        if name == 'data_sheets_schema' or name.startswith('data_sheets_schema.'):
            filename = getattr(module, '__file__', None)
            if filename is None:
                # This source tree deliberately uses a namespace package.
                locations = list(getattr(module, '__path__', []))
                if (name != 'data_sheets_schema' or not locations
                        or any(physical(item) != source / 'data_sheets_schema' for item in locations)):
                    raise ValueError('native namespace is outside the selected checkout: ' + name)
                continue
            path = physical(filename)
            if not path.is_relative_to(source):
                raise ValueError('native module imported outside selected checkout: ' + name)
            pin = pin_file(path)
            blob = git(checkout, 'show', 'HEAD:' + path.relative_to(checkout).as_posix())
            if hashlib.sha256(blob).hexdigest() != pin['sha256']:
                raise ValueError('imported native source differs from e772: ' + name)
            pins.append(pin)
    return pins


def compare_bound(args):
    checkout = verify_source(args.checkout)
    evidence, evidence_pin = load_pinned(args.evidence)
    if evidence_pin['sha256'] != args.evidence_sha256:
        raise ValueError('measurement SHA256 differs from the supplied immutable pin')
    if (type(evidence.get('schema_version')) is not int or evidence['schema_version'] != 1
            or evidence.get('source_commit') != TARGET or evidence.get('checkout') != str(checkout)):
        raise ValueError('measurement schema, source or checkout is not the selected e772 source')
    all_pins = measurement_pins(evidence)
    observation, observation_pin = load_pinned(args.observation, 4_000_000)
    sys.path.insert(0, str(checkout / 'src'))
    from data_sheets_schema.native_u4b_probe_sequence import validate_observation
    from data_sheets_schema.native_model_aliases import model_aliases
    from data_sheets_schema.native_runtime_profiles import require_production
    native_source_pins(checkout)
    validated = validate_observation(args.observation, expected_pin=observation_pin)
    runtime = require_production(validated['provisional_runtime'])
    transcript_pin = validated['transcript']
    if pin_file(transcript_pin['path']) != transcript_pin:
        raise ValueError('validated transcript changed before limit extraction')
    raw = Path(transcript_pin['path']).read_bytes()
    if len(raw) != transcript_pin['bytes'] or hashlib.sha256(raw).hexdigest() != transcript_pin['sha256']:
        raise ValueError('transcript changed while reading its terminal')
    terminal_pin = validated['terminal']
    lines = raw.splitlines()
    line = terminal_pin['line']
    if type(line) is not int or line != len(lines) or line < 1:
        raise ValueError('validated terminal is not the final complete transcript line')
    if hashlib.sha256(lines[line - 1]).hexdigest() != terminal_pin['sha256']:
        raise ValueError('validated terminal bytes changed')
    terminal = json.loads(lines[line - 1], object_pairs_hook=object_pairs)
    aliases = model_aliases(runtime)
    if evidence['tokenization'].get('selected_model') != aliases['requested']:
        raise ValueError('measurement tokenizer model differs from the observed requested model')
    usage = observed_model_usage(runtime, terminal)
    context_window, max_output_tokens = usage['contextWindow'], usage['maxOutputTokens']
    comparator, comparator_pin = import_comparator()
    result = comparator.compare(evidence, context_window, max_output_tokens, 'observed_arguments')
    source_pins = native_source_pins(checkout)
    if pin_file(args.evidence) != evidence_pin or measurement_pins(evidence) != all_pins:
        raise ValueError('measurement evidence changed during comparison')
    if validate_observation(args.observation, expected_pin=observation_pin) != validated:
        raise ValueError('observation evidence changed during comparison')
    verify_source(checkout)
    result.update(kind='d4d_post_probe_envelope_comparison_e772_v1', status='COMPARED',
        evidence=evidence_pin, verified_artifact_pins=all_pins, verified_pin_count=len(all_pins),
        comparator=comparator_pin, adapter=pin_file(Path(__file__).resolve()),
        native_validator_source_commit=TARGET, native_validator_source_pins=source_pins,
        observation=observation_pin, observation_artifact_pins={key: observation[key] for key in
            ('authorization', 'provisional_runtime', 'claim', 'invocation', 'transcript', 'request')},
        terminal=terminal_pin, model_aliases=aliases, saved_observation_validated=True,
        synthetic_observation_allowed=False, native_calls=0, provider_calls=0,
        launch_authority=False,
        scope='Offline C18 comparison using limits extracted from a validated saved C10 terminal. '
              'Saved scripted evidence establishes byte consistency, not authenticated human/account '
              'authority or independently witnessed probe execution. Completeness and tokenizer '
              'refusals remain unchanged. This receipt supplies no launch authority.')
    result['limits']['source'] = 'validated_saved_observation_terminal'
    result['limits']['numeric_limit_arguments_supplied'] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--checkout', type=Path, default=DEFAULT_CHECKOUT)
    parser.add_argument('--observation', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--evidence-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if re.fullmatch('[0-9a-f]{64}', args.evidence_sha256) is None:
        parser.error('evidence-sha256 requires exactly 64 lowercase hexadecimal characters')
    output = physical(args.output)
    if output.exists() or output.is_symlink():
        parser.error('output must be fresh; existing receipts are never overwritten')
    try:
        result = compare_bound(args)
        code = 0 if result['overall'] == 'PASS' else 2
    except Exception as error:
        result = dict(kind='d4d_post_probe_envelope_comparison_e772_v1', status='REFUSED',
            overall='FAIL', expected_source_commit=TARGET, checkout=str(args.checkout),
            requested_observation=str(args.observation), requested_evidence=str(args.evidence),
            requested_evidence_sha256=args.evidence_sha256, error_type=type(error).__name__,
            reason=str(error), saved_observation_validated=False, launch_authority=False,
            native_calls=0, provider_calls=0, adapter=pin_file(Path(__file__).resolve()))
        code = 1
    raw = (json.dumps(result, sort_keys=True, indent=2) + '\n').encode()
    with output.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    actual = pin_file(output)
    if actual['sha256'] != hashlib.sha256(raw).hexdigest() or actual['bytes'] != len(raw):
        raise ValueError('saved comparison receipt differs from rendered bytes')
    print(json.dumps(dict(output=actual, status=result['status'], overall=result['overall'],
                          returncode=code), sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
