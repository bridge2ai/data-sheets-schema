"""Independent Wave3 A23 review probes, #5164/R8, 2026-10-27.

Inputs: committed evaluation contexts and their actual pinned source bundles.
Outputs: offline pytest evidence. Citation identity is checked separately from
manual semantic review; these probes do not constitute human scoring approval.
"""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

import pytest
import yaml

from scripts.build_api_registrations import build_draft_context
from scripts.build_draft_contexts import (
    DEFAULT_MANIFEST_PATH, KIDS_FIRST_MANIFEST_PATH,
    build_draft_scope_context, load_project_manifest_data,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ('AI_READI', 'CHORUS', 'CM4AI', 'VOICE', 'VOICE_PEDIATRIC', 'KIDS_FIRST')


@lru_cache(maxsize=None)
def source(project):
    if project == 'KIDS_FIRST':
        base = ROOT / 'notes/matched_cborg_2026-09-13/kids_first'
        bundle, manifest = base / 'KIDS_FIRST_preprocessed.txt', base / 'chunks.yaml'
    else:
        bundle = ROOT / f'data/preprocessed/concatenated/{project}_preprocessed.txt'
        manifest = ROOT / f'data/preprocessed/chunks/{project}_chunks.yaml'
    raw = bundle.read_bytes()
    chunks = yaml.safe_load(manifest.read_bytes())
    assert hashlib.sha256(raw).hexdigest() == chunks['bundle_sha256']
    lines = raw.splitlines(keepends=True)
    parts = {}
    for chunk in chunks['chunks']:
        start, end = chunk['lines']
        part = b''.join(lines[start - 1:end])
        assert len(part) == chunk['bytes']
        assert hashlib.sha256(part).hexdigest() == chunk['sha256']
        parts[chunk['id']] = part.decode('utf-8')
    return raw.decode('utf-8'), parts


def evidence(project, predicate):
    context = yaml.safe_load((ROOT / f'data/context/{project.lower()}_context.yaml').read_bytes())
    entry = context[predicate]
    match = re.search(r'\[chunks:\s*([^\]]+)\]', entry['evidence'])
    ids = [item.strip() for item in match.group(1).split(',')]
    _, parts = source(project)
    return entry['evidence'], ids, {key: parts[key] for key in ids}


@pytest.mark.parametrize('project', PROJECTS)
def test_all_pinned_bundles_chunks_and_citations_are_byte_verified(project):
    source(project)
    context = yaml.safe_load((ROOT / f'data/context/{project.lower()}_context.yaml').read_bytes())
    assert len(context) == 7
    for predicate in context:
        text, ids, parts = evidence(project, predicate)
        assert text and ids and len(parts) == len(ids)


def test_pediatric_ethics_and_assent_are_bound_to_the_cited_child_sources():
    text, ids, parts = evidence('VOICE_PEDIATRIC', 'human_subjects')
    assert {'c002', 'c003', 'c005'} <= set(ids)
    assert 'Patients/healthy volunteers at the Hospital for Sick Children' in parts['c002']
    assert 'approved by the Research Ethics Board at the Hospital for Sick Children' in parts['c003']
    assert 'assent' in parts['c005'].lower()
    assert 'Hospital for Sick Children' in text
    assert 'South Florida' not in text


def test_pediatric_free_speech_statement_keeps_the_release_qualification():
    text, ids, parts = evidence('VOICE_PEDIATRIC', 'data_processing')
    assert 'c003' in ids
    statement = 'releasing audio features for all free speech tasks that were manually checked'
    assert statement in parts['c003']
    assert 'v1.1.0' in text and 'manual checking' in text
    assert 'unconsented speakers and PII' in text
    assert 'free-speech spectrograms are stripped' not in text


def test_pediatric_processing_does_not_retain_unregistered_resampling_claims():
    text, _, parts = evidence('VOICE_PEDIATRIC', 'data_processing')
    full, _ = source('VOICE_PEDIATRIC')
    unsupported = re.compile(r'monaural|16[ ,]?kHz|16,?000|resampl', re.I)
    # Direct entire pinned file, including content gitignore would hide. The cited
    # release does describe FFT/Mel/MFCC derivation; it does not give resampling.
    assert '400-point FFT' in parts['c002']
    assert unsupported.search(full) is None
    assert unsupported.search(text) is None, 'R8-F1: pediatric resampling is not supported by the registered corpus'


def test_pediatric_recording_scope_preserves_the_documented_microphone_exception():
    text, _, parts = evidence('VOICE_PEDIATRIC', 'data_collection')
    assert 'A headset was used to record for most participants' in parts['c002']
    assert 'built-in tablet microphone' in parts['c002']
    assert 'most' in text.lower() or 'tablet microphone' in text.lower() or 'headset' not in text.lower(), (
        'R8-F1: universal headset wording loses the pediatric release exception'
    )


@lru_cache(maxsize=None)
def aireadi_directories():
    text, _ = source('AI_READI')
    # Parse the real nested FAIRhub record, not an unscoped bag of format words.
    marker = 'FILE: fairhub_api_dataset_3_2026-07-27.txt'
    start = text.index('{', text.index(marker))
    document, _ = json.JSONDecoder().raw_decode(text[start:])
    # The source API envelope groups dataset metadata under metadata.
    def find_structure(value):
        if isinstance(value, dict):
            if 'datasetStructureDescription' in value:
                return value['datasetStructureDescription']['directoryList']
            for child in value.values():
                found = find_structure(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = find_structure(child)
                if found is not None:
                    return found
        return None
    rows = find_structure(document)
    assert rows
    return {row['directoryName']: row for row in rows}


@pytest.mark.parametrize('directory,standard', [
    ('cardiac_ecg', 'WaveForm DataBase (WFDB)'),
    ('clinical_data', 'The Observational Medical Outcomes Partnership (OMOP) Common Data Model (CDM)'),
    ('retinal_flio', 'Digital Imaging and Communications in Medicine (DICOM)'),
    ('environment', 'ASCII File Format Guidelines for Earth Science Data'),
    ('wearable_activity_monitor', 'Open mHealth'),
    ('wearable_blood_glucose', 'Open mHealth'),
])
def test_aireadi_formats_are_bound_to_specific_source_directories(directory, standard):
    row = aireadi_directories()[directory]
    matching = [item for item in row['relatedStandard'] if item['standardName'] == standard]
    assert len(matching) == 1
    assert 'All the data files within this directory' in matching[0]['standardUse']


@pytest.mark.parametrize('predicate', ['data_processing', 'processing_software'])
def test_aireadi_evidence_does_not_relabel_registered_standards_as_custom_json(predicate):
    text, _, parts = evidence('AI_READI', predicate)
    # c019's actual release README recapitulates the modality-specific directory
    # standards, so correction can stay within the already cited source authority.
    readme = parts['c019']
    assert 'Earth Science Data Systems (ESDS) format' in readme
    assert 'Open mHealth' in readme
    full, _ = source('AI_READI')
    assert re.search(r'custom\s+JSON', full, re.I) is None
    assert re.search(r'custom\s+JSON', text, re.I) is None, (
        'R8-F2: environmental ASCII/ESDS and wearable Open mHealth are not custom JSON'
    )


def test_kids_first_cwl_and_named_workflows_resolve_to_their_actual_cited_chunks():
    text, ids, parts = evidence('KIDS_FIRST', 'processing_software')
    assert {'c006', 'c013'} <= set(ids)
    assert 'Common Workflow Language (CWL)' in parts['c013']
    assert 'for describing and running tools and workflows in CAVATICA' in parts['c013']
    assert 'Kids First FHIR Model' in parts['c013']
    for software in ('HaplotypeCaller', 'Joint Genotyping', 'STAR', 'RSEM', 'Arriba', 'STAR-Fusion'):
        assert software in parts['c006']
    assert 'GitHub and CAVATICA' in parts['c006']
    for unsupported in ('Six Bridges', 'GenotypeGVCFs'):
        assert unsupported not in source('KIDS_FIRST')[0]
        assert unsupported not in text


def test_kids_first_does_not_infer_bwa_algorithm_from_an_index_format():
    text, _, parts = evidence('KIDS_FIRST', 'processing_software')
    full, _ = source('KIDS_FIRST')
    assert 'bwa-indexed reference fasta' in parts['c006']
    assert re.search(r'bwa[ -]mem', full, re.I) is None
    assert re.search(r'bwa[ -]mem', text, re.I) is None, (
        'R8-F3: a bwa-indexed reference is not evidence that the BWA-MEM algorithm ran'
    )


@pytest.mark.parametrize('with_scope', [False, True])
def test_explicit_manifest_authority_survives_both_synthesizer_entrypoints(tmp_path, with_scope):
    custom = {'profile': 'neutral', 'projects': {'KIDS_FIRST': {'sources': []}},
              'source_priority': {1: ['review_primary'], 2: ['review_secondary']}}
    if with_scope:
        custom['scope'] = {'KIDS_FIRST': {'referent': 'review-selected study', 'release': 'urn:review:release'}}
    path = tmp_path / 'deliberate_manifest.yaml'
    path.write_text(yaml.safe_dump(custom))
    selected = load_project_manifest_data('KIDS_FIRST', path)
    assert selected == custom
    direct = build_draft_scope_context('KIDS_FIRST', selected)
    delegated = build_draft_context('KIDS_FIRST', path, write_to_disk=False)
    assert direct == delegated
    assert direct['source_policy']['priority'] == ['review_primary', 'review_secondary']
    assert direct['vocabulary'] == {}
    if with_scope:
        assert direct['scopes'][0]['release'] == 'urn:review:release'
        assert direct['scopes'][0]['referent'] == 'review-selected study'
    else:
        assert direct['scopes'][0]['release'] is None


@pytest.mark.parametrize('argument', [None, DEFAULT_MANIFEST_PATH])
def test_default_manifest_still_resolves_the_registered_kids_first_authority(argument):
    selected = load_project_manifest_data('KIDS_FIRST', argument)
    assert selected == yaml.safe_load(KIDS_FIRST_MANIFEST_PATH.read_bytes())
    doc = build_draft_scope_context('KIDS_FIRST', selected)
    assert doc['vocabulary'] == {}
    assert doc['scopes'][0]['release'] == 'https://kidsfirstdrc.org/'


def test_chorus_omission_identity_uses_actual_historical_bytes():
    raw = (ROOT / 'data/omission_contexts/chorus_omission_context.json').read_bytes()
    assert len(raw) == 6476
    assert hashlib.sha256(raw).hexdigest() == 'ac94a74bd0d7d6c656564d67e656c7dbcf6627dca4c147a876eded072a81a3b0'
