# Native helper cache isolation (issue 5966)

Current native-v2 runtime declarations must include
`environment.PYSTOW_HOME`, the absolute canonical path
`<attempt_directory>/helper-cache`. This is the only added library variable.
PyStow imports through the term validator and oaklib write here rather than
under HOME. Production and synthetic execution use the same environment
constructor in `native_shared_registration.environment` and the same exclusive
creation in the shared lifetime. The synthetic empty-HOME check is unchanged.
Legacy v1 runtime validation retains its old environment contract.

The controller creates the directory with mode 0700 after reserving the one-use
attempt and before invoking a runtime or helper. A pre-existing directory,
even empty, or a symlink refuses creation. A new attempt gets a new directory;
no cache is copied or reused. The registration requires the attempt/cache to be
disjoint from HOME, immutable inputs, staged/output roots and source repository.
Permission expectations bind the same path and protect it from probe-root
substitution. The cache is not a registered input, output or persisted-tool
result, so the existing FileAccess classifier refuses model Read and Write.
The existing closed Bash grammar does not expose arbitrary shell/environment
commands, and the cache is outside its repository/input/output lookup roots.
This is a tool-policy boundary, not a new OS filesystem sandbox.

Retention rule: leave the cache inside the spent local attempt for diagnostic
census, including hidden entries. Do not publish it or inventory its contents
as generation evidence. The completion snapshot explicitly captures named
attempt records and selected inputs/outputs; it does not recursively capture
the attempt directory. Cache contents confer no authority. A later dependency
that still writes into HOME is rejected by the unchanged guard; no tolerated
HOME names or speculative library variables are introduced.

## Identities requiring fresh construction

| Identity | Why it changes |
| --- | --- |
| Source commit and package-source/dependency map | New cache module and changed environment, runtime, permission and lifecycle sources; the cache module is an explicitly consumer-owned source |
| Scanner integrated-render source contract | Authority, runtime and profile source pins change; the runtime dispatcher adds native_helper_cache as a callee. Helper 1 must review the expanded finite contract before updating instrument pins; this repair does not restamp them |
| Runtime declaration R | New exact environment entry, bound to one attempt |
| Runtime observation/probe sequence and bound permission sequence | Their runtime/source/expectation joins must bind the new R and code |
| Preparation A and its dependency/runtime pins | New source closure and R bytes |
| Rendered instruction/preparation identity and composition C | Reconstructed from the changed pinned preparation; retain fresh derived bytes even if some text/assets stay identical |
| Permission expectation and saved permission evidence | New explicit environment entry and fixed cache-source closure; probe roots must not overlap it |
| Execution registration E | Exact R, source dependencies, composition, permission expectation and child environment all join here |
| Review bundle, CI evidence and owner launch word | Must bind the new E/source/permission identities; a prior approval cannot carry forward |
| Capture journal, observation, subscription guard and attempt records | Bound to the new registration and exact owner-word/review bytes |

No protected prompt pins, protected branch files, historical evidence bytes,
fixed controller manifest, tool grants, account declarations or scientific
acceptance rules are restamped. The launch sequence script bytes are unchanged;
its new review bundle still binds its registered SHA-256. Failure-publication
and retention repairs remain separately owned. The only edit to
`native_execution_orchestration.py` adds cache creation after `cli_config`
creation for the shared route; it does not alter publication or readback.
