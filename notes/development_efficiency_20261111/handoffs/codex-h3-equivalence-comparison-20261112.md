# Equivalence comparison: first handoff

Work in progress; no implementation commit yet. Not valid for a pilot disposition.

Base: 6561dac3c3af50cbfce1ba3c8b6ad21d9cd4b834. Permitted locations so far: 23; conservative rule objects: 6825.

- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-equivalence-comparison-20261112/scripts/native_equivalence_compare.py: 450f69fe7a726b574fced79a162d9709ef3b77be520b991a24b32ba25906b9e6
- /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-native-equivalence-comparison-20261112/scripts/native_equivalence_compare.json: ee0fd408d76d421bc6368aaa45e3aa6be4a7933b4c26ce9ddfd38252a3152834

The first completed demonstration compares the two saved candidate snapshots as equal, with zero differences. The producer called every registered helper on fixed synthetic inputs, including refusal paths. Earlier canaries and their failures remain saved. Five mutation demonstrations remain. No test failure was converted to equality.

The comparator has three exits, exact-field transformations and dependent-value verification. The producer and data list remain under construction. No native execution, provider call, probe, reservation or publication occurred. The assignment-required read-only fetch selected the published head above.
