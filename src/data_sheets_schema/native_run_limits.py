"""D143 exact declared non-synthetic run limits; never inferred from a project.

The canary is a shakedown. Production selects its own registered pair before
the reference pilot. Validation does not add fields or rewrite declarations.
"""
CANARY = ('90', 21600)
PRODUCTION = ('400', 43200)
REGISTERED_PAIRS = (CANARY, PRODUCTION)


def require_registered_pair(runtime):
    if type(runtime) is not dict:
        raise ValueError('run limits require an explicit runtime')
    pair = (runtime.get('budget_guard_usd'), runtime.get('deadline_seconds'))
    if (type(pair[0]) is not str or type(pair[1]) is not int
            or pair not in REGISTERED_PAIRS):
        raise ValueError('U4b requires registered budget/deadline as one complete pair: '
                         + ', '.join(repr(p) for p in REGISTERED_PAIRS))
    return pair
