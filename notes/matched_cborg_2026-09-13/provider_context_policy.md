# Registered provider context policy

CBORG documents default structural compression of tool results and a request
header for bypassing it. See its [Headroom documentation](https://cborg.lbl.gov/headroom_compression/),
read on 2026-09-15. This motivated #1851; it does not establish that a particular
historical request was compressed or explain the interrupted streams in #1849.

New executable registrations select `provider_context_policy: headroom_bypass_v1`.
The API SDK and native transport send `x-headroom-bypass: true`. The same policy
applies to token counting, including the native CLI's separate counting endpoint
and admission counts. Native forwarding sets this header from the registration;
a child-supplied header cannot change it. Request bodies remain unchanged.

Launch receipts record the selected policy and requested non-secret headers.
Native request-protocol evidence also records the forwarded header. These
records establish the requested control, not independently observed provider
behavior. No claim is made about effective provider-side token transformations.

Historical registrations without the field retain their original transport.
An explicit null, unknown policy, arbitrary header, or native counting/forwarding
mismatch fails before generation. Frozen registrations and active attempts are
never edited. A new reviewed registration and fresh admission checks are required
before applying the policy to a scientific attempt.
