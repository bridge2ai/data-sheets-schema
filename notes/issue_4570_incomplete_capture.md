# Incomplete native final-evidence diagnostic (#4570)

Both merged native gate consumers use `native_supervisor_gates.incomplete_capture`
after capture fails. It deliberately retains `final_result=None` and
`replay_complete=False`. Their old evidence expressions dereferenced the null
result and reported an incidental `AttributeError` inside an unchecked failed
gate.

The shared `final_evidence_gate` now reports unavailable final evidence for that
explicit incomplete state. It preserves null, copies the captured problems and
keeps the evidence gate unchecked and failed. Other null or malformed states
remain failures. Existing evidence mappings retain their checked/findings
semantics and detached returned data, including when a mapping accompanies an
incomplete capture.

Focused regressions exercise the actual incomplete-capture reader followed by
each public gate consumer, compare every other gate against the previous
evidence expression, preserve the original first stop and shutdown failure,
and cover mapping and malformed-input boundaries. They launch no native child
or provider request and make no inference about process liveness from null
results.

This repair is based on merged native consumers. The unmerged #4354 shared
adapter must retain this diagnostic when its extracted gate engine is integrated;
its separate deadline, performance, shutdown and completion obligations remain.
