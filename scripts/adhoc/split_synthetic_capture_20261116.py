"""Split synthetic authority issuance from capture for D156, 2026-11-16.

Input/output: tests/utils/native_synthetic_evidence.py in this checkout.
Serves the capture-order implementation; refuses an unexpected source shape.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[2] / 'tests/utils/native_synthetic_evidence.py'
text = path.read_text()
text = text.replace('def authority_for(registration_raw, ci_path, directory):',
    'def authority_for(registration_raw, ci_path, directory, *, defer_capture=False):', 1)
start = text.index('    _, _, _, binding = capture._authority(')
end = text.index('    return {\'review_path\': review_path', start)
body = text[start:end]
paths_start = body.index('    review_path, word_path, guard_path = ')
paths_end = body.index('    with capture.current_guard_preparation', paths_start)
paths = body[paths_start:paths_end]
body = body[:paths_start] + body[paths_end:]
body = body.replace('    for path, raw in ((review_path, review_raw), (word_path, word_raw)):\n        path.write_bytes(raw)\n', '')
body = body.replace('    _, _, _, binding = capture._authority(registration_raw, review_raw, word_raw, capture_root)',
    '    if identity is None:\n        current = capture._authority(registration_raw, review_raw, word_raw, capture_root)\n'
    '    else:\n        current = capture._current_authority(registration_raw, review_raw, word_raw, prepared_identity=identity)\n'
    '    _, _, _, binding = current')
body = body.replace('review_bundle_raw=review_raw, launch_word_raw=word_raw) as guard_raw:',
    'review_bundle_raw=review_raw, launch_word_raw=word_raw, prepared_identity=identity) as guard_raw:')
replacement = paths + '''    for path, raw in ((review_path, review_raw), (word_path, word_raw)):
        path.write_bytes(raw)
    def mint(identity):
        return _mint_capture(registration_raw, value, review_raw, word_raw,
            terms, capture_root, directory, guard_path, identity)
    if defer_capture:
        return {'review_path': review_path, 'ci_path': ci_path,
            'launch_word_path': word_path, 'prepare_capture': mint}
    minted = mint(None)
    return {'review_path': review_path, 'ci_path': ci_path, 'launch_word_path': word_path,
        'subscription_guard_path': guard_path, 'subscription_guard_sha256': minted['guard_sha256']}


def _mint_capture(registration_raw, value, review_raw, word_raw, terms,
                  capture_root, directory, guard_path, identity):
    from data_sheets_schema import native_subscription_capture as capture
    runtime = value['runtime']
''' + body + "    return {'guard_path': str(guard_path), 'guard_sha256': c.sha(guard_raw)}\n"
text = text[:start] + replacement
if chr(64) in text:
    raise ValueError('prohibited character in generated source')
path.write_text(text)
