"""PR #5532/#5517, 2026-11-08: reuse independent byte-containment review.

Input: committed HEAD, original reviewer script (with embedded in-repo fallback
when invoked outside d4d-executions, #5613). Output: scratch-5517 JSON audit.
Only adaptation: recognize the new decision-note tag as a note token. All original
bundle/chunk hashes, quotation bytes, values and D52 comparisons remain unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import types

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ.get('D4D_5517_SCRATCH', ROOT.parent / 'scratch-5517'))
EXTERNAL_REVIEWER = ROOT.parent / 'plans/reviews/pr5532_review_scripts/verify_context_quotations.py'
PINNED_REVIEWER_SHA256 = '08114ccd9e6499fa1efd8c9e74992e55e231e1c31687751df2e0c5c163248166'
DEFAULT_HEAD = '616222dff8c3043c7b915f7edcfb2e26f409c48a'
DEFAULT_BASE = 'cf50d9a1c059f3b5030103378ccef33619475dde'
PREDICATES = (
    'human_subjects', 'regulated_access', 'shared_dataset', 'data_collection',
    'data_processing', 'processing_software', 'ml_training_dataset',
)


def _embedded_reviewer() -> types.SimpleNamespace:
    ns = types.SimpleNamespace()
    ns.DEFAULT_HEAD = DEFAULT_HEAD
    ns.DEFAULT_BASE = DEFAULT_BASE
    ns.PREDICATES = PREDICATES

    def git(repo, *args, binary=False):
        out = subprocess.run(['git', '-C', repo, *args], check=True, capture_output=True)
        return out.stdout if binary else out.stdout.decode('utf-8')

    def show(repo, commit, rel_path):
        return git(repo, 'show', f'{commit}:{rel_path}', binary=True)

    def exists(repo, commit, rel_path):
        return subprocess.run(
            ['git', '-C', repo, 'cat-file', '-e', f'{commit}:{rel_path}'],
            capture_output=True,
        ).returncode == 0

    def raw_tokenize(evidence):
        tokens, i, n = [], 0, len(evidence)
        decoder = json.JSONDecoder()
        while i < n:
            ch = evidence[i]
            if ch.isspace():
                i += 1
            elif ch == '[':
                j = evidence.index(']', i)
                tokens.append(('tag', evidence[i + 1:j]))
                i = j + 1
            elif ch == '"':
                value, end = decoder.raw_decode(evidence, i)
                tokens.append(('string', value))
                i = end
            else:
                j = i
                while j < n and evidence[j] not in '["':
                    j += 1
                tokens.append(('prose', evidence[i:j]))
                i = j
        return tokens

    ns.tokenize = raw_tokenize

    def structure(evidence):
        tokens = ns.tokenize(evidence)
        quotes, notes, tags, problems = [], [], [], []
        k = 0
        while k < len(tokens):
            kind, payload = tokens[k]
            if kind == 'tag':
                follower = tokens[k + 1] if k + 1 < len(tokens) else None
                if payload.startswith('chunks:'):
                    ids = [x.strip() for x in payload[len('chunks:'):].split(',')]
                    if follower is None or follower[0] != 'string':
                        problems.append(f'[{payload}] not followed by a quotation')
                        k += 1
                        continue
                    quotes.append({'ids': ids, 'quote': follower[1]})
                    k += 2
                    continue
                if payload == 'search_notes':
                    if follower is None or follower[0] != 'string':
                        problems.append('[search_notes] not followed by a string')
                        k += 1
                        continue
                    notes.append(follower[1])
                    k += 2
                    continue
                tags.append(payload)
                k += 1
                continue
            if kind == 'string':
                problems.append(f'orphan string not preceded by a chunk citation: {payload[:80]!r}')
            else:
                problems.append(f'untagged prose: {payload[:80]!r}')
            k += 1
        return quotes, notes, tags, problems

    def comment_chunks(raw_text):
        result, current = {}, None
        for line in raw_text.splitlines():
            top = re.match(r'^([a-z_]+):\s*$', line)
            if top:
                current = top[1]
                continue
            m = re.match(r'^\s+# chunks: \[([^\]]*)\]\s*$', line)
            if m and current:
                result[current] = [x.strip() for x in m[1].split(',') if x.strip()]
        return result

    def load_bundle(repo, commit, context_raw):
        header = re.search(
            rb'^# Bundle chunks: (\S+) \(rule\.version: (\d+), (\d+) chunks\)',
            context_raw,
            re.M,
        )
        if not header:
            raise SystemExit('context file lacks a parseable "# Bundle chunks:" header')
        manifest_path = header[1].decode()
        manifest = yaml.safe_load(show(repo, commit, manifest_path))
        info = {
            'manifest': manifest_path,
            'header_rule_version': int(header[2]),
            'header_chunk_count': int(header[3]),
            'manifest_rule_version': manifest['rule']['version'],
            'manifest_chunk_count': manifest['chunk_count'],
            'problems': [],
        }
        sibling = str(PurePosixPath(manifest_path).parent / manifest['bundle'])
        concatenated = f"data/preprocessed/concatenated/{manifest['bundle']}"
        bundle_path = sibling if exists(repo, commit, sibling) else concatenated
        info['bundle'] = bundle_path
        raw = show(repo, commit, bundle_path)
        for key, value, expected in (
            ('bundle_sha256', hashlib.sha256(raw).hexdigest(), manifest['bundle_sha256']),
            ('bundle_md5', hashlib.md5(raw).hexdigest(), manifest['bundle_md5']),
            ('bundle_bytes', len(raw), manifest['bundle_bytes']),
        ):
            info[key] = value
            if value != expected:
                info['problems'].append(f'{key} {value} != manifest {expected}')
        if info['header_rule_version'] != info['manifest_rule_version']:
            info['problems'].append('header rule.version differs from manifest')
        if (
            info['header_chunk_count'] != info['manifest_chunk_count']
            or len(manifest['chunks']) != manifest['chunk_count']
        ):
            info['problems'].append('chunk count mismatch between header, manifest and chunk list')
        lines = raw.split(b'\n')
        lines = [part + b'\n' for part in lines[:-1]] + ([lines[-1]] if lines[-1] else [])
        if len(lines) != manifest['bundle_lines']:
            info['problems'].append(f'LF line count {len(lines)} != manifest {manifest["bundle_lines"]}')
        chunks, expected_next = {}, 1
        for chunk in manifest['chunks']:
            first, last = chunk['lines']
            if first != expected_next:
                info['problems'].append(f'{chunk["id"]} does not start where the previous chunk ended')
            expected_next = last + 1
            body = b''.join(lines[first - 1:last])
            if hashlib.sha256(body).hexdigest() != chunk['sha256'] or len(body) != chunk['bytes']:
                info['problems'].append(f'{chunk["id"]} sha256/bytes mismatch')
            chunks[chunk['id']] = {
                'first': first, 'last': last, 'bytes': body, 'source': chunk.get('source'),
            }
        if expected_next - 1 != len(lines):
            info['problems'].append('chunks do not cover the whole bundle')
        return raw, chunks, info

    def line_of(raw, offset):
        return raw[:offset].count(b'\n') + 1

    def audit(repo, head, base):
        changed = [
            p for p in git(repo, 'diff', '--name-only', base, head, '--', 'data/context').split()
            if re.fullmatch(r'data/context/[a-z0-9_]+_context\.yaml', p)
        ]
        report = {'head': head, 'base': base, 'changed_context_files': changed, 'files': {}}
        totals = {
            'files': 0, 'predicates': 0, 'quotations': 0, 'citations': 0,
            'contained': 0, 'not_contained': 0, 'notes_strings': 0,
            'notes_inner_quotes': 0, 'notes_inner_quotes_found': 0, 'structural_problems': 0,
        }
        for rel_path in changed:
            totals['files'] += 1
            raw_ctx = show(repo, head, rel_path)
            base_raw = show(repo, base, rel_path)
            ctx, base_ctx = yaml.safe_load(raw_ctx), yaml.safe_load(base_raw)
            bundle, chunks, info = load_bundle(repo, head, raw_ctx)
            comments = comment_chunks(raw_ctx.decode())
            file_report = {'bundle': info, 'predicates': {}}
            totals['structural_problems'] += len(info['problems'])
            if set(ctx) != set(PREDICATES):
                info['problems'].append(f'predicate set {sorted(ctx)}')
            for pred in PREDICATES:
                totals['predicates'] += 1
                entry, base_entry = ctx[pred], base_ctx[pred]
                quotes, notes, tags, problems = structure(entry['evidence'])
                base_tags = [
                    t for t in ns.tokenize(base_entry['evidence'])
                    if t[0] == 'tag' and t[1].startswith('curator_assertion')
                ]
                pred_report = {
                    'value': entry['value'], 'base_value': base_entry['value'],
                    'tags': tags, 'problems': problems, 'quotations': [], 'notes': [],
                }
                if entry['value'] is not base_entry['value']:
                    problems.append('VALUE CHANGED versus base')
                if set(entry) != set(base_entry):
                    problems.append(f'keys changed: {sorted(entry)} vs {sorted(base_entry)}')
                curator_now = [t for t in tags if t.startswith('curator_assertion')]
                if [t[1] for t in base_tags] != curator_now:
                    problems.append(f'curator tag changed: {[t[1] for t in base_tags]} -> {curator_now}')
                if not quotes:
                    problems.append('no cited quotation')
                cited_ids = []
                for q in quotes:
                    totals['quotations'] += 1
                    qb = q['quote'].encode('utf-8')
                    q_report = {
                        'ids': q['ids'], 'quote': q['quote'], 'chars': len(q['quote']),
                        'bundle_occurrences': bundle.count(qb), 'per_chunk': {},
                    }
                    if len(q['ids']) != len(set(q['ids'])):
                        problems.append(f'duplicate id in one citation {q["ids"]}')
                    for cid in q['ids']:
                        if cid not in cited_ids:
                            cited_ids.append(cid)
                        totals['citations'] += 1
                        chunk = chunks.get(cid)
                        if chunk is None:
                            problems.append(f'unknown chunk {cid}')
                            totals['not_contained'] += 1
                            q_report['per_chunk'][cid] = {'contained': False, 'reason': 'unknown chunk'}
                            continue
                        offset = chunk['bytes'].find(qb)
                        if offset < 0:
                            totals['not_contained'] += 1
                            other = [k for k, c in chunks.items() if qb in c['bytes']]
                            q_report['per_chunk'][cid] = {'contained': False, 'found_in_other_chunks': other}
                            problems.append(f'quotation NOT verbatim in cited {cid}: {q["quote"][:60]!r}')
                        else:
                            totals['contained'] += 1
                            start_line = chunk['first'] + chunk['bytes'][:offset].count(b'\n')
                            end_line = start_line + qb.count(b'\n')
                            q_report['per_chunk'][cid] = {
                                'contained': True,
                                'byte_offset_in_chunk': offset,
                                'bundle_lines': [start_line, end_line],
                                'occurrences_in_chunk': chunk['bytes'].count(qb),
                                'chunk_source': chunk['source'],
                            }
                    pred_report['quotations'].append(q_report)
                comment = comments.get(pred)
                pred_report['comment_chunks'] = comment
                if comment is None or sorted(comment) != sorted(cited_ids):
                    problems.append(f'# chunks comment {comment} != cited ids {cited_ids}')
                for note in notes:
                    totals['notes_strings'] += 1
                    n_report = {'text': note, 'inner_quotes': []}
                    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', note):
                        inner = m[1]
                        try:
                            decoded = json.loads('"' + inner + '"')
                        except json.JSONDecodeError:
                            decoded = inner
                        totals['notes_inner_quotes'] += 1
                        db = decoded.encode('utf-8')
                        positions = [mm.start() for mm in re.finditer(re.escape(db), bundle)]
                        found = bool(positions)
                        totals['notes_inner_quotes_found'] += found
                        n_report['inner_quotes'].append({
                            'quote': decoded,
                            'found_in_bundle': found,
                            'bundle_lines': [line_of(bundle, p) for p in positions][:5],
                        })
                    pred_report['notes'].append(n_report)
                totals['structural_problems'] += sum(1 for p in problems if 'NOT verbatim' not in p)
                file_report['predicates'][pred] = pred_report
            report['files'][rel_path] = file_report
        report['totals'] = totals
        return report

    def self_test():
        chunk = 'Raw audio was preprocessed by converting to monaural.\nNext line.'.encode()
        good = '[chunks: c001] "Raw audio was preprocessed by converting to monaural.\\nNext"'
        quotes, _, _, problems = structure(good)
        assert not problems and quotes[0]['quote'].encode() in chunk
        for bad in (
            'Raw audio was preprocessed by converting to Monaural.',
            'Raw audio was preprocessed  by converting to monaural.',
            'Raw audio was preprocessed by converting to monaural. Next',
        ):
            assert bad.encode() not in chunk
        for malformed in (
            'prose before [chunks: c001] "x"',
            '[chunks: c001] "x" trailing prose',
            '"orphan string"',
            '[chunks: c001] [search_notes] "x"',
        ):
            assert structure(malformed)[3], malformed
        print('self-test: 3 mutated quotations rejected, 4 malformed evidence strings flagged')

    ns.structure = structure
    ns.audit = audit
    ns.self_test = self_test
    return ns


def load_reviewer(external_path: Path = EXTERNAL_REVIEWER):
    if external_path.exists():
        spec = importlib.util.spec_from_file_location('independent_quotation_review', external_path)
        review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(review)
        sha256 = hashlib.sha256(external_path.read_bytes()).hexdigest()
    else:
        review = _embedded_reviewer()
        sha256 = PINNED_REVIEWER_SHA256
    original = review.tokenize

    def tokenize(evidence):
        return [
            (kind, 'search_notes' if kind == 'tag' and payload == 'context_note: D120' else payload)
            for kind, payload in original(evidence)
        ]

    review.tokenize = tokenize
    return review, sha256


def main():
    assert not (ROOT.parent / 'plans/native_quiet_window.lock').exists()
    review, reviewer_sha256 = load_reviewer(EXTERNAL_REVIEWER)
    review.self_test()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report = review.audit(str(ROOT), head, review.DEFAULT_BASE)
    report['adapter'] = 'Only context_note: D120 mapped to note token; strict allow-list checked by pytest.'
    report['reviewer_script_sha256'] = reviewer_sha256
    OUT.mkdir(parents=True, exist_ok=True)
    output = OUT / 'r6-verbatim-audit.json'
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    assert json.loads(output.read_text()) == report
    print(json.dumps(report['totals'], indent=2))
    print('reviewer_script_sha256:', report['reviewer_script_sha256'])
    return int(bool(report['totals']['not_contained'] or report['totals']['structural_problems']))


if __name__ == '__main__':
    sys.exit(main())
