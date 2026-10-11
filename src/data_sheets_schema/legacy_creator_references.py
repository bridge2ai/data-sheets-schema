"""Finite same-crate author projection, separate from scientific mapping claims.

The source author URI is reused as Creator.id, matching the existing converter
convention. This is an explicit representation of the asserted author, not a
claim that Person and Creator have identical semantics or that the author is a
principal investigator. Complete source objects remain in separate evidence.
"""
from copy import deepcopy
from hashlib import sha256
import json

from data_sheets_schema.legacy_creators import REFERENCE_MARKER

FORMAT = 'legacy_creator_reference_construction_v1'
LIMIT = ('Source author URI is reused as Creator.id; no PI/CRediT roles or '
         'organization IDs are inferred. Projection is not lossless, source '
         'coverage, unique-person counting or validation success.')


def _digest(value):
    """Hash ASCII-escaped parsed JSON, including escaped lone surrogates.

    This retains parsed values, not the spelling of the original file bytes.
    """
    return sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                             separators=(',', ':')).encode('utf-8')).hexdigest()


def _project(unit, graph):
    evidence = {'original_unit': deepcopy(unit), 'status': 'unresolved',
                'reason': None, 'matches': [], 'mapped_fields': {},
                'excluded_fields': []}
    if isinstance(unit, str):
        evidence.update(status='literal', reason='whole_literal_description',
                        mapped_fields={'description': 'author'})
        return {'description': unit}, evidence
    if type(unit) is not dict or set(unit) != {'@id'} or type(unit['@id']) is not str or not unit['@id']:
        evidence['reason'] = 'unsupported_author_unit'
        return deepcopy(unit), evidence

    # Count before checking type: duplicate IDs never acquire a preferred winner.
    entities = ([('/@graph', graph)] if type(graph) is dict else
                [('/@graph/' + str(i), member) for i, member in enumerate(graph)])
    members = [(pointer, member) for pointer, member in entities
               if type(member) is dict and type(member.get('@id')) is str
               and member['@id'] == unit['@id']]
    evidence['matches'] = [{'pointer': pointer, 'raw_member': deepcopy(member),
                            'parsed_json_sha256': _digest(member)}
                           for pointer, member in members]
    if len(members) != 1:
        evidence['reason'] = 'missing_reference' if not members else 'duplicate_reference_id'
        return deepcopy(unit), evidence
    member = members[0][1]
    reason = None
    if member.get('@type') != 'Person' or type(member.get('@type')) is not str:
        reason = 'unsupported_reference_type'
    elif not {'@id', '@type', 'name'} <= set(member) or set(member) - {'@id', '@type', 'name', 'identifier', 'affiliation'}:
        reason = 'unsupported_person_fields'
    elif type(member['name']) is not str or not member['name']:
        reason = 'invalid_person_name'
    elif 'identifier' in member and (type(member['identifier']) is not str or member['identifier'] != unit['@id']):
        reason = 'conflicting_person_identifier'
    elif 'affiliation' in member:
        org = member['affiliation']
        if (type(org) is not dict or set(org) != {'@type', 'name'}
                or type(org['@type']) is not str or org['@type'] != 'Organization'
                or type(org['name']) is not str or not org['name']):
            reason = 'unsupported_affiliation'
    if reason:
        evidence['reason'] = reason
        return deepcopy(unit), evidence

    result = {'id': unit['@id'], 'name': member['name']}
    mapped = {'id': 'author/@id', 'name': 'member/name'}
    excluded = ['member/@type']
    if 'identifier' in member:
        excluded.append('member/identifier')
    if 'affiliation' in member:
        result['affiliations'] = [{'name': member['affiliation']['name']}]
        mapped['affiliations/0/name'] = 'member/affiliation/name'
        excluded.append('member/affiliation/@type')
    evidence.update(status='resolved', reason='unique_typed_person',
                    mapped_fields=mapped, excluded_fields=excluded)
    return result, evidence


def construct_creators(root, graph):
    """One fresh graph, preserving root units/order and every matching member."""
    value = root.get('author')
    units = [] if value is None else value if isinstance(value, list) else [value]
    result, entries = [], []
    for index, unit in enumerate(units):
        converted, evidence = _project(unit, graph)
        evidence.update(author_index=index, match_count=len(evidence['matches']),
                        output_range=[index, index + 1])
        result.append(converted)
        entries.append(evidence)
    return (None if value is None else result), {
        'root_id': deepcopy(root.get('@id')), 'author_present': 'author' in root,
        'raw_author': deepcopy(value), 'entries': entries}


def reference_evidence(presence, constructions):
    """Join fresh per-source construction to the existing raw-source roster."""
    if not constructions or all(item is None for item in constructions):
        return None
    if presence['status'] != 'measured' or len(presence['sources']) != len(constructions):
        raise ValueError('Creator reference evidence requires the exact source roster')
    sources, offset = [], 0
    for raw, construction in zip(presence['sources'], constructions):
        if construction is None:
            raise ValueError('Creator reference evidence is missing a selected source')
        row = deepcopy(construction)
        for key in ('source_index', 'processing_index', 'source_name', 'selected_primary'):
            row[key] = deepcopy(raw[key])
        end = offset + len(row['entries'])
        row['output_range'] = [offset, end]
        for entry in row['entries']:
            entry['output_range'] = [offset + entry['author_index'], offset + entry['author_index'] + 1]
        sources.append(row)
        offset = end
    return {'format': FORMAT, 'policy': REFERENCE_MARKER,
            'scope': 'selected_root_author_unique_same_crate_person',
            'limitations': LIMIT, 'sources': sources}


def reference_lines(evidence):
    if evidence is None:
        return []
    return ['', 'CREATOR REFERENCE CONSTRUCTION', '-' * 80, LIMIT,
            json.dumps(evidence, ensure_ascii=True, sort_keys=True), '']
