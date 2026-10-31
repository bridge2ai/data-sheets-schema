# Issue draft: pin the v5 regex worker in shared-generation routing identity

Source: R6 in `receipts_v5_fixes_claude_rereview_2026-10-29.md` (2026-10-29).
Not filed: this task explicitly prohibits network and `gh`.

`src/data_sheets_schema/_receipt_regex.py` determines v5 receipt outcomes but
is absent from `ROUTING_CODE` in `shared_generation.py`. Changes to the worker
therefore do not change the shared-generation v2 routing identity.

Before activating v5 under routing, include the worker in that pinned code
inventory and add a regression showing that changing worker bytes changes the
routing descriptor. Evaluate the resulting assembly identity and registration
implications in that authorized change. `shared_generation.py` is protected
and explicitly out of scope for this R4/R6 follow-up.

This does not block merging the inactive instrument. R1–R3 and R5 remain
activation work; this task changes none of them.
