"""Unchanged native_shared_stage advance CLI; orchestration is explicit.

Package __init__ contains the pure stage implementation and never imports this
module. The registered -m data_sheets_schema.native_shared_stage spelling stays
unchanged.
"""
from __future__ import annotations

import argparse
from . import _Replay, _check_response, _prepare_next, c, nr
from ..native_shared_capture_orchestration import capture_stage, publish_stage


def main():
    """    RunSpec boundary: validated-caller

    RunSpec precondition: CLI supplies an explicit registration path; capture_stage revalidates selected preparation and pending invocation before replay and publication.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    advance = commands.add_parser('advance')
    advance.add_argument('--registration', required=True)
    args = parser.parse_args()
    catalogs = nr._catalog_context()
    invocation = capture_stage(args.registration, _catalogs=catalogs)
    selected = (invocation.selection, invocation.execution, invocation.phase1, invocation.history)
    replay = _Replay(*selected, _catalogs=catalogs).run()
    if replay.pending is not None and replay.pending[-1] is not None:
        response, _ = replay.pending[-1]
        proposal = _check_response(*selected, replay.pending[2].raw, response.raw, catalogs)
    else:
        proposal = _prepare_next(*selected, catalogs)
    result = publish_stage(invocation, proposal, _catalogs=catalogs)
    print(c.canonical(result).decode('utf-8'))



if __name__ == '__main__':
    main()
