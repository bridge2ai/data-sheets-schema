#!/usr/bin/env python3
# Purpose: rerun the reviewer's pending-call scenario with/without registration.
# Inputs: reviewer sim_pending_full.py and external evidence directory, argv 1/2.
# Outputs: scenario ledgers and printed assertions; G1 N2, 2026-10-29.
from pathlib import Path
import runpy
import sys

from data_sheets_schema import dollar_readout as dr

scenario, output = sys.argv[1], Path(sys.argv[2])
compute = dr.compute_readout
registration = {'format': 'shared_generation_registration_v1',
                'audit_limits': {'context_limit_tokens': 1000000}}

for declared in (False, True):
    def checked(*args, **kwargs):
        summary = compute(*args, **kwargs, registration=registration if declared else None)
        phase = summary['pending_call']['phase']
        if phase in ('full', 'repair_full', 'full_readdress'):
            text = dr.format_readout(summary)
            assert 'CAP EXCEEDED' not in text
            if declared:
                assert summary['total_projected_dollars'] is not None
                assert not summary['cap_reached'] and not summary['trigger_reached']
            else:
                assert 'input bound unknown' in text
        return summary
    dr.compute_readout = checked
    print('declared registration:', declared)
    sys.argv = [scenario, str(output / ('declared' if declared else 'missing'))]
    runpy.run_path(scenario, run_name='__main__')
