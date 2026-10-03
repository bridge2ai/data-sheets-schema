# Offline native attribution saved-trace replay

`data_sheets_schema.native_attribution_results` checks an explicitly selected callback composition and its saved native transcript/control stream. It uses the same composed command policy for executed commands, callback decisions and permission denials. It never starts a child process or calls a provider.

```sh
python -m data_sheets_schema.native_attribution_results \
  --composition /absolute/path/composition.json \
  --transcript /absolute/path/attempt/transcript.jsonl \
  --control /absolute/path/attempt/control.jsonl \
  --out /separate/new/path/replay.json
```

Use `--config-root` only when the trace contains native persisted tool output. The reader accepts only the exact session/tool-results path grammar; it does not read arbitrary configuration files. The output destination must be new, outside the retained attempt and registered output directories, and must not alias any captured input, including through a hard link or symlink. Omitting `--out` prints the result without publishing a file. Exit status is 0 for a passed additional gate, 1 for checked failure, and 2 for unusable input or publication failure.

## Authority and captured evidence

Version 1 requires current code authority. It reconstructs the supplied composition and registration, checks exact source/policy/interpreter/instruction pins and captures raw transcript/control, selected inputs, prompt/controller sources, metadata, records, report, originals and audit. Raw hashes bind replay inputs; they do not authenticate a provider. An old trace pinned to another source HEAD or package closure refuses, even when its outer hashes are updated. This version does not supply an archived-authority override or silently upgrade a registration.

The capture stage checks current bytes with the real attribution and evidence-checker primitives. Once sealed, semantic replay uses only captured bytes and metadata. Publication separately rechecks the inputs and aliases for changes. The report records raw file hashes/lengths/roles, the embedded registration identity, composition and authority pins, captured aliases, alias symlink metadata and current file metadata. Metadata describes the capture time and cannot establish historical intermediate file contents.

Ordered replay preserves pending calls, mutation epochs, report-only correction, finite draft checks, terminal failures and exact final-recorder ordering. A separate lifecycle check requires one successful initialization before tools and rejects cancelled callbacks, extra/error/late initialization responses and unknown control frames. A completed recorder must still be a regular, non-symlink, single-link file according to captured current metadata; no absent historical fingerprint is invented. An earlier draft pass superseded by a report correction remains an unverified historical observation; the final current successful pass is recomputed against captured saved bytes. Failed, stopped, partial or malformed histories cannot become successful merely because current files pass a checker.

The bounded file/control replay is versioned here so frozen controller helpers retain their old APIs and bytes. Tests compare legacy command, denial and ordered-control outputs, including failures and denials. The shared state only gains overridable path and command resolution hooks; its existing defaults remain unchanged.

## Meaning of a passed result

`additional_gate_passed` covers the selected attribution, command/control, denial and current final-evidence checks. `generation_acceptance` is always `not_assessed`. Complete generation history, schema/pair/receipt acceptance, usage accounting, native permission proof, scientific support and launch authorization remain separate requirements. A replay report never resumes an attempt, rewrites a result receipt or grants permission to run a new condition.

Neutral fixtures and callback traces are engineering checks, not empirical calibration. Parent issues #2427 and #3336 remain open for the registered runtime and scientific work. Historical controllers, registrations, held audit28 artifacts and paid attempts are unchanged.
