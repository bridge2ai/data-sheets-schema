# Native launch verification audit — 2026-11-11

**Result:** AGY4's headline counts and inclusive CPU totals are correct: nine shared-registration verifications, fourteen execution verifications, twenty-one preparation verifications and one prewarm. I found **no additional measured call site for which the already-reviewed narrowed capture recheck is demonstrably sufficient**. The CPU attributed to that newly narrowable group is therefore **0 seconds**. This route cannot, on the available evidence, supply the approximately **44.20 seconds** needed to reach the 210-second target on its own. This is not a proof that every repeated derivation is irreducible; several intervals remain unproved, and the large prewarm residual has no applicable retained function profile.

This audit inspected Git objects at **382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b**, not current working-tree source, in `d4d-executions/codex-native-u1u3`. It read the completed diagnostic only. No tests, diagnostic reruns, compositions, native executables, production imports, provider calls, network operations, source/config changes, commits, GitHub actions or STATUS edits were performed. The only writes are this report and the read-only analysis helper identified below.

**Evidence and measurement method**

The retained run is `d4d-executions/scratch-native-u1u3/u3m/wp1-382f0dfd1ce8-cpu-monitoring-lead-rerun-20261111`.

| Input | SHA-256 |
|---|---|
| `phase-metrics/67941-measurement.json` | `12cba82d359f98d39220db521d8920130da94f863b554d265c0116736738a31d` |
| `phase-metrics/67941-diagnostic.json` | `33b032291d891f06249596da823d2a6f26d87d59317388f078b3a399ffc21cba` |

I independently selected the launch phase's rows `[457,1122)`, counted the labels, checked agreement with the recorded counts, and rebuilt the monitored call tree from entry times and inclusive durations. All 665 rows are closed and on one recorded thread. Subtracting each row's **direct monitored children** gives CPU outside those children; it includes unmonitored descendants and measurement overhead, and is not Python function self-time. All such disjoint residuals sum to 243.397365 seconds, the public-launch interval, within 0.000779 seconds of the phase's 243.398144 thread CPU. No inclusive times across nested layers are added as potential savings.

| Measured label | Count | Callee first line | Distinct recorded code-object IDs | Inclusive thread CPU, seconds | Outside direct monitored children, seconds |
|---|---:|---|---:|---:|---:|
| `shared_registration_verified` | 9 | `native_shared_registration_orchestration.py:129` | 1 | 108.372327 | 28.604915 |
| `execution_registration_verified` | 14 | `native_execution_registration_v2.py:475` | 1 | 113.838536 | 53.939775 |
| `preparer_verified` | 21 | `native_execution_registration_v2.py:375` | 1 | 66.579529 | 52.664646 |
| `controller_prewarm` | 1 | `native_shared_controller_orchestration.py:228` | 1 | 64.187670 | 56.764656 |

The three verification-layer residuals total 135.209336 seconds. That is a disjoint attribution to expensive work, **not** a safe-to-remove amount. The first shared call contains the first execution and preparation calls; prewarm also contains an execution/preparation pair. A recorded code-object ID does not establish that all objects, loader scopes or classifier lifetimes used beneath it are the same.

Corrections to `handoffs/agy4-diagnostic-result-analysis.md`:

- Counts and headline inclusive/residual totals in the table above are correct. The execution verifier is at line **475**, not 678. The execution and preparation rows each record **one** code-object ID, not two and fifteen respectively.
- Execution-verification minimum/maximum inclusive thread CPU are **4.416479 / 20.586678**, not 5.864857 / 20.590297. Preparation minimum/maximum are **1.046536 / 16.841838**, not 1.045458 / 15.553598.
- Prewarm's actual coarse split is **48.630105 user + 15.557570 system = 64.187675 seconds** within timer rounding; the coarse process clock reads 64.187673. Its reaped-child split is **0.266166 user + 0.581480 system = 0.847646 seconds**. The reported 58.972226/5.215436 and 0.219129/0.409052 splits are not this row's values.
- This measured route does not call `_join_subscription_authority` twice before the refusal. The first static inspection is the `CurrentSelection` branch at engine lines 335–336; the alternative join at 340–341 is skipped. The actual join is at 369–370. The call map below accounts for all nine shared verifications without counting both alternatives.
- The estimated 6.5–7.5 seconds saved per substituted warm verification, and hence 40–50 seconds for six or seven substitutions, are not established by these rows. There is no separately measured equivalent narrow replacement at those sites, and this audit does not establish the substitutions' safety.

**What the existing narrow recheck actually proves**

All source references below mean `src/data_sheets_schema/` at the full commit above. To keep the call tables readable, these abbreviations identify exact files:

| Alias | File |
|---|---|
| Front | `native_shared_execution_orchestration.py` |
| Engine | `native_execution_orchestration.py` |
| Shared | `native_shared_registration_orchestration.py` |
| Exec | `native_execution_registration_v2.py` |
| Controller | `native_shared_controller_orchestration.py` |
| Capture | `native_subscription_capture.py` |
| Subscription | `native_subscription_admission.py` |

`Capture.read_capture_for_event:720` first obtains a fully verified authority tuple. After journal/claims enumeration and matching-manifest inspection, `:738` calls `_read_capture_with_authority`, whose `:677` reaches `_recheck_authority:153`. That recheck retains the **local initial authority**, runs `Shared._recheck_verified`, recomputes review/word/request bindings and compares the complete authority tuple (`Capture:148–158`). Matching-slot reconstruction then rereads the capture evidence (`:618–669`). For **that within-reader interval**, the classification is **a narrowed recheck is sufficient**. It is already present in 382f; it is not an additional optimization of any of the 44 full-verifier rows counted above.

The narrow shared recheck (`Shared:142–269`) is substantial. It reparses the canonical envelope and compares its whole body with the initial value; recaptures dependency/source identity, committed closure, controller manifest and cwd; rechecks physical argument/path bindings; recaptures selection/runtime; rereads preparation pins, composition, instruction, system and permission-probe bytes; and validates runtime observations and the bound permission sequence. Executable identity is independently fingerprinted by runtime validation. `_recheck_authority` additionally recomputes the review/word/capture-request join. Capture reconstruction rereads current-word/journal state, reservation, claims, manifest, streams, observations and terminal result. Narrowing does **not** mean trusting file modification times or omitting freshness/one-use checks.

It nevertheless carries forward some initial proofs rather than reproducing them:

- Full execution verification accepts an explicit live classifier projection, freshly verifies preparation, and reconstructs the execution body through the verified source-loaded consumer (`Exec:487–534`). Narrow verification accepts no projection. It cannot authenticate its exact type, mint membership, active lifetime, original member identities or current source-callable identity. Those checks are explicit in `native_shared_controls.py:42–59,100–115` and used by `native_shared_registration.py:239,256,261,289`.
- Full preparation reconstructs a guarded `RunSpec`, renders instruction/spec/input identity, and independently derives outputs and the pin roster (`Exec:334–370,393–398`). Full composition compares a freshly derived instruction/spec with captured values (`Controller:48–67`). The narrow path compares the captured values and current pinned files without recreating that derivation.
- Full execution reconstruction recomputes policy guidance, effective system text, permission expectations/observations, argv, environment and optional receipt-origin declaration (`native_shared_registration.py:256–282`). Carrying forward those fields is justified by an appropriate initial proof and interval; identical disk bytes alone do not establish that interval.

A concrete source-derived distinction is `VIRTUAL_ENV = sys.prefix` in `native_shared_registration.py:35–39`. Dependency identity records the Python executable, version and executable hash, not `sys.prefix` (`native_supervisor_authority_v2.py:45–49`). With otherwise unchanged bytes, a changed prefix changes full reconstruction's environment; the narrow check neither rederives nor explicitly checks that field. This is an **unexecuted source counterexample to general equivalence**, not evidence that the diagnostic changed its prefix or that such a change is reachable during every interval below. Likewise, full verification is not a guarantee of arbitrary interpreter-global immutability: `native_execution_authority_v2.py:584–604` documents the narrower source/callable identity contract.

**Per-call classifications**

The classifications concern replacing the **current site's obligation with the existing reviewed narrow pattern**. “Must stay a full verification” means the current boundary needs an independent full proof; it is not a claim about every possible future architecture. “Cannot tell from source” contributes no savings: the necessary missing evidence is stated. An untrusted supplied dictionary equal to raw bytes is not itself a previously established proof.

For the tables, the state reread by each full layer is:

- **S:** Shared full verification (`Shared:129–139`) recaptures dependency identity, enters loaded controls, invokes full E and validates runtime observations/bound permission evidence.
- **E:** Exec full verification (`Exec:475–534`) checks the closed wire/dependency roster, invokes full P, recaptures runtime/selection/composition bindings and committed source, authenticates the classifier through reconstruction, reconstructs the complete execution body, compares it and recaptures dependencies.
- **P:** Full preparation (`Exec:375–400`) checks the closed preparation, current source/dependencies, runtime declaration, guarded spec/render/input/output derivations and final dependency equality.

Each S/E/P entry below therefore specifies both its reread set and the interval that makes the repeat distinct. Full calls nested inside a retained full boundary cannot independently be replaced with a narrow check that presupposes the proof they are establishing. The uncertain status of some *outer* repetitions does not license weakening the inner full-verifier implementation.

The nine shared calls, in measured order:

| Row; inclusive CPU seconds | Call site | State and interval since the prior proof | Classification and narrow-check answer |
|---|---|---|---|
| 458; 23.627346 | `Front:114` → `Shared:129` | S; synthetic front-door entry from caller bytes, before preflight/selection. No initial proof in this invocation. | **Must stay a full verification.** No trusted initial value exists for the narrow pattern. |
| 505; 9.774378 | `Engine:290` → `Shared:129` | S; follows front-door runtime/profile checks, current-selection construction and preflight, but is also an independent raw-byte entry. Front-door proof is not passed in. | **Must stay a full verification.** The current engine contract establishes its own proof. |
| 541; 10.650903 | `Engine:328` → `Shared:129` | S; follows row 505 and opening `loaded_capabilities` at 292. The private launch receives controls/raw bytes, not the engine's verified value. | **Cannot tell from source.** Need proof that initial-value provenance and every newly opened capability/source-loader obligation survive a narrow recapture, including live classifier/derived-state coverage. The capture reader establishes no such cross-loader rule. |
| 599; 10.806283 | `Engine:335–336` → `Subscription:99,147` → `Capture:720,143` | S plus fresh capture authority; follows launch verification and independent authorization, then checks selected guard/review/word and scans saved capture. | **Must stay a full verification.** This is the capture reader's initial proof, not its subsequent narrow matching-slot read. It receives raw registration/review/word without a prior authority tuple. |
| 665; 10.142540 | `Engine:342` → `Front:38` | S; after rows 541/576/599, authorization reconstruction and static subscription inspection. `_unchanged` also rereads review/CI/word and host platform at `Front:40–45`. | **Cannot tell from source.** File/pin mutations are covered by narrow recapture, but live-control/derived-state equivalence through the intervening calls is not proved. Deciding evidence is an interval-specific refusal/derivation equivalence argument covering those states, while retaining the additional authorization/platform checks. |
| 898; 10.500568 | `Engine:366–368` → `Subscription:118,168,147` → `Capture:720,143` | S plus current capture authority; after admission, adapter construction and a fully unwound prewarm scope. Acceptance reads current selected guard/word/review and saved evidence. | **Must stay a full verification.** A new reader invocation has no carried initial authority. A matching-slot narrow read still occurs inside it. |
| 972; 11.519216 | `Engine:369–370,143` → `Subscription:147` → `Capture:720,143` | S plus fresh current authority; after actual capture acceptance, checks the current guard/type/clock join. | **Must stay a full verification.** Accepted guard/value is not the reader's full initial-authority tuple. Current journal/guard/clock obligations remain separate. |
| 1046; 11.370907 | `Engine:371` → `Front:38` | S plus authorization/platform rereads; after fresh admission, adapter/prewarm lifetime, actual acceptance and current join. | **Cannot tell from source.** Need evidence covering closed/reopened loader and classifier lifetimes and all freshly derived execution state across this larger interval. The existing within-capture pattern does not prove that equivalence. |
| 1080; 9.980186 | `Engine:379–381` → `Capture:467,430–436,143` | S plus current review/word authority; follows row 1046, establishes authority immediately before taking the word/limits lock at `Capture:468` and requiring the word at 469. | **Must stay a full verification.** Independent lease entry reconstructs its own authority. Neither prior value nor previous lock is supplied; retain locking and immediate freshness check regardless. |

The fourteen execution calls consist of the nine S children plus five direct calls:

| Measured E rows; inclusive CPU seconds | Call site | State and protected interval | Classification |
|---|---|---|---|
| 459: 20.586678; 506: 6.707121; 542: 7.518546; 600: 7.591945; 666: 7.006143; 899: 7.247032; 973: 8.189878; 1047: 8.127180; 1081: 6.724301 | `Shared:138` → `Exec:475` | E, in each S invocation above's newly loaded controls. This is how the full outer helper obtains its independent execution proof. | **Must stay a full verification** inside a full S boundary. Replacing this with a recheck would assume the proof that S is currently establishing. Whether a particular outer repeat can cease being a full S boundary is answered separately above. |
| 576; 7.337120 | `Engine.authorizations:122` | E; independent `(raw, value)` entry enters fresh controls before capturing external authorization at 124. Matching caller-supplied value alone does not authenticate its derivation. | **Must stay a full verification.** Narrow verification has no authenticated initial proof or live-classifier check at this entry. |
| 731; 7.317775 | `Exec.admit:668` | E; after composition/path/runtime checks, the fresh admission boundary consumes the explicit current classifier at `Engine:351–354`. | **Must stay a full verification.** Admission independently establishes authority; an earlier launch value is expressly not a launch capability (`Engine:349–350`). |
| 761; 4.416479 | `Exec.admit:681` | E; closes the interval containing external authorization reads, host-runtime validation, a verified consumer's path calculation and reservation checking (`:669–678`). Evidence is reread again at 684. | **Must stay a full verification.** Existing narrow verification does not authenticate the supplied projection or independently rederive execution after these operations; it cannot substitute for this full admission contract. |
| 778; 7.855182 | `Controller.CallbackAdapter.__init__:192` | E; live adapter construction enters controls and verifies caller-supplied raw bytes and execution dictionary before constructing composition/attribution and storing mutable adapter state. | **Must stay a full verification.** This independently callable adapter boundary does not accept an authenticated earlier proof. |
| 864; 7.213155 | `Controller.prewarm_before_acceptance:244` | E; after adapter construction, enters a new temporary loader/mint lifetime and compares with the stored execution at 245, before constructing callbacks at 247. | **Must stay a full verification** for the current prewarm contract. The inactive-adapter flag is not proof of unchanged derivation/classifier state; a new scope is verified. This does not classify the entire prewarm's residual as irreducible. |

The twenty-one preparation calls are fourteen E children, six calls bracketing three compositions, and one reservation check:

| Measured P rows; inclusive CPU seconds where useful | Call site | State and protected interval | Classification |
|---|---|---|---|
| 460, 507, 543, 577, 601, 667, 732, 762, 779, 865, 900, 974, 1048, 1082 | `Exec.verified:493` → `Exec.verify_preparer:375` | P; fresh preparation for each E entry above before the input-only consumer trusts its preparation. There is no separately authenticated preparation supplied to this helper. | **Must stay a full verification** inside full E. Using a narrow check here would make independent reconstruction depend on the proof it is supposed to establish. |
| 700; 1.046536 | `Engine:344` → `Controller.verified_composition:168` → `_compose:42` | P; first preparation proof of this composition entry, following `_unchanged` and runtime observation. Composition accepts preparation bytes rather than a trusted E proof. | **Must stay a full verification.** Establishes independent preparation before a fresh RunSpec/render/policy reconstruction. |
| 718; 1.069725 | Same composition, `_compose:124` | P; after current selection/spec/render validation, source-loaded controls/protocol/consumer recapture, composition and loader unwind (`Controller:43–123`). Instruction bytes are reread at 125. | **Cannot tell from source.** Need proof that all preparation derivations and mutable renderer/bootstrap state are invariant across this interval, or equivalent refusal coverage. Pin equality alone does not establish that; the existing narrow API is for E, not this standalone preparation. |
| 749; 1.109413 | `Exec._checked_reservations:628` | P; after `admit:668`, authorization/runtime checks and source-loaded execution-path calculation, independently obtains expected selected pins, outputs and reservation paths (`:629–653`). | **Cannot tell from source.** Need evidence that a narrower check preserves independent output/pin-roster derivation rather than trusting the consumer's result. Physical-path, existence and overlap checks must remain. |
| 795; 1.111847 | `Controller.CallbackAdapter.__init__:199` → `_compose:42` | P; separate composition entry after adapter's full E check. Reconstructs the composition before storing its spec/selection. | **Must stay a full verification** at this composition entry; no trusted preparation capability is passed. |
| 813; 1.097688 | Same adapter composition, `_compose:124` | P; closes this invocation's policy/source-loader/render interval. | **Cannot tell from source.** Same missing preparation/ambient-state equivalence evidence as row 718, for this separate invocation. |
| 829; 1.098365 | `Controller:212` → `native_shared_attribution_orchestration.live:34` → `_compose:42` | P; after adapter composition, live attribution reconstructs its own composition and then compares selection/spec with supplied live objects (`attribution:35–38`). | **Must stay a full verification** at the attribution's independent composition entry. Equal supplied objects are not a previous preparation proof. |
| 847; 1.142093 | Same attribution composition, `_compose:124` | P; closes the attribution reconstruction's source-loader/policy interval before returning the reconstructed objects. | **Cannot tell from source.** Need equivalent derivation/refusal evidence over this specific interval, including final comparison with the caller's live spec/selection. |

These tables account for all 9 + 14 + 21 full-verifier calls. They intentionally distinguish one function's repeated invocations from distinct call sites. The remaining measured operation is the one prewarm below.

`native_subscription_guard_v2.py` supplies no hidden full-registration proof: `_admission:318` is an outer-byte/runtime join, `_static:400–402` repeats that join, and `_fresh:419–437` reads guard/clock/age/reset/dispatch state. Those necessary checks do not replace initial registration reconstruction. Conversely, full registration verification does not replace current-word locking, real-clock freshness or one-use dispatch.

**Prewarm: what is known and what the retained profiles do not show**

Row **863**, `Controller.prewarm_before_acceptance:228`, is **cannot tell from source** for narrowing the complete warmup. It consumes **64.187670 thread CPU seconds**, of which **56.764656** are outside monitored children. It starts after adapter/attribution construction and closes its whole temporary callback/source-loader scope before current saved-capture acceptance. No temporary admission, active finder or warmed callback capability escapes. Its inner full E obligation is classified separately in row 864 above.

| Direct monitored child of row 863 | CPU seconds |
|---|---:|
| Row 864, execution verification (including its P child) | 7.213155 |
| Rows 881 and 884, selection captures | 0.154184 |
| Row 887, synthetic peer fingerprint | 0.000855 |
| Row 888, selection rebuild | 0.054820 |
| Total direct children | 7.423014 |

The source identifies what can occupy the residual, but does not time those components:

- `native_shared_callback_orchestration.py:218–237` freezes a RunSpec, rebuilds registration arguments and loads the classifier, utility modules, callback modules and fixed execution consumer.
- `:238–260` reads/verifies source and deferred-import graphs and loads graph/orchestration modules.
- `:261–285` recaptures selection, rederives commands/render spec, assembles and checks source/input pins and module identities, mints temporary admission and reconstructs execution.
- `:286–311` constructs phase/attribution/receipt state, wraps callback entry points, installs the worker import guard and then performs teardown/source checks. `native_shared_callback_capture.py:84–96` checks the active mint and brackets consumer reconstruction with source checks.
- `native_execution_authority_v2.py:952–965` performs physical-file, byte, metadata and digest checks. Its verified loader at `:969–1103` manages source graphs and module bindings, compiles/executes source when required and restores bindings. The fresh-compilation/enclosing-loader contract is at `:974–977`; compile/exec is at `:876–877`.

The narrowed capture recheck does not freeze a callback RunSpec, reconstruct callback admission, establish an active mint or verify this callback import lifetime. A claim that some work is merely duplicate warming needs evidence distinguishing pure derivations from those live checks, plus unchanged refusal/activation behavior. The temporary nature of prewarm makes redundant work plausible; it does not establish safe replacement or quantify savings. Simply dropping prewarm could move cold work to actual activation after acceptance, not remove it. Actual activation (`Controller:258–272`) opens and retains a fresh callback scope and performs one-use admission; that path was not reached in this diagnostic.

The retained-profile search included ignored and hidden files (`rg --files --hidden --no-ignore`, followed by `find`) under `scratch-native-u1u3/u3m`, and a broader search under `scratch-native-u1u3` for historical profiles. No `*call*calibr*` path was found in the U3-M evidence scope. This is a scoped absence finding, not a claim about the entire machine.

| Existing profile inspected | What it can establish |
|---|---|
| `u3m/metrics-canary-672bcdb45/phase-metrics/62771-canary.pstats` | Instrumentation witness, total recorded time 0.050466 seconds; no native prewarm functions. SHA-256 `274bccdf941cf795be2ef650a3a10572c13a6490692b63b4d5ad2a16689446a2`. |
| `u3k/profile-pre-reservation-a2241d4c6/phase-metrics/41580-launch.pstats` | Historical a2241d4c6 launch; no `prewarm_before_acceptance` entry. `verified_source_module` has 44.418540 inclusive seconds, but its nested totals overlap and are not this prewarm. SHA-256 `b4511f0fe314ff2e008e55bab4c45fa79ba0df33cb068b8eb7074ff224febf31`. |

The adjacent historical fixture profile/function summaries also belong to that earlier run, not the measured launch. None supplies a function-level attribution of the **current 56.764656-second residual**. AGY4's suggestion that retained call-calibration pstats already decompose it is unsupported by the evidence found. Equal top-level bytecode hashes would not prove equal callees, source closure, globals, input workload or cache state; current authority code has import-fact caching and fresh policy evaluation (`native_execution_authority_v2.py:226–265,447–464`). Historical timing proportions cannot be transferred to 382f.

**CPU total and disposition**

The only site classified **a narrowed recheck is sufficient** is the already-shipped full-initial-read → narrow-matching-slot-read pattern inside one capture reader. It has already reduced the observed path. Among the measured full-verifier/prewarm calls, there are **zero newly proven sufficient narrow replacements**, so the non-overlapping measured CPU at newly eligible sites is **0 seconds**. No potential savings are assigned to uncertain sites; no outer/inner totals are double-counted; even an eligible call's full CPU would be an upper bound before paying replacement cost.

The phase consumed 243.398143 process CPU seconds and 295.745893 wall seconds. Capture preceded launch by 10.802291 seconds, leaving 199.197709 of the 210-second allowance at launch entry. On the assignment's optimistic self-CPU basis, the deficit is therefore **243.398143 − 199.197709 = 44.200434 seconds**. Reaped-child CPU is a separate 17.308275 seconds; it is not included in the verification thread-CPU figures or used to invent per-site savings.

The three recorded `freshness_before_dispatch` calls entered at capture ages 38.526258, 259.396027 and 279.556570 seconds and returned successfully. The `freshness_before_reservation` entry at row 1120 was at age **306.533703 seconds** and refused, about **96.53 seconds** beyond its 210-second limit. The differently named inner freshness entry differs by microseconds; these are entry ages, not an amended capture timestamp. Reservation `mkdir` at `Engine:387`, runtime probe, child dispatch, active callbacks and finalization were not reached. Their later verifications (`Engine:421,431,506`) are outside this measurement; no projected savings or acceptance claims are made for them.

The host was unqualified and contended, and observer overhead remains included. The arithmetic is a diagnostic bound under the assignment's stated assumptions, not a forecast for a quiet or uninstrumented launch. Nevertheless, **the supported narrowing route cannot reach the 210-second target on its own**: it currently offers 0 proven seconds against about 44.20 needed. The measurement confirms that repeated verification and prewarm are expensive, but does not overturn the earlier source-only conclusion of **no material safely established change available through this narrow-recheck substitution route**. It leaves narrower uncertainty about some repeated intervals and the unprofiled prewarm internals, rather than establishing that no optimization of any kind can exist. No design or patch is proposed by this audit.

**Reproduction and handoff**

The only helper created/updated for this assignment is:

`d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/audit_native_launch_verification_20261111.py`

SHA-256: `b2deba242192148a247145c986b9f68ca515f2c20f167485a479621874b676e4`.

It uses only the standard library to read existing JSON/pstats and prints to stdout. Its `counts` mode reconstructs the monitored nesting, counts, residuals and freshness arithmetic; `profiles` reads named existing pstats files. It imports no repository production code and writes no evidence artifacts. For the counts, it was run from the development-efficiency checkout with:

```sh
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin HOME=/var/empty \
  /opt/homebrew/Caskroom/miniforge/base/bin/python3.13 -S -B \
  scripts/adhoc/audit_native_launch_verification_20261111.py counts
```

Source references were read with `git show 382f0dfd1ce863fdf257a77e2bbb2637dbe2f67b:<path>` and line-numbered locally. Independent read-only passes checked the preparation, capture/launch and prewarm intervals. Existing evidence and the one-use diagnostic guard were preserved. Assignment complete; stop here.
