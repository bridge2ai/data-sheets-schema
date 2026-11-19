"""Closed native U4b model labels, with explicit CLI reporting versions.

Pure saved-value checks only: no inference from a model prefix, no provider
discovery and no historical runtime-schema change. These labels describe the
CLI invocation, reported init/accounting and API request/assistant identities.
Final basis 4 and provisional basis 2 declare the 2.1.325 reporting shape;
older declarations retain their exact labels without inference from a binary.
"""
from . import native_shared_contract as c

KIND = 'd4d_native_u4b_runtime_basis'
PROVISIONAL_KIND = 'd4d_native_u4b_provisional_runtime_basis'
REQUESTED = 'claude-opus-5[1m]'
RETURNED = 'claude-opus-5'
REPORTED_VERSION = 4
PROVISIONAL_REPORTED_VERSION = 2
CONTEXT_WINDOW = 1_000_000


def model_aliases(runtime):
    """Read the declared closed pair; historical other models stay identical."""
    if type(runtime) is not dict or type(runtime.get('model')) is not str:
        raise ValueError('native model identity must be explicit text')
    model = runtime['model']
    from . import native_runtime_profiles as profiles
    raw = runtime.get('limits_basis')
    basis = None
    if type(raw) is str and raw.lstrip().startswith('{'):
        try:
            basis = c.strict_json(raw.encode('utf-8'), 'native model alias basis', 4096)
        except ValueError:
            # Historical aliases never interpreted opaque basis text. Retain
            # that readback behavior only when no current/profile marker exists;
            # malformed declarations cannot downgrade a software-test identity.
            reserved = (profiles.SYNTHETIC_PROFILE, profiles.SYNTHETIC_PROVIDER,
                        profiles.SYNTHETIC_REQUESTED, profiles.SYNTHETIC_RETURNED)
            markers = [model, runtime.get('provider')]
            auth = runtime.get('auth')
            if type(auth) is dict:
                markers.extend(auth.values())
            if (model == REQUESTED or any(type(item) is str and item in reserved for item in markers)
                    or any(marker in raw for marker in (KIND, PROVISIONAL_KIND, 'profile', *reserved))):
                raise
            return {'requested': model, 'returned': model}
    profile = profiles.profile_name(runtime)
    current = model == REQUESTED or type(basis) is dict and basis.get('kind') in (KIND, PROVISIONAL_KIND)
    if not current:
        return {'requested': model, 'returned': model}
    requested, returned = (profiles.SYNTHETIC_REQUESTED, profiles.SYNTHETIC_RETURNED) if (
        profile == profiles.SYNTHETIC_PROFILE) else (REQUESTED, RETURNED)
    if (type(basis) is not dict or type(basis.get('version')) is not int
            or (basis.get('kind'), basis['version']) not in (
                (KIND, 2), (KIND, 3), (PROVISIONAL_KIND, 1),
                (KIND, REPORTED_VERSION), (PROVISIONAL_KIND, PROVISIONAL_REPORTED_VERSION))
            or model != requested):
        raise ValueError('native 1M model requires an explicit versioned U4b alias declaration')
    reported = (basis['kind'], basis['version']) in (
        (KIND, REPORTED_VERSION), (PROVISIONAL_KIND, PROVISIONAL_REPORTED_VERSION))
    expected = {'requested': requested, 'returned': returned}
    if reported:
        if profile != profiles.PRODUCTION_PROFILE:
            raise ValueError('reported CLI model labels require the production profile')
        expected['reported'] = RETURNED
    aliases = basis.get('model_aliases')
    if type(aliases) is not dict or aliases != expected:
        raise ValueError('native 1M model alias pair differs from its closed declaration')
    if runtime.get('auxiliary_models') != []:
        raise ValueError('native 1M model alias pair does not permit auxiliary models')
    return dict(aliases)


def reported_model(aliases):
    """Read a checked declaration; old pairs keep the requested reporting label."""
    return aliases.get('reported', aliases['requested'])


def require_invocation_model(argv, aliases):
    """New reporting declarations still require one exact saved requested alias."""
    if 'reported' not in aliases:
        return
    if type(argv) is not list or any(type(value) is not str for value in argv):
        raise ValueError('native invocation requires explicit argv strings')
    positions = [index for index, value in enumerate(argv)
                 if value == '--model' or value.startswith('--model=')]
    if (len(positions) != 1 or argv[positions[0]] != '--model'
            or positions[0] + 1 >= len(argv) or argv[positions[0] + 1] != aliases['requested']):
        raise ValueError('native invocation differs from its declared requested model alias')


def require_frame_models(event, aliases):
    """Check present frame/message labels against an already checked pair.

    Current-profile assistant frames must expose a model label; a missing
    observation cannot stand in for the returned label. Other-model historical
    frames retain their previous optional-label behavior.
    """
    assistant = event.get('type') == 'assistant'
    wanted = aliases['returned'] if assistant else reported_model(aliases)
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
    """Check the declared accounting label and the new version's exact 1M proof."""
    if aliases['requested'] == aliases['returned']:
        return
    usage = terminal.get('modelUsage')
    model = reported_model(aliases)
    if (type(usage) is not dict or set(usage) != {model}
            or type(usage[model]) is not dict):
        raise ValueError('native terminal modelUsage differs from the declared reported alias')
    if 'reported' in aliases:
        window = usage[model].get('contextWindow')
        if type(window) is not int or window != CONTEXT_WINDOW:
            raise ValueError('native reported model requires an exact 1000000 contextWindow')
