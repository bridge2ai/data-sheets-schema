"""#5212/D73, 2026-10-31: one real CI-shard test before the xdist batch.

Input: explicit canary node after the normal CI plugin has selected its shard.
Output: one selected node in every worker, with all other nodes deselected.
Only the offline validation launcher loads this plugin; ordinary CI is untouched.
"""
import pytest


def pytest_addoption(parser):
    parser.addoption("--d73-canary-node", required=True)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_modifyitems(config, items):
    result = yield
    node = config.getoption("--d73-canary-node")
    selected = [item for item in items if item.nodeid == node]
    assert len(selected) == 1, "canary must belong to the real selected CI shard"
    config.hook.pytest_deselected(items=[item for item in items if item not in selected])
    items[:] = selected
    return result
