# Purpose: prove caught offline-denial events cannot produce D76 acceptance.
# Inputs: D76 guarded runner on a frozen checkout; output: one passing pytest
# case but a rejected runner outcome with exactly one retained denial event.
# This emits a synthetic audit event; it performs no DNS/network operation.
# Serves #5213/D76 harness finding H1; 2026-10-31.
import sys

import pytest


def test_caught_synthetic_network_denial_still_blocks_run_acceptance():
    with pytest.raises(RuntimeError, match='D76 offline guard refuses'):
        sys.audit('socket.getaddrinfo', 'd76-synthetic-invalid.example', 443, 0, 0, 0)
