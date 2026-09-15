# Native temperature metadata — 2026-09-15

Issue #1804 concerns native generation headers that copied `Temperature: 0.0`
from templates. Four retained main offline Claude Code requests omit the
parameter. They carry adaptive thinking and high effort in that offline probe;
these observations do not establish a provider temperature or the effort of a
future scientific request.

Fresh native instructions use renderer 7 and mark temperature as unknown.
The recorder stores null with an explicit unverified limitation. The header
checker accepts that unknown declaration against null, while still reporting
it against an asserted numeric value. Numeric assertions in historical
records are retained with their existing unverified basis. Nothing rewrites
old records or frozen raw prompts. A fixed synthetic renderer 6 instruction
still reproduces its pre-change SHA256 exactly. API rendering stays on version
5 by default, and API header stamping continues to use request settings.

These changes affect new native instruction identity and must be registered
before launch. They do not change the already stopped v10h attempt. No native
scientific canary or evaluator was run to test the engineering correction.
