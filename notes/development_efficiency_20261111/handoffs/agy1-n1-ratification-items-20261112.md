# AGY1 Handoff: Open Ratification Items of Native Amendment N1 (as Data)

- **Date**: `2026-11-12`
- **Assignment**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/assignments/claude-lead-agy1-n1-ratification-items-20261112.md`
- **Primary Repository**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema`
- **Amendment Commit**: `754fbfdae10dbe9fe3f4443725cf0fa2a696b49e` (branch agy/native-amendment-n1-20261108; checked-out file `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/agy-native-amendment/notes/generic_v10_analysis_plan_amendment_n1_2026-11-08.md`)
- **Amendment File SHA-256**: `741677373008237020d409a7f79365b3e2d0f188a16d996b5defb3a14af050aa` (`412` lines)
- **Status Ledger**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md`
- **Extraction Script**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/n1_ratification_items_20261112.py`
- **Extracted JSON**: `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/notes/development_efficiency_20261111/handoffs/agy1-n1-ratification-items-20261112.json`

## Extraction Command

```zsh
/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/.venv/bin/python /Users/marcin/Documents/VIMSS/ontology/bridge2ai/d4d-executions/codex-development-efficiency-20261111/scripts/adhoc/n1_ratification_items_20261112.py
```

## Summary Counts

| Metric | Count | Details |
|---|---:|---|
| Lettered ratification items in N1.8 | `24` | Items `(a)` through `(x)` (`lines 346–369`) |
| Items with a `[proposed]` matching clause in body | `24` | All 24 items `(a)`–`(x)` (`0` items without `[proposed]`) |
| Items naming a recorded owner decision (item text + immediate matching clause lines) | `16` | `(b), (c), (d), (e), (f), (g), (h), (k), (l), (m), (p), (s), (t), (v), (w), (x)` (`12` name standalone top-level owner rulings `D43, D53, D56, D71, D98, D99, D107, D108, D110, D111, D114, D115, D117, D118`; `4` — `(f)`, `(g)`, `(p)`, `(s)` — name only `D18`, `D14`, or `D12`, which are recorded in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` at `lines 818, 820, 821` as `D107` default sub-bullets under `L805`/`L815`) |
| Items naming no owner decision (item text + immediate matching clause lines) | `8` | `(a), (i), (j), (n), (o), (q), (r), (u)` |
| Items naming a recorded owner decision / naming none when enclosing block lines are included (`B0–B7` lines `178–224` for `(i)` and margin-refusal lines `262–264` for `(u)`) | `18` / `6` | Including enclosing blocks adds `(i)` (`D109, D43, D53, D56, D36`) and `(u)` (`D115, D113`), leaving `(a), (j), (n), (o), (q), (r)` naming none |
| Lines in amendment containing `[proposed]` | `24` | `26` total `[proposed]` occurrences across `24` lines (lines `159` and `161` contain 2 occurrences each; line `24` is the document-level rule; lines `110` and `341` both mark `(h)`) |
| Distinct owner decision numbers (`D` + digits) named across items and matching/enclosing clauses | `23` | `D11, D12, D13, D14, D18, D36, D43, D53, D56, D71, D98, D99, D105, D107, D108, D109, D110, D111, D113, D114, D115, D117, D118` |

## 1 & 2. N1.8 Lettered Ratification Items, `[proposed]` Clauses, and Named Decisions

| Letter | N1.8 Line | Full Text (Exact Line from Amendment) | Matching Clause `[proposed]`? | `[proposed]` Line(s) | Matching Clause Line(s) | `D`-Decisions in Item Text | `D`-Decisions in Matching Clause Line(s) | Additional `D`-Decisions in Enclosing Block |
|---|---:|---|---|---:|---:|---|---|---|
| `(a)` | `346` | `- **(a)** No auxiliary models, accepting that an auxiliary call stops the attempt (N1.2).` | Yes | `136` | `136`, `137`, `138`, `139` | none | none | none |
| `(b)` | `347` | `- **(b)** The pinned executable is a durable copy outside the auto-updater's path (N1.2, D11).` | Yes | `150` | `149`, `150`, `151` | `D11` | `D11`, `D107` | none |
| `(c)` | `348` | `- **(c)** D13: the literal launch argv recorded verbatim (#4162).` | Yes | `159` | `159` | `D13` | `D13`, `D114` | none |
| `(d)` | `349` | `- **(d)** D13: any change to a pinned item is a new registration.` | Yes | `159` | `159` | `D13` | `D13`, `D114` | none |
| `(e)` | `350` | `- **(e)** D13: the transcript-based receipt origin is the "receipt origin" D107 names (N1.1).` | Yes | `121` | `121` | `D13`, `D107` | `D107`, `D13` | `D105` (lines `117–121`) |
| `(f)` | `351` | `- **(f)** D18: its old meaning (the #4354 offline time box) is closed.` | Yes | `161` | `161` | `D18` | `D18` | none |
| `(g)` | `352` | `- **(g)** D18: the registration is valid for two weeks from its registration commit's author date.` | Yes | `161` | `161` | `D18` | `D18` | none |
| `(h)` | `353` | `- **(h)** Schema 3.2.0 for the native arm, superseding D71(a) for that arm only (N1.1).` | Yes | `110`, `341` | `110`, `111`, `341` | `D71` | `D98`, `D99`, `D108`, `D71` | none |
| `(i)` | `354` | `- **(i)** The N1.4(B) row set, B0–B7.` | Yes | `178` | `178` | none | none | `D109`, `D43`, `D53`, `D56`, `D36` (lines `178–224`) |
| `(j)` | `355` | `` - **(j)** B3: the typed-protocol ordering mapping, with `receipt_chunks_unopened` reported only. `` | Yes | `199` | `199`, `200`, `201`, `202`, `203`, `204` | none | none | none |
| `(k)` | `356` | `- **(k)** B4: the native clean checks and their evidence.` | Yes | `205` | `205`, `206`, `207`, `208`, `209`, `210` | none | `D43`, `D53`, `D56` | none |
| `(l)` | `357` | `- **(l)** Admission: starting seven-day utilisation ≤ 0.50. D118's record restates this value; a "no" here supersedes D118's restated 0.50 for this amendment.` | Yes | `250` | `250` | `D118` | none | none |
| `(m)` | `358` | `- **(m)** Admission: a window is allowed when its utilisation is a finite non-boolean number with 0 ≤ u < 1 and its reset is after capture and dispatch. D118 sets the five-hour bound, and presence of both windows is implied by it.` | Yes | `252` | `251`, `252` | `D118` | `D118` | none |
| `(n)` | `359` | `` - **(n)** Admission: a further window judged by the same rule when it carries `utilization`, and recorded but not refused otherwise. `` | Yes | `253` | `253` | none | none | none |
| `(o)` | `360` | `` - **(o)** Freshness, one rule with two values: `captured_at` ≥ the word's `authorized_at`, and `max_age_seconds` = 300. `` | Yes | `255` | `255` | none | none | none |
| `(p)` | `361` | `- **(p)** Deadline: 21,600 s.` | Yes | `279` | `279` | none | `D14` | none |
| `(q)` | `362` | `` - **(q)** Host: keep-awake `macos_iokit_ims_v1` on AC power, accepting that mid-run loss is undetected. `` | Yes | `276` | `276`, `278` | none | none | none |
| `(r)` | `363` | `- **(r)** Host: the quiet-window lock held by the operator for the attempt.` | Yes | `277` | `277` | none | none | none |
| `(s)` | `364` | `- **(s)** The owner may stop the attempt manually, as operator.` | Yes | `287` | `287` | none | `D12` | none |
| `(t)` | `365` | `- **(t)** D107's stop rule read as in N1.5: usage is a live stop, and acceptance-row failures are judged after the attempt.` | Yes | `288` | `288` | `D107` | `D107` | none |
| `(u)` | `366` | `- **(u)** Freshness margin: at least 90 s left at the pre-reservation check.` | Yes | `256` | `256` | none | none | `D115`, `D113` (lines `237–384`) |
| `(v)` | `367` | `- **(v)** After three failed captures: a new word for the same registration within its validity window, with no attempt consumed. This extends D115, and the newer word supersedes the earlier one.` | Yes | `265` | `265`, `266`, `267` | `D115` | `D115` | none |
| `(w)` | `368` | `- **(w)** The owner statement is how the word states D110's and D111's terms, bound through the review bundle.` | Yes | `233` | `233` | `D110`, `D111` | `D110`, `D111` | `D118`, `D115` (lines `233–402`) |
| `(x)` | `369` | `- **(x)** Every capture's limits are cross-checked, not only the first (stricter than D117).` | Yes | `130` | `130`, `131`, `132` | `D117` | `D117` | none |

## 3. Owner Decision Numbers Cross-Referenced in `/Users/marcin/Documents/VIMSS/ontology/bridge2ai/data-sheets-schema/notes/coordination/STATUS.md` (via `grep -n`)

| Decision | Named by Item(s) (Item Text / Clause) | Named in Enclosing Block Only | Recorded as Decided by Owner in Status Ledger? | Record Type | Heading Line(s) | Bullet Line(s) | Total `grep -n` Matches |
|---|---|---|---|---|---|---|---:|
| `D11` | `(b)` | none | Yes | `d107_amendment_default_subbullet` | `805` (via `D107`) | `815` (`D107`), `817` | `3` |
| `D12` | `(s)` | none | Yes | `d107_amendment_default_subbullet` | `805` (via `D107`) | `815` (`D107`), `818` | `1` |
| `D13` | `(c)`, `(d)`, `(e)` | none | Yes | `d107_amendment_default_subbullet` | `805` (via `D107`) | `815` (`D107`), `819` | `1` |
| `D14` | `(p)` | none | Yes | `d107_amendment_default_subbullet` | `805` (via `D107`) | `815` (`D107`), `820` | `3` |
| `D18` | `(f)`, `(g)` | none | Yes | `d107_amendment_default_subbullet` | `805` (via `D107`) | `815` (`D107`), `821` | `3` |
| `D36` | none | `(i)` | Yes | `standalone_owner_decision` | none | `132` | `4` |
| `D43` | `(k)` | `(i)` | Yes | `standalone_owner_decision` | none | `186` | `18` |
| `D53` | `(k)` | `(i)` | Yes | `standalone_owner_decision` | none | `262` | `10` |
| `D56` | `(k)` | `(i)` | Yes | `standalone_owner_decision` | none | `277` | `10` |
| `D71` | `(h)` | none | Yes | `standalone_owner_decision` | `416` | none | `9` |
| `D98` | `(h)` | none | Yes | `standalone_owner_decision` | `552` | `553` | `8` |
| `D99` | `(h)` | none | Yes | `standalone_owner_decision` | `552` | `559` | `8` |
| `D105` | none | `(e)` | Yes | `standalone_owner_decision` | `717`, `805` | `806` | `22` |
| `D107` | `(b)`, `(e)`, `(t)` | none | Yes | `standalone_owner_decision` | `805` | `815` | `5` |
| `D108` | `(h)` | none | Yes | `standalone_owner_decision` | `797` | `798` | `10` |
| `D109` | none | `(i)` | Yes | `standalone_owner_decision` | `787` | `788` | `3` |
| `D110` | `(w)` | none | Yes | `standalone_owner_decision` | `787` | `792` | `4` |
| `D111` | `(w)` | none | Yes | `standalone_owner_decision` | `787` | `794` | `4` |
| `D113` | none | `(u)` | Yes | `standalone_owner_decision` | `776` | `780` | `3` |
| `D114` | `(c)`, `(d)` | none | Yes | `standalone_owner_decision` | `776` | `784` | `15` |
| `D115` | `(v)` | `(u)`, `(w)` | Yes | `standalone_owner_decision` | `765` | `766` | `4` |
| `D117` | `(x)` | none | Yes | `standalone_owner_decision` | `755` | `756` | `2` |
| `D118` | `(l)`, `(m)` | `(w)` | Yes | `standalone_owner_decision` | `755` | `762` | `3` |

## 4. Every Line of Amendment N1 Containing `[proposed]` (Line Number and First 200 Characters)

| # | Line Number | `[proposed]` Count on Line | Full Line Length | First 200 Characters (Exact) |
|---:|---:|---:|---:|---|
| 1 | `24` | `1` | `167` | `- **Values marked [proposed]** are the lead's choices. They take effect only through N1.8. Unmarked rules are the owner's decisions or the plan's own text, each cited.` |
| 2 | `110` | `1` | `145` | `- **Schema** [proposed]: the released 3.2.0 (content: D98, D99, D108), once it has merged and the native integration has been re-validated on it.` |
| 3 | `121` | `1` | `134` | `  - [proposed] The transcript-based receipt origin is the "receipt origin" that D107's D13 default pins: one measurement, named twice.` |
| 4 | `130` | `1` | `171` | ``   - [proposed] **every** live capture's terminal `modelUsage` limits must equal the registered limits. D117 names the first, and checking each one is the stricter reading. `` |
| 5 | `136` | `1` | `40` | `- **Auxiliary models** [proposed]: none.` |
| 6 | `150` | `1` | `227` | `  - [proposed] The pinned executable is a **durable copy** outside the auto-updater's path, so that an update inside the validity window can't change the pinned sha. This was the 2026-10-25 packet's s` |
| 7 | `159` | `2` | `455` | `\| **D13** \| The registration pins:<br>• the **toolchain exposure**, narrowed to the generation agents under D114 (#4019);<br>• the **tool allow-list**;<br>• [proposed] the **literal launch argv, recor` |
| 8 | `161` | `2` | `412` | `\| **D18** \| [proposed] D18's original subject, a time box for #4354's offline acceptance, is closed by this amendment.<br>[proposed] D18 now means a **two-week validity window** for the native registr` |
| 9 | `178` | `1` | `148` | `[proposed] **The row set.** Plan §5 defers the native rows to this amendment. These are taken from the plan and generation plan N10, not from #4354.` |
| 10 | `199` | `1` | `81` | `3. **Tool history**, generation plan N10 mapped to the typed protocol [proposed]:` |
| 11 | `205` | `1` | `193` | `4. **Clean.** The attempt is clean: an assisted attempt is evidence only and never accepted (D43; plan §1 item 1, §5 row 7, §10). [proposed] The native clean checks, with how each is evidenced:` |
| 12 | `233` | `1` | `284` | `  2. **The owner writes the statement of launch terms.** [proposed] This statement is what D110 and D111 mean by "the launch word states" and "confirms … in the launch word": the coded word's closed f` |
| 13 | `250` | `1` | `222` | `     - **[proposed] the seven-day utilisation is ≤ 0.50.** It's stricter than the sources' 0.80 because the window was exhausted on 2026-10-24, the 1M context spends faster, and a canary stopped by th` |
| 14 | `252` | `1` | `267` | ``      - **[proposed] both windows are allowed.** A nested window is allowed when its `utilization` is a finite JSON number, not a boolean, with 0 ≤ utilisation < 1, and its `resetsAt` is after both cap `` |
| 15 | `253` | `1` | `150` | ``      - **[proposed] a further window type is judged by the same rule when it carries `utilization`, and is recorded but not refused when it doesn't;** `` |
| 16 | `255` | `1` | `412` | ``      - **[proposed] One freshness rule with two values:** `captured_at` is no earlier than the word's `authorized_at`, and dispatch occurs within `max_age_seconds` = 300 of `captured_at`. 300 is the c `` |
| 17 | `256` | `1` | `322` | ``      - **[proposed] a margin at the reservation:** at the pre-reservation check, `captured_at + max_age_seconds − now` is at least 90 s. That covers what runs after the reservation and before dispatch `` |
| 18 | `265` | `1` | `245` | `  - [proposed] **After three failed captures,** the capture reservation refuses a fourth. The path is a new word for the same registration, if it's still within its validity window. A new word gets th` |
| 19 | `276` | `1` | `112` | ``   - [proposed] the registered keep-awake policy `macos_iokit_ims_v1` (idle, disk and system sleep), on AC power; `` |
| 20 | `277` | `1` | `158` | `  - [proposed] the operator holds the quiet-window lock for the attempt. That's a coordination protocol, not a controller gate, and not proof of a quiet host.` |
| 21 | `279` | `1` | `117` | `- **Deadline** [proposed]: 21,600 s (6 h) of wall time from dispatch. That's the sources' value, re-validated in D14.` |
| 22 | `287` | `1` | `152` | `  - [proposed] **The owner, as operator (D12),** may stop the attempt manually at any time, by the signal and cleanup procedure the launch packet names.` |
| 23 | `288` | `1` | `282` | `  - [proposed] **D107's stop rule is read as follows.** The usage limit is the live stop above. "any acceptance-row failure" is judged after the attempt on the saved result, because the rows are prope` |
| 24 | `341` | `1` | `41` | `- D71(a)'s schema, under N1.1 [proposed];` |
