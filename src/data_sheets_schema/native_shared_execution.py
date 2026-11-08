"""Pure implementation census for D's execution consumer.

Public launch/readback moved to native_shared_execution_orchestration. No
backward import wrapper is provided: that would reintroduce verifier authority
into A3's consumer graph. This census grants no dispatch capability.
"""
from . import native_shared_contract as c
from .native_execution_engine import GATES, UNASSESSED

KIND = c.KINDS['attempt']
VERSION = 1


def require_gate_implementations():
    from .native_gate_engine import check
    from .native_shared_schema_gates import check_schemas, check_pair
    from .native_shared_receipts import schema_snapshot, _catalog_context
    from .native_subscription_guard import load_guard, validate_saved_observations
    if not all(callable(item) for item in (check, check_schemas, check_pair,
            schema_snapshot, _catalog_context, load_guard, validate_saved_observations)):
        raise ValueError('native shared execution gate implementation is incomplete')
