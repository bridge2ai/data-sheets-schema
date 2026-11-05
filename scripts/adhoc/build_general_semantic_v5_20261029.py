#!/usr/bin/env python3
# Purpose: derive new neutral semantic instruments without rewriting predecessors.
# Inputs: released rubric10 v3 / rubric20 v4; outputs: v5 definition/rubric/schema.
# Generality F8, 2026-10-29. Run one family and inspect it before the second.
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def generalize(text):
    lines = []
    for line in text.splitlines():
        if 'DOI Format:' in line or 'DOI must match' in line:
            line = ('   - **DOI syntax:** Accept a DOI with `10.` followed by a numeric registrant code and a nonempty suffix separated by `/`; '
                    'do not restrict credit to familiar registrars or repositories. Syntax alone does not prove registration or relevance.')
        elif 'Prefix plausibility:' in line or ('Example:' in line and '10.13026' in line):
            line = ('     - Assess identifier relevance against the supplied record and evidence; '
                    'an unfamiliar prefix is not an error. Do not claim live resolution without supplied evidence.')
        elif 'Score 1 ONLY if format valid AND prefix is plausible' in line:
            line = '     - Score 1 when the identifier is well formed and identifies the documented resource; registrar familiarity is not a scoring criterion.'
        elif 'MGH' in line:
            label = '**Good:**' if '**Good:**' in line else '**Score 5 Example:**'
            line = (f'- {label} "Synthetic example: measurements were collected hourly at stations A, B and C '
                    'from January through June 2025 using calibrated sensors; all scheduled readings were retained, '
                    'with outages logged by station and date. The locations, sampling interval, equipment, '
                    'inclusion rule and missing-observation procedure are specified."')
        elif '**Score 3 Example:**' in line:
            line = '- **Score 3 Example:** "Synthetic example: sensors recorded hourly measurements at three stations; calibration and outage handling are unspecified."'
        elif ('DOI prefix not matching known registrars' in line
              or 'DOI format valid but registrar prefix unusual/unverified' in line):
            line = '    - description: "Identifier contradicts the resource identity documented in the supplied evidence"'
        elif 'Look for: PhysioNet' in line:
            line = '   - Look for: a named repository, publisher, archive, or other documented hosting service'
        elif 'Grant Number Format:' in line:
            line = '   - **Award identifier:** Judge identifiers against the declared funder and supplied evidence; do not impose one funder’s syntax on other funders.'
        elif '     - NIH:' in line or '     - NSF:' in line:
            continue
        elif ('Grant number format non-standard for NIH/NSF' in line
              or 'Grant number format non-standard for funding agency (NIH/NSF)' in line):
            line = '    - description: "Award identifier conflicts with the declared funder evidence"'
        elif line.startswith('# AI/ML Readiness (Bridge2AI):'):
            line = '# AI/ML Readiness: assess the criteria declared by this instrument.'
        elif line.startswith('#   - Reference: Bridge2AI') or line.startswith('#   - Tool: Bridge2AI'):
            continue
        line = line.replace('PhysioNet, Dataverse, Zenodo, institutional repositories',
                            'a disciplinary, general-purpose, or institutional repository')
        lines.append(line)
    result = '\n'.join(lines) + '\n'
    result = result.replace('PhysioNet,\n        Dataverse, Zenodo, institutional repositories',
                            'a disciplinary, general-purpose, or institutional repository')
    return result


def build(family, refresh=False):
    version = 3 if family == 'rubric10' else 4
    old_agent = f'd4d-{family}-semantic' + ('-v4' if version == 4 else '')
    new_agent = f'd4d-{family}-semantic-v5'
    old_rubric = f'data/rubric/{family}' + ('_semantic_v4' if version == 4 else '') + '.txt'
    new_rubric = f'data/rubric/{family}_semantic_v5.txt'
    old_schema = f'src/download/prompts/{family}_semantic' + ('_v4' if version == 4 else '') + '_schema.json'
    new_schema = f'src/download/prompts/{family}_semantic_v5_schema.json'
    text = generalize((ROOT / f'.claude/agents/{old_agent}.md').read_text())
    text = text.replace(old_agent, new_agent).replace(old_rubric, new_rubric).replace(old_schema, new_schema)
    text = text.replace(f'General context instrument v{version}', 'General context instrument v5')
    text = text.replace(f'Emit version "{version}.0"', 'Emit version "5.0"')
    text = text.replace(f'"version": "{version}.0"', '"version": "5.0"')
    text = text.replace(f'--semantic-version {version}.0', '--semantic-version 5.0')
    text = text.replace(f'(version {version})', '(version 5)')
    text = text.replace(f'new version {version} outputs', 'new version 5 outputs')
    text = text.replace('## General context instrument v5\n',
        '## General context instrument v5\n\n'
        'Semantic 5.0 generalizes identifier criteria, collection examples and repository anchors. '
        'Judge documentation against its own declared scope and supplied evidence; unfamiliar projects, '
        'registrars and repositories do not reduce a score. Historical instruments and scores remain unchanged. '
        'This version retains the released v3 structured evidence-name authority and its limitations.\n')
    if version == 4:
        start = text.index('This is an explicitly selected semantic 4.0 instrument.')
        end = text.index('Use arbitrary nonempty dataset', start)
        text = text[:start] + ('The rubric20 fixed maximum remains 88, including v4’s representation-neutral Q19. '
            'This instrument has offline contract tests; no new scientific scoring or calibration is claimed.\n\n') + text[end:]
    else:
        text = text.replace('Read the current source rubric', f'Read {new_rubric}')
        # The original strict validation example did not select its version.
        text = re.sub(r'(--rubric rubric10-semantic)(?! --semantic-version)', r'\1 --semantic-version 5.0', text)
    rubric = generalize((ROOT / old_rubric).read_text())
    rubric = '# Semantic instrument 5.0 (F8), 2026-10-29; predecessor retained unchanged.\n' + rubric
    rubric = rubric.replace('Semantic 4.0', 'Semantic 5.0')
    schema = json.loads((ROOT / old_schema).read_text())
    schema['$id'] = schema['$id'].replace('.schema.json', '-v5.schema.json').replace('-v4-v5', '-v5')
    schema['title'] = f'{family}-semantic 5.0 Evaluation Schema'
    schema['description'] = 'Neutral semantic instrument 5.0; released structured evidence contract retained.'
    schema['properties']['version'] = {'type': 'string', 'const': '5.0'}
    outputs = {f'.claude/agents/{new_agent}.md': text, new_rubric: rubric,
               new_schema: json.dumps(schema, indent=2) + '\n'}
    for path in outputs:
        assert refresh or not (ROOT / path).exists(), path
    for path, content in outputs.items():
        (ROOT / path).write_text(content)
        assert (ROOT / path).read_text() == content and len(content) > 1000
    combined = text + rubric
    assert not re.search(r'Bridge2AI|FAIRhub|PhysioNet|10\.13026|10\.18130|OT2OD032742|MGH|UT Health|prefix is plausible|prefix unusual|NIH/NSF', combined)
    print('\n'.join(outputs))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('family', choices=['rubric10', 'rubric20'])
    parser.add_argument('--refresh', action='store_true', help='Regenerate only this unpublished v5 family')
    args = parser.parse_args()
    build(args.family, args.refresh)
