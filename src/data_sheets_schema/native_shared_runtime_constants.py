"""Neutral render constants extracted from the unchanged v1 route, 2026-11-07.

Only wire vocabulary lives here. Runtime validation and execution authority
remain at their existing boundaries; importing these values admits no run.
"""

ROUTE = 'claude_code_direct_stream_json_v1'
RUNTIME_KEYS = {'route', 'executable', 'model', 'auxiliary_models', 'effort', 'limits',
    'limits_basis', 'provider', 'auth', 'environment', 'deadline_seconds', 'budget_guard_usd', 'keep_awake'}
