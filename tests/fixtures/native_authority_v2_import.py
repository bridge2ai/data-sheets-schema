# Purpose: #5508 standalone v2 CLI import witness; input: checkout path and mode.
# Output: assertion success/failure only. Date: 2026-11-06. No CLI main is invoked.
from pathlib import Path
import sys
root = Path(sys.argv[1])
sys.path[:0] = [str(root/'src'), str(root/'notes/claudecode_direct'),
               str(root/'notes/matched_cborg_2026-09-13')]
if sys.argv[2] == 'mixed':
    import prepare_registration
    try:
        import prepare_direct_v2
    except ImportError:
        pass
    else:
        raise AssertionError('standalone v2 CLI accepted a preloaded v1 preparer')
else:
    import prepare_direct_v2
    import prepare_registration
    assert Path(prepare_registration.__file__).name == 'prepare_registration_v2.py'
    assert prepare_direct_v2.generation is prepare_registration
