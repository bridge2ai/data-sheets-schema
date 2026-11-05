"""D63, 2026-10-28: agy's ONE authorized count; never generation.

Input: the fixed SHA256-pinned worker request below. Output: request SHA256,
endpoint input-token count and canonical request bytes/token on stdout.
Uses #5157's existing admission measurement route, with SDK retries disabled.
Prepared offline; this script must not be run by the preparing Codex session.
Run from this worktree with its project Python -S -B and CBORG_API_KEY set.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
REQUEST = ROOT / 'notes/reviews/d63_count_tokens_request_2026-10-28.json'
EXPECTED_SHA256 = 'c2087a5a3ad9eddae8d42393a96d71a9d200bee749d02b76e75ee286311f70c9'


def main():
    raw = REQUEST.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit('D63 refused: request SHA256 differs from the fixed authorized file')
    if not sys.flags.no_site:
        raise SystemExit('D63 requires Python -S -B to select this worktree explicitly')
    sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
    sys.path.append(str(Path(sys.executable).parent.parent / 'lib' /
                        f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages'))
    from data_sheets_schema import api_runner as api, receipt_completion as receipts
    if api.provider_identity()['base_url'] != 'https://api.cborg.lbl.gov':
        raise SystemExit('D63 requires the A21 CBORG route: unset ANTHROPIC_API_KEY; set CBORG_API_KEY')
    payload = json.loads(raw)
    # The frozen worker has no tools. Refuse instead of silently dropping any
    # count-relevant field unsupported by this existing admission route.
    if set(payload) - {'model', 'system', 'messages', 'thinking', 'output_config', 'max_tokens', 'temperature'}:
        raise SystemExit('D63 payload has a field the admission counter does not forward')
    print(f'request_sha256={digest}', flush=True)
    client = receipts._single_attempt_client(api._client())
    try:
        count = receipts._measure_context(client, payload, {
            'context_limit_tokens': 1000000,
            'context_limit_basis': 'Route context window 1,000,000 tokens; sized for largest bundle'},
            label='D63 fixed worker request')
    finally:
        client.close()
    tokens = count['input_tokens']
    if type(tokens) is not int or tokens <= 0:
        raise SystemExit('D63 provider did not return a positive integer input-token count; do not retry')
    print(f'provider_input_tokens={tokens}')
    print(f'request_bytes={len(raw)}')
    print(f'implied_bytes_per_token={len(raw) / tokens:.8f}')


if __name__ == '__main__':
    main()
