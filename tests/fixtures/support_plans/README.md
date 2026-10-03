# Historical request parity fixture

`pre_result_contract_requests.json` captures the exact expanded v1 and v2
requests and counts from the invented neutral fixture in
`tests/test_evaluation/test_support_plan.py`, before the #4282 implementation,
at main `a8ada66534f9e05b58efce5685e79648aa723023`.

Both versions used explicit model `judge`, output cap 417 and profile `neutral`;
v2 selected `full`. The source SHA256 map records capture provenance. The
regression asserts request/count parity, not permanent equality of source file
bytes. No response or scientific calibration is represented by this fixture.
