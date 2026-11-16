"""PR 5968 fresh-process JSON identity assertions, 2026-11-16.

Input: one named assertion helper. Output: success only after all original
assertions pass. No provider call, native executable or cache-authority reset.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))

import pytest


def main():
    from tests import test_typed_json_parse_cache as subject
    name = sys.argv[1]
    if name == 'test_replaced_copy_alias_disables_shared_values':
        with pytest.MonkeyPatch.context() as patch:
            subject._assert_replaced_copy_alias_disables_shared_values(patch)
    elif name == 'test_interpreter_integer_limit_change_refuses_a_warm_value':
        subject._assert_interpreter_integer_limit_change_refuses_a_warm_value()
    else:
        raise ValueError('unknown assertion helper')
    print(name + ' passed')


if __name__ == '__main__':
    main()
