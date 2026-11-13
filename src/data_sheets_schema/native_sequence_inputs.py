"""Invocation-only parent/child byte pins; never registered authority.

No document version changes. Each consumer checks its actual captured bytes;
a preflight read alone does not bind later independent recaptures.
"""
import re
from . import native_subscription_guard as wire

BASE=('registration','review','launch_word','account_choice','ci')


def capture_expected(args):
    encoded=getattr(args,'sequence_inputs',None)
    if encoded is None:
        return None
    value=wire.strict_json(encoded.encode())
    names=set(BASE)
    if args.command=='capture-subscription-event': names.add('sequence_start')
    elif args.command=='prepare-subscription-guard-v2': names.add('capture')
    elif args.command=='launch': names.add('subscription_guard')
    if type(value) is not dict or set(value)!=names:
        raise ValueError('sequence input pins must contain the exact command roster')
    for name in (*BASE, *sorted(names-set(BASE))):
        pin=value[name]
        if (type(pin) is not dict or set(pin)!={'path','sha256'}
                or type(pin['path']) is not str or type(pin['sha256']) is not str
                or re.fullmatch('[0-9a-f]{64}',pin['sha256']) is None):
            raise ValueError('sequence input pin is malformed')
        selected=getattr(args,name,None)
        if selected is not None and selected!=pin['path']:
            raise ValueError('sequence input path differs from the command argument')
        raw=wire.read_regular(pin['path'],limit=16*1024 if name=='account_choice' else 32*1024*1024)
        check_raw(value,name,raw)
    return value


def check_raw(pins,name,raw):
    if pins is not None and wire.sha(raw)!=pins[name]['sha256']:
        raise ValueError('sequence input bytes differ from parent digest: '+name)
    return raw


def check_authority(expected,raw):
    """Bind the engine's actual review/CI/word capture before any reservation."""
    if expected is None:
        return
    if type(expected) is not dict or set(expected)!={'review','ci','launch_word'}:
        raise ValueError('sequence authority digest roster differs')
    if any(wire.sha(raw[name])!=digest for name,digest in expected.items()):
        raise ValueError('captured launch authority differs from parent digests')
