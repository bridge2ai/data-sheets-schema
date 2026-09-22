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
scoped with the agentic canonicals and could supersede them. `provider` is an
arm procedure field, so `compare-arms` and `arm_confounds` report the transport
difference between the two Claude Code arms.

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
- **Auxiliary model.** The runtime's own auxiliary calls, titles and
  summaries, use a second model, `claude-haiku-4-5`, and they appear in the
  terminal accounting; the proxied arm never saw them because its proxy
  refused off-model requests. The registration names the auxiliary models it
  permits, their usage is recorded under `auxiliary_model_usage`, and a model
  outside that set stops the run. `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`
  is set to reduce them; it does not remove them.
- **Effort.** `--effort max` is passed to the runtime and `--reasoning-effort
  max` is rendered into the instruction's own recorder line, so the record
  carries it as asserted by the launcher. The runtime does report the active
  effort, after any silent downgrade, on every tool callback, and the control
  log keeps it; after the run every reported level is compared with the
  registered one, recorded under `effort_observed`, and a difference is a
  validation problem.
- **Isolation.** The registration names the checkout it was prepared in and
  the launcher refuses any other. The job's method, runtime and every output
  path must be the direct arm's, checked before any write. Writes go under
  `data/d4d_concatenated/claudecode_direct`, its core twin, and the attempt
  directory beside the registration. Nothing under `notes/matched_cborg_*` is
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
blank response, or an existing file:

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
