"""U3-M offline timing adapter, 2026-11-09.

Inputs: the unchanged K observer and its explicit control-mode environment.
Outputs: the same per-phase evidence, additionally observing K's late admission
entry. No production monkeypatch or deadline change; code identities remain
recorded separately even when two acceptance frames are nested.
"""
from scripts.adhoc.u3k_metrics_plugin_20261109 import *

TARGETS[('native_subscription_admission.py', 'accept_current_selection')] = 'accept_saved_capture'
