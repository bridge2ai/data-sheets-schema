# The direct arm: Claude Code on the maintainer's subscription

Decided by the maintainer on 2026-09-22 (#2202). A third generation arm beside
the API arm (the Messages SDK through CBORG, `claudecode_api`) and the agentic
arm (Claude Code through the local proxy to CBORG, `claudecode_agent`): the
Claude Code runtime authenticated by the maintainer's claude.ai login, talking
to Anthropic directly. No proxy, no CBORG endpoint, no ledger.

| | API arm | Agentic arm | Direct arm |
|---|---|---|---|
| Runtime | Messages SDK, no tools | Claude Code 2.1.272 | Claude Code 2.1.272 |
| Provider | CBORG | CBORG, through the proxy | Anthropic, claude.ai login |
| Record runtime string | `Claude API (direct)` | `Claude Code` | `Claude Code (direct)` |
| Method directory | `claudecode_api` | `claudecode_agent` | `claudecode_direct` |
| Effort | provider default | runtime default (observed `high`) | `max`, asserted |
| Accounting | per-request ledger | per-request ledger | the runtime's terminal accounting |

The runtime string is distinct on purpose: canonical selection is scoped by
runtime key, and a subscription record reading plain `Claude Code` would be
scoped with the agentic canonicals and could supersede them. It is also what
`compare-arms` and `arm_confounds` compare: the transport difference between
the two Claude Code arms is `Claude Code` against `Claude Code (direct)`.
`provider` is recorded on every record and not compared (#2214): on the
2026-08 agentic records it is the literal the old playbook line dictated
while the transport was CBORG, and #2215 is its basis.

## What is kept from the native controls

Everything that hooks the runtime rather than the provider, imported from
`notes/matched_cborg_2026-09-13/native_controls` and never edited here: the
pre-execution command and file policies over the control protocol, the phase
history, the denial classifier and the maintainer's denial ruling, the
transcript diagnostics, the observer, and every record, receipt and evidence
gate. `execute_child` runs with a stand-in for the proxy that carries only the
controller's own stop state.

## What is different

- **Auth.** With an isolated `CLAUDE_CONFIG_DIR` the runtime looks for a
  keychain item suffixed by that directory and finds no login. The child gets
  `CLAUDE_SECURESTORAGE_CONFIG_DIR` set and empty, which makes it use the
  maintainer's own login item in the login keychain. That item is a shared
  store: a token refresh during the run may rewrite it. The child's
  environment is built from the preparer's constants, the job's variables
  and the parent's pass-through names only, and it is refused wherever a
  provider key, token, custom header, cloud-provider switch, proxy or base
  URL appears, in the launcher's own environment or in the registration.
  The job's variables are an allowlist of three names (`D4D_MANIFEST`,
  `D4D_PROFILE`, `D4D_LAUNCH_INSTRUCTION`): any other name is refused
  whatever its value, so a registration cannot add a proxy, a base URL, a
  TLS override or a model override in either spelling, or shadow a
  registered constant (#2244). The denylist behind it names every such
  variable the pinned binary reads.
  `auth status --json` is captured before launch in that exact environment:
  method, provider and plan only. The init line must report `apiKeySource:
  none`; that is a necessary condition, not proof of the login by itself,
  since the runtime reports `none` for a bearer token or a cloud provider
  too, which is why the environment is screened first.
- **Cost.** Nothing meters the provider. The receipt carries the runtime's
  terminal `usage`, the registered model's `modelUsage`, `num_turns` and its
  own `total_cost_usd`, which is the runtime's estimate. `--max-budget-usd`
  is passed as a runaway guard on that estimate; the runtime honours it on a
  login session, and it is not a cap against any allocation. The observer
  measures the transcript as it does for every Claude Code run.
- **Auxiliary model.** First-party Claude Code sessions report a second
  model, `claude-haiku-4-5`, in their terminal accounting for the runtime's
  own auxiliary calls. The proxied arm's proxy stops the run on a request for
  any model but the registered one, so an auxiliary request there would have
  stopped a run rather than gone unrecorded; none is recorded. The
  registration names the auxiliary models it permits, their usage is recorded
  under `auxiliary_model_usage`, a model outside that set stops the run, the
  registered model must carry positive input and output tokens, and no
  auxiliary model may carry as much generation as the registered one, which
  is what a main-loop fallback would look like (#2247).
  `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` is set; its effect on those
  calls is not established, since no recorded run has set it (#2248).
- **Runtime limits.** The registration states the `contextWindow` and
  `maxOutputTokens` the runtime is expected to report for the registered
  model, taken from the native registration's offline observation of the
  same model through CBORG; they are asserted, not observed on this
  transport, until the first run. The receipt records what the runtime
  reported under `runtime_limits_observed`, and a difference is a validation
  problem, since a different context window is a different instrument
  (#2246).
- **Effort.** `--effort max` is passed to the runtime and `--reasoning-effort
  max` is rendered into the instruction's own recorder line, so the record
  carries it as asserted by the launcher. The runtime does report the active
  effort, after any silent downgrade, on every tool callback, and the control
  log keeps it; after the run every reported level is compared with the
  registered one, recorded under `effort_observed`, and a difference is a
  validation problem. A run whose callbacks reported no effort at all is
  named as that, apart from a downgrade (#2249).
- **Isolation.** The registration names the checkout it was prepared in and
  the launcher refuses any other. The job's method, runtime and every output
  path must be the direct arm's, checked before any write. Writes go under
  `data/d4d_concatenated/claudecode_direct`, its core twin, and the attempt
  directory beside the registration, which a job id names: one path
  component of the preparer's shape, nothing else (#2252). Nothing under `notes/matched_cborg_*` is
  read or written: no ledger, no sequence owner, no registration, no attempt
  directory of the CBORG arms. Every check, the login probe included, runs
  before the attempt directory exists, so a refusal never consumes the job
  identity.

## Running one canary

```bash
cd <checkout>
poetry run python notes/claudecode_direct/prepare_direct.py --output <fresh dir>   # offline; no model call
# independent review of the registration; CI on the exact commit; the maintainer's launch word
poetry run python notes/claudecode_direct/run_direct_canary.py \
    --registration <dir>/registration.json --review <review.json> \
    --launch-word <word.json> --job CHORUS_direct_rep1
```

The launcher needs three files: the registration, a review binding its hash
to an approving verdict and a successful CI run, and the maintainer's launch
word quoting their exact instruction for that hash. `bind_direct_launch.py`
writes the last two and refuses a CI run that is not a completed success on
the registered commit, an independent review that approves another hash, a
blank response, or an existing file. The launcher reads the binder's whole
record: the verdict, the CI conclusion, the CI head, which must be the
registered commit, the run id and the independent review's hash (#2245).
A registered command policy that cannot be built is a named stop, as in the
native launcher (#2251):

```bash
poetry run python notes/claudecode_direct/bind_direct_launch.py review \
    --registration <dir>/registration.json --independent-review <report.json> \
    --ci-run <run id> --out <dir>/review.json
poetry run python notes/claudecode_direct/bind_direct_launch.py word \
    --registration <dir>/registration.json --exact-response "<the maintainer's words>" \
    --quoted-request "<the question they answered>" --out <dir>/word.json
```

On a subscription a one-token `--print` run under the same login, model and
effort costs nothing marginal and would show the auxiliary model and the
reported effort before a full canary. It is still a model call, and the
maintainer's word gates it like the canary.

## Not established

The runtime's estimate is not a metered charge. A run on the subscription is a
different instrument from the two CBORG arms: same model, different transport
and effort, and every comparison must say so. Kids First follows only after an
accepted CHORUS pair.
