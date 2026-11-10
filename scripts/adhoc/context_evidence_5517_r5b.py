"""PR #5532, 2026-11-08: restore D120/A23 quotations and audit exact bytes.

Inputs: pinned bundles/context YAML. Outputs: context edits and scratch byte audit.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import yaml
from data_sheets_schema.evaluation_context import context_digest

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('D4D_5517_SCRATCH', ROOT.parent / 'scratch-5517'))
assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
audit = []

def format_row(name):
    # Preserve literal table spacing and URL bytes from the serialized README.
    source = (ROOT / 'data/preprocessed/concatenated/AI_READI_preprocessed.txt').read_text()
    return re.search(r'\| '+name+r' +\|[^\\\n]+', source)[0]

def restore(project, additions, notes=None):
    path = ROOT / f'data/context/{project.lower()}_context.yaml'
    text = path.read_text()
    manifest_path = ROOT / re.search(r'^# Bundle chunks: (\S+)', text, re.M)[1]
    manifest = yaml.safe_load(manifest_path.read_text())
    directory = manifest_path.parent if project == 'KIDS_FIRST' else ROOT / 'data/preprocessed/concatenated'
    raw = (directory / manifest['bundle']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    lines = raw.splitlines(keepends=True)
    chunks = {}
    starts = {}
    for item in manifest['chunks']:
        start, end = item['lines']
        part = b''.join(lines[start-1:end])
        assert hashlib.sha256(part).hexdigest() == item['sha256']
        chunks[item['id']] = part
        starts[item['id']] = sum(map(len, lines[:start-1]))
    context = yaml.safe_load(text)
    for predicate, pairs in additions.items():
        old = context[predicate]['evidence']
        evidence = old
        if project == 'AI_READI':
            for term, name in [('Earth Science Data Systems (ESDS) format', 'environment'),
                               ('Open mHealth', 'wearable_activity_monitor')]:
                evidence = evidence.replace('[chunks: c019] '+json.dumps(term),
                                            '[chunks: c019] '+json.dumps(format_row(name)))
        if notes and predicate in notes and not evidence.startswith('[search_notes] '):
            evidence = '[search_notes] ' + json.dumps(notes[predicate]) + ' ' + evidence
        for cid, quote in pairs:
            encoded = quote.encode()
            assert encoded in chunks[cid], (project, predicate, cid)
            offset = starts[cid] + chunks[cid].index(encoded)
            audit.append(dict(project=project, predicate=predicate, chunk=cid,
                              quote=quote, utf8_hex=encoded.hex(), bundle_byte_offset=offset,
                              bundle_line=raw[:offset].count(b'\n')+1,
                              bundle_sha256=manifest['bundle_sha256']))
            citation = f'[chunks: {cid}] ' + json.dumps(quote, ensure_ascii=False)
            if citation not in evidence:
                evidence += ' ' + citation
        text = text.replace('  evidence: ' + json.dumps(old, ensure_ascii=False),
                            '  evidence: ' + json.dumps(evidence, ensure_ascii=False))
        # Existing files use JSON-compatible YAML strings; verify replacement.
        assert yaml.safe_load(text)[predicate]['evidence'] == evidence
    for predicate in additions:
        block = re.search(rf'^{predicate}:\n.*?(?=\n\w|\Z)', text, re.M | re.S)
        ids = list(dict.fromkeys(re.findall(r'\[chunks: (c\d{3})\]', yaml.safe_load(text)[predicate]['evidence'])))
        updated = re.sub(r'  # chunks: \[[^\]]*\]', '  # chunks: ['+', '.join(ids)+']', block[0])
        text = text[:block.start()] + updated + text[block.end():]
    path.write_text(text)

restore('VOICE_PEDIATRIC', {
    'human_subjects': [('c003', 'Data collection and sharing was approved by the Research Ethics Board at the Hospital for Sick Children.'),
                       ('c005', 'When children will be participating in the research, parents or guardians will provide consent, and children will provide verbal assent where appropriate.')],
    'data_processing': [('c003', 'b2ai-voice-pediatric v1.1: No new participants released in this minor update, but releasing audio features for all free speech tasks that were manually checked for presence of unconsented speakers and PII.')],
}, {'data_processing': 'Release qualification for v1.1.0: manual checking is documented by the c003 release note quoted below; retained c002 describes feature derivation.'})
restore('AI_READI', {p: [('c019', format_row('environment')),
                        ('c019', format_row('wearable_activity_monitor')),
                        ('c019', '| Processing   | custom / ad hoc | automated + custom |automated + custom | automated + custom |')]
                     for p in ('data_processing', 'processing_software')},
        {p: 'D120: c019 supplies contextual file-format standards and automated + custom processing evidence; it does not identify processing software. D104 direct software evidence remains in c018.'
         for p in ('data_processing', 'processing_software')})
restore('KIDS_FIRST', {'processing_software': [('c013', 'Common Workflow Language (CWL) (https://www.commonwl.org)\nfor describing and running tools and workflows in CAVATICA')]})
target = OUT / 'r5b-restored-quotation-bytes.json'
target.write_text(json.dumps(audit, indent=2, ensure_ascii=False)+'\n')
assert json.loads(target.read_text()) == audit

record_path = ROOT / 'scripts/adhoc/context_evidence_5517_r3_kids_first_search.txt'
record = record_path.read_text()
original = next(line for line in record.splitlines() if line.startswith(('# Original command (JSON argv): ', '# Command (JSON argv): ')))
argv = json.loads(original.split(': ', 1)[1])
assert argv[:5] == ['rg', '--hidden', '--no-ignore', '-n', '-i']
replacement = ['python', 'scripts/adhoc/context_evidence_5517_search.py', *argv[5:]]
if '# Equivalent:' not in record:
    record_path.write_text(record.replace(original,
    original.replace('# Command', '# Original command') + '\n' +
    '# Equivalent: Python re.IGNORECASE, direct whole-file read including ignored/hidden files.\n' +
        '# Command (JSON argv): ' + json.dumps(replacement)))
path = ROOT / 'data/context/kids_first_context.yaml'
text = path.read_text()
text = text.replace('Reproducible helper: scripts/adhoc/context_evidence_5517_r3.py;',
    'Original rg search retained in the search record. Equivalent reproducible helper: scripts/adhoc/context_evidence_5517_search.py (Python re.IGNORECASE, direct entire-file read including ignored/hidden files);')
path.write_text(text)

# D102 permits updating only the current context digest table, not old captures.
pin_path = ROOT / 'notes/reviews/v10_human_decisions_and_context_review_2026-10-20.md'
pin_text = pin_path.read_text()
for project in ('AI_READI', 'VOICE_PEDIATRIC', 'KIDS_FIRST'):
    context = yaml.safe_load((ROOT / f'data/context/{project.lower()}_context.yaml').read_text())
    pin_text, count = re.subn(rf'(^\| \*\*{project}\*\* \| `data/context/[^`]+` \| `)[a-f0-9]{{64}}',
                             lambda match: match[1]+context_digest(context), pin_text, flags=re.M)
    assert count == 1
pin_path.write_text(pin_text)
