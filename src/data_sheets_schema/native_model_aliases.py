"""Closed native U4b model labels, 2026-11-08 (addendum 2).

Pure saved-value checks only: no inference from a model prefix, no provider
discovery and no historical runtime-schema change. These labels describe the
CLI request/init/accounting identity and the API request/assistant identity.
"""
from . import native_shared_contract as c

KIND = 'd4d_native_u4b_runtime_basis'
PROVISIONAL_KIND = 'd4d_native_u4b_provisional_runtime_basis'
REQUESTED = 'claude-opus-5[1m]'
RETURNED = 'claude-opus-5'


def model_aliases(runtime):
    """Read the declared closed pair; historical other models stay identical."""
    if type(runtime) is not dict or type(runtime.get('model')) is not str:
        raise ValueError('native model identity must be explicit text')
    model = runtime['model']
    raw = runtime.get('limits_basis')
    basis = None
    if type(raw) is str and raw.lstrip().startswith('{'):
        try:
            basis = c.strict_json(raw.encode('utf-8'), 'native model alias basis', 4096)
        except ValueError:
            if model == REQUESTED:
                raise
    current = model == REQUESTED or type(basis) is dict and basis.get('kind') in (KIND, PROVISIONAL_KIND)
    if not current:
        return {'requested': model, 'returned': model}
    if (type(basis) is not dict or type(basis.get('version')) is not int
            or (basis.get('kind'), basis['version']) not in ((KIND, 2), (KIND, 3), (PROVISIONAL_KIND, 1))
            or model != REQUESTED):
        raise ValueError('native 1M model requires an explicit versioned U4b alias declaration')
    aliases = basis.get('model_aliases')
    if (type(aliases) is not dict or set(aliases) != {'requested', 'returned'}
            or aliases != {'requested': REQUESTED, 'returned': RETURNED}):
        raise ValueError('native 1M model alias pair differs from its closed declaration')
    if runtime.get('auxiliary_models') != []:
        raise ValueError('native 1M model alias pair does not permit auxiliary models')
    return dict(aliases)


def require_frame_models(event, aliases):
    """Check present frame/message labels against an already checked pair.

    Current-profile assistant frames must expose a model label; a missing
    observation cannot stand in for the returned label. Other-model historical
    frames retain their previous optional-label behavior.
    """
    assistant = event.get('type') == 'assistant'
    wanted = aliases['returned'] if assistant else aliases['requested']
    message = event.get('message')
    containers = (event, message) if type(message) is dict else (event,)
    observed = False
    for value in containers:
        if 'model' in value:
            observed = True
            if value['model'] != wanted:
                raise ValueError('native frame contradicts its declared model alias')
    if assistant and aliases['requested'] != aliases['returned'] and not observed:
        raise ValueError('native assistant frame lacks its declared returned model observation')


def require_model_usage(terminal, aliases):
    """Current-profile usage names the requested alias only, never the return label."""
    if aliases['requested'] == aliases['returned']:
        return
    usage = terminal.get('modelUsage')
    if (type(usage) is not dict or set(usage) != {aliases['requested']}
            or type(usage[aliases['requested']]) is not dict):
        raise ValueError('native terminal modelUsage differs from the declared requested alias')
