# CHORUS native audit history and retry policy — September 21, 2026

The nine CHORUS audit continuations did not produce an accepted Phase 3 audit. Their stopped evidence remains preserved. Audit9 wrote six native output parts, but never assembled or validated a final audit. It stopped on a token-counting timeout after all 26 paid requests had settled; that does not show that its longer generation read timeout expired.

The nine continuations account for $45.34993425 across 145 admitted requests. The table separates the amount charged against the budget from the treatment of each interrupted request; attempt totals include the other settled requests.

| Audit | Requests | Attempt budget accounting (USD) | Interrupted-request treatment (USD) |
| --- | ---: | ---: | --- |
| 1 | 5 | 1.29882575 | User-confirmed complete charge: 0.08634550 |
| 2 | 5 | 1.29389825 | User-confirmed complete charge: 0.08502850 |
| 3 | 5 | 1.30046725 | User-confirmed complete charge: 0.08503800 |
| 4 | 32 | 10.57582425 | Full-reservation debit: 3.14805000 |
| 5 | 1 | 2.54055000 | Full-reservation debit: 2.54055000 |
| 6 | 9 | 5.09030175 | Full-reservation debit: 2.77563125 |
| 7 | 39 | 11.39397075 | Full-reservation debit: 2.29371250 |
| 8 | 23 | 7.24842875 | Full-reservation debit: 2.51600000 |
| 9 | 26 | 4.60766750 | All requests settled; no reconciliation needed |

The five full-reservation debits total $13.27394375. Each had request-specific authorization, retained the actual provider fee as unknown, and released no reserved funds. They are conservative budget debits, not confirmed provider charges. Across the full shared lineage, including work before these nine continuations, $158.23539350 is accounted against the $400 allocation, leaving $241.76460650.

[PR #2151](https://github.com/bridge2ai/data-sheets-schema/pull/2151) adds an optional registered audit policy that retries eligible token-count failures and permits a bounded number of full-reservation debits for eligible paid-request stalls before any response byte reaches the native client. The debit allowance requires explicit recorded authorization. Failures after response bytes have been relayed, errors with a known provider status below 500, failures to establish a connection, closed admission, budget refusals and an exhausted allowance remain terminal. Existing registrations retain their behavior; generation, Phase 4 and evaluations do not inherit the policy.

The [retained offline probe](native_stall_policy_probe_2026-09-21.json) records the pinned native client recovering from two scripted stalls and one counting timeout, with no provider requests. The record identifies the exact code and executable used. This supports the retry mechanism under those synthetic conditions; it does not establish real-provider reliability or how many requests a complete audit requires. The historical interruptions had different mechanisms, including an audit6 exit whose cause remained unproved, so these observations do not justify a completion-probability estimate.

The previous audit10 registration remains unlaunched and frozen. The maintainer approved a new condition with three token-count tries, at most six authorized full-reservation stall debits, a $40 attempt cap, a 20-minute read limit, a one-hour native SDK timeout and a six-hour job deadline. The shared allocation remains $400. A fresh registration must bind the reviewed merged code and those limits before launch. Scientific acceptance is still pending, and Kids First remains waiting.

The policy's [transport controls](matched_cborg_2026-09-13/audit_controls/README.md) use cancellable I/O workers to enforce a total deadline for each count and for receiving paid-response headers. The parent retains all accounting and evidence ownership. Local worker failures are terminal and cannot spend the provider-stall allowance. Slow-response, cleanup and error-classification tests run against synthetic local services. These checks establish the local controls; they do not establish real-provider reliability or accept a scientific result.
