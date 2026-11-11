# Generated-product acceptance helper expects text the generator does not emit

Read-only review found two false-failure expectations in `scripts/adhoc/check_final_generation_products_20261110.py` before execution. The comprehensive SSSOM generator truncates `d4d_description` to its first 100 characters followed by `...`, but the helper compares full descriptions. Its expected old comment also says `no external vocabulary mapping needed`; the pinned base row actually says `no URI needed`.

Correct these expectations from the pinned base and generator contract before running the bounded integrated artifact check. Do not change generated artifacts or broaden allowed differences. This is diagnostic correctness work, not a semantic-exchange expansion.

Base: `7233f193ad102a8488b31ec7333662c8fefaa996`. Target integrated source: `2e9469852b09150a998793a552ffe8926bf95754`.
