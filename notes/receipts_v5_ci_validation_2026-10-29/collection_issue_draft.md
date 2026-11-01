# Offline issue draft: whole-repository pytest collection fails outside CI scope

Status: recorded locally for review; not submitted to GitHub because #5364's
follow-up explicitly forbids network and GitHub commands.

The requested whole-tree collection, through the offline validation launcher,
exited 2 with 17 errors. Evidence: [collect_root_resumed.log](collect_root_resumed.log)
and [collect_root_resumed.execution.json](collect_root_resumed.execution.json).

The errors comprise:

- Fourteen `fairscape_models` import errors: eleven submodule test modules and
  three `tests/test_fairscape_integration` modules. Collecting the whole tree
  introduces the outer submodule package namespace before those imports.
- Two historical renderer modules importing unavailable `weasyprint`.
- `src/scripts_obsolete/download_module_test.py`, which performs HTTP requests
  at module import. The offline audit hook rejected the first network attempt
  before any download or output write.

Fresh CI-scope `tests/` collection succeeds with 20,475 tests, including the
three integration modules. The exact shard 4/6 and 6/6 selectors also collect
successfully. The affected source paths and FAIRSCAPE gitlink are unchanged
from `49dd8f0eb`; this finding is outside the receipt-loop fix.

The recorded invocation is equivalent to `pytest . --collect-only -q` with
provider keys removed, network calls forbidden, and basetemp outside the
checkout. Runtime: Python 3.13.12, pytest 7.4.4. CI uses Python 3.12 and explicitly
collects `tests/` plus separate named notes lanes.

Follow-up scope: decide how repository-wide discovery should handle the nested
submodule tests and historical renderer/download scripts, while preserving
explicit CI coverage. No test exclusions, dependency changes, or historical
source edits were made for this receipt fix.
