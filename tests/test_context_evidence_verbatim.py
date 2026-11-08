"""D101 exact quotations with cited-chunk provenance; explicit unresolved states.

Quotation validation is lexical, not an automatic entailment judgment. D103
absence support and unresolved evidence are separately counted, never skipped.
No fuzzy, case-folded or whitespace-normalized matching.
"""
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTEXTS = sorted((ROOT / 'data/context').glob('*_context.yaml'))
PREDICATES = {'human_subjects', 'regulated_access', 'shared_dataset',
              'data_collection', 'data_processing', 'processing_software', 'ml_training_dataset'}
NEEDS_OWNER = set()
ABSENCE_SUPPORTED = {('kids_first_context', 'ml_training_dataset')}
OWNER_DECISIONS = {
    ('chorus_context', 'regulated_access'): "[curator_assertion: true; accepted by the owner's human review, D52, 2026-10-27]",
    ('kids_first_context', 'ml_training_dataset'): "[curator_assertion: true; set to false by the owner's human review, D52, 2026-10-27]",
}


def parse_evidence(evidence):
    """Closed grammar: optional curator metadata, unresolved metadata, cited JSON strings."""
    remaining = evidence
    owner = None
    if remaining.startswith('[curator_assertion:'):
        match = re.match(r'\[curator_assertion: true; [^]\n]+\] ', remaining)
        assert match, 'invalid curator metadata'
        owner = match[0].rstrip()
        remaining = remaining[match.end():]
    state, notes = 'quoted', None
    decoder = json.JSONDecoder()
    for candidate in ('needs_owner', 'absence_supported'):
        prefix = f'[{candidate}: true] '
        if remaining.startswith(prefix):
            state = candidate
            remaining = remaining[len(prefix):]
            assert remaining.startswith('[search_notes] '), 'state requires notes'
            break
    if remaining.startswith('[search_notes] '):
        remaining = remaining[len('[search_notes] '):]
        notes, end = decoder.raw_decode(remaining)
        assert isinstance(notes, str) and len(notes.strip()) >= 40, 'substantive search notes required'
        remaining = remaining[end:].lstrip()
    quotations = []
    while remaining:
        match = re.match(r'\[chunks: (c\d{3}(?:, c\d{3})*)\] ', remaining)
        assert match, 'uncited text or malformed evidence metadata'
        ids = match[1].split(', ')
        remaining = remaining[match.end():]
        quote, end = decoder.raw_decode(remaining)
        assert isinstance(quote, str) and quote.strip(), 'nonempty quotation required'
        quotations.append((ids, quote))
        remaining = remaining[end:].lstrip()
    assert quotations, 'at least one cited quotation required, even for needs_owner context'
    return state, notes, owner, quotations


def validate_quotes(evidence, chunks):
    state, notes, owner, quotations = parse_evidence(evidence)
    for ids, quote in quotations:
        assert len(ids) == len(set(ids)), 'duplicate citation'
        for cid in ids:
            assert cid in chunks, f'unknown chunk {cid}'
            assert quote in chunks[cid], f'quotation not verbatim in cited chunk {cid}'
    return state, notes, owner


@lru_cache(maxsize=None)
def source_chunks(path):
    # Resolve the actual context declaration, not a silently inferred replacement bundle.
    match = re.search(r'^# Bundle chunks: (\S+)', path.read_text(), re.M)
    assert match
    manifest_path = ROOT / match[1]
    manifest = yaml.safe_load(manifest_path.read_text())
    project = path.stem.removesuffix('_context')
    if project == 'kids_first':
        assert match[1] == 'notes/matched_cborg_2026-09-13/kids_first/chunks.yaml'
        directory = manifest_path.parent
    else:
        source_manifest = yaml.safe_load((ROOT / 'data/preprocessed/source_manifest.yaml').read_text())
        assert project.upper() in source_manifest['projects']
        assert match[1] == f'data/preprocessed/chunks/{project.upper()}_chunks.yaml'
        directory = ROOT / 'data/preprocessed/concatenated'
    raw = (directory / manifest['bundle']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest['bundle_sha256']
    lines = raw.splitlines(keepends=True)
    chunks = {}
    for chunk in manifest['chunks']:
        first, last = chunk['lines']
        chunk_raw = b''.join(lines[first - 1:last])
        assert hashlib.sha256(chunk_raw).hexdigest() == chunk['sha256']
        chunks[chunk['id']] = chunk_raw.decode('utf-8')
    return chunks


def test_context_inventory_is_not_empty_or_partial():
    assert {path.stem for path in CONTEXTS} == {
        'ai_readi_context', 'chorus_context', 'cm4ai_context', 'kids_first_context',
        'voice_context', 'voice_pediatric_context',
    }
    counts = Counter()
    unresolved = set()
    for path in CONTEXTS:
        context = yaml.safe_load(path.read_text())
        assert set(context) == PREDICATES
        for pred, entry in context.items():
            state, _, _ = validate_quotes(entry['evidence'], source_chunks(path))
            counts[state] += 1
            if state == 'needs_owner':
                unresolved.add((path.stem, pred))
    assert unresolved == NEEDS_OWNER
    assert counts['quoted'] == 41
    assert counts['absence_supported'] == 1
    assert counts['needs_owner'] == 0
    assert sum(counts.values()) == 42


def test_literal_check_does_not_accept_terms_or_casefolding():
    quote = 'The resultant bam is de-dupped and base score recalibrated.'
    chunks = {'c006': quote, 'c007': 'Another document.'}
    evidence = '[chunks: c006] ' + json.dumps(quote)
    assert validate_quotes(evidence, chunks)[0] == 'quoted'
    for changed in ('GATK Base Quality Score Recalibration', quote.upper(), quote + ' HMB', quote.replace(' ', '  ')):
        with pytest.raises(AssertionError, match='not verbatim'):
            validate_quotes('[chunks: c006] ' + json.dumps(changed), chunks)
    for bad in (evidence.replace('c006', 'c007'), evidence.replace('c006', 'c999'),
                evidence + ' fabricated extension', '[chunks: c006] ""',
                '[needs_owner: true] ' + evidence,
                '[needs_owner: true] [search_notes] "" ' + evidence,
                '[needs_owner: true] [search_notes] "' + 'x' * 50 + '"'):
        with pytest.raises(AssertionError):
            validate_quotes(bad, chunks)
    # Unresolved entries cannot hide fabricated quoted text either.
    with pytest.raises(AssertionError, match='not verbatim'):
        validate_quotes('[needs_owner: true] [search_notes] "' + 'x' * 50 + '" [chunks: c006] "invented"', chunks)


@pytest.mark.corpus
@pytest.mark.parametrize('path,predicate', [(p, pred) for p in CONTEXTS for pred in sorted(PREDICATES)],
                         ids=[f'{p.stem}-{pred}' for p in CONTEXTS for pred in sorted(PREDICATES)])
def test_every_evidence_string_occurs_verbatim_in_its_bundle(path, predicate):
    entry = yaml.safe_load(path.read_text())[predicate]
    state, notes, owner = validate_quotes(entry['evidence'], source_chunks(path))
    key = (path.stem, predicate)
    assert state == ('needs_owner' if key in NEEDS_OWNER else
                     'absence_supported' if key in ABSENCE_SUPPORTED else 'quoted')
    assert owner == OWNER_DECISIONS.get(key)
    if state != 'quoted':
        assert notes and 'D52 value retained.' in notes
    # Explicitly retain every applicability decision, including the D52 negatives.
    expected = key in {('cm4ai_context', 'human_subjects'),
                      ('cm4ai_context', 'regulated_access'), *ABSENCE_SUPPORTED}
    assert entry['value'] is (not expected)


def test_absence_supported_search_is_reproducible():
    import subprocess
    import sys
    path = ROOT / 'data/context/kids_first_context.yaml'
    entry = yaml.safe_load(path.read_text())['ml_training_dataset']
    state, notes, _, _ = parse_evidence(entry['evidence'])
    assert state == 'absence_supported' and entry['value'] is False
    record = (ROOT / 'scripts/adhoc/context_evidence_5517_r3_kids_first_search.txt').read_text()
    command = json.loads(next(l.removeprefix('# Command (JSON argv): ') for l in record.splitlines()
                              if l.startswith('# Command (JSON argv): ')))
    assert command[:2] == ['python', 'scripts/adhoc/context_evidence_5517_search.py']
    pattern = command[2]
    assert command[-1] == 'notes/matched_cborg_2026-09-13/kids_first/KIDS_FIRST_preprocessed.txt'
    for term in ('artificial intelligence', 'deep learning', 'AI-ready', 'AI/ML'):
        assert term in pattern
    assert 'research|resource' not in pattern
    digest = hashlib.sha256((ROOT / command[-1]).read_bytes()).hexdigest()
    assert digest in record and digest in notes and pattern in notes
    # Use this test's interpreter; no ripgrep installation or skip required.
    result = subprocess.run([sys.executable, *command[1:]], cwd=ROOT,
                            text=True, capture_output=True, timeout=60)
    assert result.returncode == 0
    assert record.split('# Matching lines: ', 1)[1].split('\n', 1)[1] == result.stdout
    assert '1440:' in result.stdout and '1440' in notes and 'downstream use' in notes


@pytest.mark.parametrize('state', ['needs_owner', 'absence_supported'])
def test_explicit_states_require_notes_and_verbatim_quotes(state):
    prefix = f'[{state}: true] '
    quote = '[chunks: c001] "exact source"'
    chunks = {'c001': 'exact source'}
    for bad in (prefix + quote, prefix + '[search_notes] "short" ' + quote,
                prefix + '[search_notes] "' + 'x' * 50 + '" [chunks: c001] "invented"'):
        with pytest.raises(AssertionError):
            validate_quotes(bad, chunks)
    assert validate_quotes(prefix + '[search_notes] "' + 'x' * 50 + '" ' + quote, chunks)[0] == state
