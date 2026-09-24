"""Selected immutable batch proposals, source-blind grammar and explicit assembly."""
import argparse
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import hashlib
import json
import os
from pathlib import Path
import shlex

from budgeted_cborg import BudgetStop
from .output_parts import canonical, describe, read_regular, same_json
from .draft_output import (_directory, _encoded, _exclusive, _preserve, _witness,
                           _sync, _registration_identity, _tool_identity, _tool_lines)
from .registration import strict_json

KIND = 'fresh_context_integrated_v1'
CHECKPOINT_KIND = 'closed_worker_checkpoint_integrated_v1'
MAX_ROUNDS, MAX_PARTS, MAX_PART_BYTES = 2, 64, 32768
MAX_BYTES = MAX_PARTS * MAX_PART_BYTES
MAX_DOCUMENT = 32 * 1024 * 1024


def plan(manifest):
    from data_sheets_schema.audit_batches import validate_plan
    path = manifest['audit_batches']['plan_path']
    value = strict_json(read_regular(path, MAX_DOCUMENT))
    original = read_regular(manifest['inputs']['original_full'], MAX_DOCUMENT).decode('utf-8')
    validate_plan(value, original)
    return value


@lru_cache(maxsize=32)
def _layout_json(registration_path, plan_path, attempt_dir, python, worker_cap, worker_ids,
                 max_rounds, max_parts, max_part_bytes, checkpoint=False):
    """Pure layout only: no file bytes, manifests, evidence or validation cached.

    Return immutable JSON; callers receive a fresh parsed value so a mutation
    cannot affect a later layout comparison. All filesystem reads and exact
    selector/plan validation remain outside this bounded cache.
    """
    path, root = Path(registration_path), Path(attempt_dir)
    command = [python, '-m', 'audit_controls.batch_output', '--registration', str(path)]
    children = []
    for name in ([*worker_ids, 'integration'] if not checkpoint else ['integration']):
        child = root / 'children' / name
        output = child / 'output'
        static = path.parent / 'batch-inputs' / name
        children.append({'id': name, 'kind': 'integration' if name == 'integration' else 'worker',
            'attempt_dir': str(child), 'output_dir': str(output),
            'proposal_path': str(output / 'proposal.json'),
            'instruction': str(child / 'instruction.md') if name == 'integration' else str(static / 'instruction.md'),
            'system_prompt': str(static / 'system.md'),
            'rounds': [{'round': number, 'parts': [str(output / 'drafts' / f'round-{number}' / f'{i:06d}.txt')
                         for i in range(1, max_parts + 1)],
                        'check_argv': [*command, '--child', name, '--round', str(number)]}
                       for number in range(1, max_rounds + 1)],
            'seal_argv': [*command, '--child', name, '--seal']})
    value = {'kind': KIND, 'plan_path': str(plan_path), 'worker_total_cap_usd': worker_cap,
            'max_rounds': max_rounds, 'max_parts': max_parts, 'max_part_bytes': max_part_bytes,
            'children': children, 'integration_base': str(path.parent / 'batch-inputs/integration/base.md'),
            'integration_index': str(root / 'children/integration/proposal-index.json'),
            'assemble_argv': [*command, '--child', 'integration', '--assemble']}
    if checkpoint:
        value['kind'] = CHECKPOINT_KIND
        del value['worker_total_cap_usd']
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def specification(manifest, registration_path, *, worker_total_cap_usd=None, plan_path=None):
    from .worker_checkpoint import KEY, selection
    checkpoint = KEY in manifest
    if checkpoint:
        selection(manifest[KEY])
        if worker_total_cap_usd is not None:
            raise BudgetStop('a closed-worker checkpoint has no new worker allowance')
    path = canonical(registration_path)
    plan_path = canonical(plan_path or path.parent / 'batch-plan.json')
    value = strict_json(read_regular(plan_path, MAX_DOCUMENT))
    root = canonical(manifest['job']['attempt_dir'])
    return json.loads(_layout_json(str(path), str(plan_path), str(root), manifest['python'],
        str(worker_total_cap_usd), tuple(r['id'] for r in value['workers']),
        MAX_ROUNDS, MAX_PARTS, MAX_PART_BYTES, checkpoint))


def configuration(manifest, registration_path=None):
    from .worker_checkpoint import KEY, selection
    if 'audit_batches' not in manifest:
        if KEY in manifest:
            raise BudgetStop('a worker checkpoint requires explicit batch integration')
        return None
    from .registration import scientific_contract, audit_batch_navigation
    scientific_contract(manifest)
    audit_batch_navigation(manifest)
    if (manifest.get('kind') != 'd4d_native_audit_continuation'
            or type(manifest.get('protocol_version')) is not int or manifest['protocol_version'] != 7
            or type(manifest.get('render_version')) is not int or manifest['render_version'] not in (20, 21, 22, 23)
            or any(k in manifest for k in ('audit_output', 'audit_drafting', 'context_recovery', 'audit_contract_context'))):
        raise BudgetStop('fresh batch integration requires only a selected native audit 7/20, 7/21, 7/22 or 7/23 mode')
    block = manifest['audit_batches']
    checkpoint = KEY in manifest
    if checkpoint:
        selection(manifest[KEY])
        if (manifest['render_version'] != 23 or type(block) is not dict
                or block.get('kind') != CHECKPOINT_KIND or 'worker_total_cap_usd' in block):
            raise BudgetStop('closed-worker integration requires the exact selected 7/23 layout')
    elif type(block) is not dict or type(block.get('worker_total_cap_usd')) is not str:
        raise BudgetStop('audit batch selector requires an explicit worker reservation ceiling')
    try:
        cap = None if checkpoint else Decimal(block['worker_total_cap_usd'])
        parent = Decimal(str(manifest['budget']['per_job_attempt_usd'][manifest['job']['id']]))
    except (KeyError, TypeError, ValueError, InvalidOperation) as error:
        raise BudgetStop('audit batch worker ceiling is invalid') from error
    if (not parent.is_finite() or parent <= 0
            or (not checkpoint and (not cap.is_finite() or not 0 < cap < parent))):
        raise BudgetStop('audit batch workers must reserve a positive portion below the parent cap')
    path = canonical(registration_path or Path(manifest['job']['attempt_dir']).parent.parent / 'registration.json')
    expected = specification(manifest, path, worker_total_cap_usd=block.get('worker_total_cap_usd'),
                             plan_path=block.get('plan_path'))
    if not same_json(block, expected):
        raise BudgetStop('audit batch selector differs from its exact deterministic layout')
    job = manifest['job']
    if (canonical(job['attempt_dir']) != path.parent / 'attempts' / job['id']
            or canonical(job['output_dir']) != canonical(job['attempt_dir']) / 'output'
            or canonical(job['audit_path']) != canonical(job['output_dir']) / 'audit.json'):
        raise BudgetStop('audit batch parent destination differs from its registered layout')
    plan(manifest)
    return block


def child(manifest, child_id):
    block = configuration(manifest)
    if block is None or type(child_id) is not str:
        raise BudgetStop('audit batch child is not selected')
    rows = [r for r in block['children'] if r['id'] == child_id]
    if len(rows) != 1:
        raise BudgetStop('audit batch child is outside its registered roster')
    return rows[0]


def required_paths(manifest):
    block = configuration(manifest)
    if block is None:
        return set()
    return {Path(block['plan_path']), Path(block['integration_base']),
            *(Path(r['system_prompt']) for r in block['children']),
            *(Path(r['instruction']) for r in block['children'] if r['kind'] == 'worker')}


def instruction(manifest, child_id):
    row = child(manifest, child_id)
    lines = ['Write a proposal as a consecutive nonempty prefix of the current round parts. '
             'Each part is at most 32768 UTF-8 bytes. Wait for every successful Write. '
             'Never rewrite a part, receipt, original, index or another child output. '
             'There are at most two source-blind grammar rounds; a helper execution failure is terminal.']
    for round in row['rounds']:
        lines += [f"Round {round['round']} parts: {Path(round['parts'][0]).parent}/000001.txt through 000064.txt",
                  shlex.join(round['check_argv'])]
    lines += ['Use round 2 only after round 1 returned passed=false. Once grammar passes, seal exactly once:',
              shlex.join(row['seal_argv'])]
    if row['kind'] == 'worker':
        lines += ['After successful sealing, finish with a final response. Do not run a source validator.']
    else:
        lines += ['Before sealing, Read every exact registered worker row-view file completely, including retained rows. '
                  'After sealing, assemble the complete explicitly authored integration:',
                  shlex.join(manifest['audit_batches']['assemble_argv']),
                  'Then run the single terminal source validator. After invoking it, call no further tool '
                  'and never repair or retry the audit:', shlex.join(manifest['job']['validator_argv'])]
    return '\n'.join(lines) + '\n'


def _number(number):
    if type(number) is not int or not 1 <= number <= MAX_ROUNDS:
        raise BudgetStop('batch draft round must be integer 1 or 2')
    return number


def draft_path(manifest, child_id, number):
    return Path(child(manifest, child_id)['output_dir']) / 'drafts' / f'round-{_number(number)}.json'


def check_paths(manifest, child_id, number):
    root = Path(child(manifest, child_id)['attempt_dir']); _number(number)
    return tuple(root / f'draft-round-{number}{suffix}.json' for suffix in ('', '_ready', '_failure'))


def seal_paths(manifest, child_id):
    root = Path(child(manifest, child_id)['attempt_dir'])
    return tuple(root / f'draft-seal{suffix}.json' for suffix in ('', '_ready', '_failure'))


def assembly_paths(manifest):
    root = Path(manifest['job']['attempt_dir'])
    return tuple(root / f'batch-assembly{suffix}.json' for suffix in ('', '_ready', '_failure'))


def read_round(manifest, child_id, number, allow_empty=False):
    row = child(manifest, child_id); _number(number)
    root = Path(row['output_dir']) / 'drafts'
    allowed = {f'round-{i}{suffix}' for i in (1, 2) for suffix in ('', '.json')}
    if any(p.name not in allowed for p in _directory(root, optional=True)):
        raise BudgetStop('batch draft container has extra entries')
    slots = row['rounds'][number - 1]['parts']
    names = sorted(p.name for p in _directory(Path(slots[0]).parent, optional=allow_empty))
    if ((not names and not allow_empty) or len(names) > MAX_PARTS
            or names != [Path(p).name for p in slots[:len(names)]]):
        raise BudgetStop('batch parts must be a nonempty contiguous registered prefix')
    pieces, parts = [], []
    for target in slots[:len(names)]:
        raw = read_regular(target, MAX_PART_BYTES)
        if not raw:
            raise BudgetStop('batch draft part is empty')
        raw.decode('utf-8', errors='strict')
        pieces.append(raw); parts.append(describe(target, raw))
    return b''.join(pieces), parts


def worker_artifacts(manifest):
    """Resolve complete worker drafts without assigning old work a new identity."""
    from .worker_checkpoint import KEY, validate
    configuration(manifest)
    if KEY in manifest:
        source = validate(manifest)
        return {r['id']: Path(source.proposal_refs[r['id']]['path']) for r in source.workers}
    return {r['id']: Path(r['proposal_path'])
            for r in manifest['audit_batches']['children'] if r['kind'] == 'worker'}


def proposals(manifest):
    return {name: read_regular(path, MAX_BYTES) for name, path in worker_artifacts(manifest).items()}


def _grammar(manifest, child_id, raw):
    from data_sheets_schema import audit_batches
    if child_id == 'integration':
        report = audit_batches.check_integration(raw, plan(manifest), proposals(manifest))
    else:
        report = audit_batches.check_worker(raw, plan(manifest), child_id)
    if type(report) is not dict or type(report.get('passed')) is not bool or len(_encoded(report)) > 16384:
        raise BudgetStop('batch grammar report is invalid or unbounded')
    return report


def _check_receipt(manifest, identity, child_id, number, raw, parts):
    return {'schema_version': 1, 'operation': 'batch_draft_grammar', 'checked': True,
        'job_id': manifest['job']['id'], 'registration_sha256': identity, 'child_id': child_id,
        'round': number, 'parts': parts, 'draft': describe(draft_path(manifest, child_id, number), raw),
        'grammar': _grammar(manifest, child_id, raw)}


def verify_check(manifest, identity, child_id, number, expected_parts):
    report = _witness(check_paths(manifest, child_id, number))
    raw, parts = read_round(manifest, child_id, number)
    if (not same_json(parts, expected_parts)
            or read_regular(draft_path(manifest, child_id, number), MAX_BYTES) != raw
            or not same_json(report, _check_receipt(manifest, identity, child_id, number, raw, parts))):
        raise BudgetStop('batch grammar receipt differs from exact native proposal bytes')
    return report


def check_summary(manifest, report):
    path = check_paths(manifest, report['child_id'], report['round'])[0]
    return {k: report[k] for k in ('schema_version', 'operation', 'job_id', 'registration_sha256', 'child_id', 'round', 'grammar')} | {
        'part_count': len(report['parts']), 'draft_sha256': report['draft']['sha256'],
        'draft_bytes': report['draft']['bytes'],
        'receipt_sha256': hashlib.sha256(read_regular(path, 131072, links=2)).hexdigest()}


def rounds(manifest, identity, child_id):
    checks, parts = [], []
    for number in (1, 2):
        _, current = read_round(manifest, child_id, number, allow_empty=True)
        started = any(os.path.lexists(p) for p in (*check_paths(manifest, child_id, number), draft_path(manifest, child_id, number)))
        if number > 1 and (current or started) and (len(checks) != number - 1 or checks[-1]['grammar']['passed']):
            raise BudgetStop('second batch draft requires the first grammar failure')
        if started:
            checks.append(verify_check(manifest, identity, child_id, number, current))
        parts.append(current)
    return checks, parts


def _seal_receipt(manifest, identity, child_id, number, raw, parts, checks):
    row = child(manifest, child_id)
    return {'schema_version': 1, 'operation': 'seal_batch_draft', 'passed': True,
        'job_id': manifest['job']['id'], 'registration_sha256': identity, 'child_id': child_id,
        'round': number, 'parts': parts, 'proposal': describe(row['proposal_path'], raw),
        'checks': [{'round': c['round'], 'passed': c['grammar']['passed'],
                    'receipt_sha256': check_summary(manifest, c)['receipt_sha256']} for c in checks]}


def verify_seal(manifest, identity, child_id, expected_round=None, expected_parts=None):
    report = _witness(seal_paths(manifest, child_id))
    checks, rosters = rounds(manifest, identity, child_id)
    if not checks or not checks[-1]['grammar']['passed'] or any(rosters[len(checks):]):
        raise BudgetStop('batch seal must bind the last grammar-passing draft')
    number = len(checks)
    raw, parts = read_round(manifest, child_id, number)
    if ((expected_round is not None and expected_round != number)
            or (expected_parts is not None and not same_json(expected_parts, parts))
            or read_regular(child(manifest, child_id)['proposal_path'], MAX_BYTES) != raw
            or not same_json(report, _seal_receipt(manifest, identity, child_id, number, raw, parts, checks))):
        raise BudgetStop('batch seal differs from its registered exact proposal and draft history')
    return report


def seal_summary(manifest, report):
    return {k: report[k] for k in ('schema_version', 'operation', 'passed', 'job_id', 'registration_sha256', 'child_id', 'round')} | {
        'part_count': len(report['parts']), 'proposal_sha256': report['proposal']['sha256'],
        'proposal_bytes': report['proposal']['bytes'],
        'receipt_sha256': hashlib.sha256(read_regular(seal_paths(manifest, report['child_id'])[0], 131072, links=2)).hexdigest()}


def verify_open(manifest):
    block = configuration(manifest)
    if block is None:
        return
    identity = _registration_identity(manifest)
    root = Path(manifest['job']['attempt_dir']) / 'children'
    allowed = {r['id'] for r in block['children']}
    if any(p.name not in allowed for p in _directory(root, optional=True)):
        raise BudgetStop('audit children differ from their registered roster')
    for row in block['children']:
        if not os.path.lexists(row['attempt_dir']):
            continue
        checks, rosters = rounds(manifest, identity, row['id'])
        if checks and len(checks) == MAX_ROUNDS and not checks[-1]['grammar']['passed']:
            raise BudgetStop('batch exhausted source-blind grammar rounds')
        if any(os.path.lexists(p) for p in (*seal_paths(manifest, row['id']), row['proposal_path'])):
            verify_seal(manifest, identity, row['id'])
    if any(os.path.lexists(p) for p in (*assembly_paths(manifest), manifest['job']['audit_path'])):
        validate_output(manifest)


def check_round(manifest, identity, child_id, number):
    row = child(manifest, child_id); _number(number)
    checks, rosters = rounds(manifest, identity, child_id)
    if (len(checks) != number - 1 or (checks and checks[-1]['grammar']['passed']) or any(rosters[number:])
            or any(os.path.lexists(p) for p in (*seal_paths(manifest, child_id), row['proposal_path']))):
        raise BudgetStop('batch grammar invocation is out of sequence')
    def produce():
        raw, parts = read_round(manifest, child_id, number)
        report = _check_receipt(manifest, identity, child_id, number, raw, parts)
        _exclusive(draft_path(manifest, child_id, number), raw)
        for item in parts:
            _sync(item['path'])
        _sync(Path(parts[0]['path']).parent, directory=True)
        _sync(draft_path(manifest, child_id, number).parent, directory=True)
        if read_round(manifest, child_id, number) != (raw, parts):
            raise BudgetStop('batch draft changed while preserving its grammar result')
        return report
    return _preserve(check_paths(manifest, child_id, number), produce)


def seal(manifest, identity, child_id):
    row = child(manifest, child_id)
    checks, rosters = rounds(manifest, identity, child_id)
    if not checks or not checks[-1]['grammar']['passed'] or any(rosters[len(checks):]):
        raise BudgetStop('only the latest grammar-passing batch proposal can be sealed')
    number = len(checks)
    def produce():
        raw, parts = read_round(manifest, child_id, number)
        _exclusive(row['proposal_path'], raw); _sync(row['output_dir'], directory=True)
        if rounds(manifest, identity, child_id) != (checks, rosters):
            raise BudgetStop('batch history changed while sealing')
        return _seal_receipt(manifest, identity, child_id, number, raw, parts, checks)
    return _preserve(seal_paths(manifest, child_id), produce)


def worker_closures(manifest, identity):
    from .batch_native import verify_child_closure, verify_checkpoint_context
    from .worker_checkpoint import KEY, validate
    if KEY in manifest:
        source = validate(manifest)
        verify_checkpoint_context(manifest, source)
        closed = []
        for row in source.workers:
            receipt = verify_child_closure(source.manifest, source.sha256, row['id'])
            if receipt['closure_sha256'] != source.closure_refs[row['id']]['sha256']:
                raise BudgetStop('inherited worker closure changed')
            closed.append(receipt)
        return closed
    return [verify_child_closure(manifest, identity, r['id'])
            for r in configuration(manifest)['children'] if r['kind'] == 'worker']


def checkpoint_lineage(manifest, closed):
    """Explicit old registration identities; no old charge becomes current work."""
    from .worker_checkpoint import KEY, validate
    if KEY not in manifest:
        return None
    source = validate(manifest)
    expected = [(r['id'], source.closure_refs[r['id']]['sha256']) for r in source.workers]
    if [(r['child_id'], r['closure_sha256']) for r in closed] != expected:
        raise BudgetStop('checkpoint lineage omits or changes an original worker')
    return {'kind': 'collective_closed_workers_v1', 'proof_sha256': source.proof_sha256,
            'source_registration': {'path': str(source.registration_path), 'sha256': source.sha256},
            'workers': [{'id': r['child_id'], 'registration_sha256': source.sha256,
                         'closure': source.closure_refs[r['child_id']],
                         'proposal': source.proposal_refs[r['child_id']]} for r in closed]}


def _assembled(manifest, identity):
    from data_sheets_schema.audit_batches import assemble
    workers = worker_closures(manifest, identity)
    integration = verify_seal(manifest, identity, 'integration')
    raw, lineage = assemble(plan(manifest), proposals(manifest),
        read_regular(child(manifest, 'integration')['proposal_path'], MAX_BYTES))
    if len(raw) > MAX_DOCUMENT:
        raise BudgetStop('assembled batch audit exceeds the registered bound')
    lineage_raw = _encoded(lineage)
    receipt = {'schema_version': 1, 'operation': 'assemble_audit_batches', 'passed': True,
        'job_id': manifest['job']['id'], 'registration_sha256': identity,
        'workers': [{'id': r['child_id'], 'closure_sha256': r['closure_sha256']} for r in workers],
        'integration': integration['proposal'], 'audit': describe(manifest['job']['audit_path'], raw),
        'lineage': describe(Path(manifest['job']['output_dir']) / 'integration-lineage.json', lineage_raw)}
    inherited = checkpoint_lineage(manifest, workers)
    if inherited is not None:
        receipt['worker_checkpoint'] = inherited
    return raw, lineage_raw, receipt


def assemble_output(manifest, identity):
    def produce():
        raw, lineage, receipt = _assembled(manifest, identity)
        _exclusive(manifest['job']['audit_path'], raw)
        _exclusive(receipt['lineage']['path'], lineage)
        _sync(manifest['job']['output_dir'], directory=True)
        if _assembled(manifest, identity) != (raw, lineage, receipt):
            raise BudgetStop('batch proposals changed during assembly')
        return receipt
    return _preserve(assembly_paths(manifest), produce)


def assembly_summary(manifest, report):
    return {k: report[k] for k in ('schema_version', 'operation', 'passed', 'job_id', 'registration_sha256')} | {
        'audit_sha256': report['audit']['sha256'], 'audit_bytes': report['audit']['bytes'],
        'lineage_sha256': report['lineage']['sha256'],
        'receipt_sha256': hashlib.sha256(read_regular(assembly_paths(manifest)[0], 131072, links=2)).hexdigest()}


def validate_output(manifest):
    identity = _registration_identity(manifest)
    report = _witness(assembly_paths(manifest))
    raw, lineage, expected = _assembled(manifest, identity)
    if (not same_json(report, expected) or read_regular(manifest['job']['audit_path'], MAX_DOCUMENT) != raw
            or read_regular(expected['lineage']['path'], MAX_DOCUMENT) != lineage):
        raise BudgetStop('batch assembly receipt or exact final bytes changed')
    return report


def closure_paths(manifest, registration_path, result):
    from .batch_native import verify_aggregate_closure
    return verify_aggregate_closure(manifest, registration_path, result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--child', required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--round', type=int); group.add_argument('--seal', action='store_true')
    group.add_argument('--assemble', action='store_true')
    args = parser.parse_args(argv)
    from .registration import validate_registration
    manifest = validate_registration(args.registration)
    identity = _registration_identity(manifest)
    if args.assemble:
        if args.child != 'integration':
            raise BudgetStop('only the integration child may assemble the audit')
        report = assembly_summary(manifest, assemble_output(manifest, identity))
    elif args.seal:
        report = seal_summary(manifest, seal(manifest, identity, args.child))
    else:
        report = check_summary(manifest, check_round(manifest, identity, args.child, args.round))
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
