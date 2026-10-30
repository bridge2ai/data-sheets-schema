"""D68: historical orphan attempts are evidence, never in-place restarts."""
import pytest
from tests.test_d68_legacy_readonly import test_authentic_legacy_refuses_without_calls_or_tree_changes as _refuse


@pytest.mark.parametrize("state", ["missing", "malformed"])
def test_fresh_restart_records_an_orphaned_partial_predecessor(tmp_path, state):
    _refuse("c3" if state == "missing" else "c2", "execute", False, tmp_path)


def test_predecessor_binding_survives_interrupted_index_activation(tmp_path):
    # C4 call 3: a prepared pre-D41 ledger, without a journal.
    _refuse("c4", "execute", True, tmp_path)


def test_fresh_restart_does_not_accept_unrelated_archived_attempts(tmp_path):
    # C1 now asserts every file and directory, including sidecar lock files.
    _refuse("c1", "execute", False, tmp_path)
