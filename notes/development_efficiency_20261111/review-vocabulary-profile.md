The existing vocabulary snapshot race test relies on the ambient default manifest selecting Bridge2AI. In the sparse development worktree, the default source manifest is not materialized, so the neutral profile provides no vocabulary; the vocabulary parametrization fails with KeyError TEST before schema_snapshot is reached. The focused compatibility run retained26passes/1failure in0.753s. WP3 did not change the failing test, schema_digest.py, profiles.py or tests/conftest.py relative to001a80ee1a33b0bdd7eef8ec4d83e82823f8f096.

Make the vocabulary-specific fixture explicitly select its intended profile, preserving its real after-read replacement behavior. Keep this independent test portability issue separate from WP3 source acceptance and final D4D generation prerequisites. A one-node baseline reproduction and explicit Bridge2AI confirmation are being retained; do not rerun the26already-passing cases or copy the full corpus into a sparse checkout.

Issue: https://github.com/bridge2ai/data-sheets-schema/issues/5833

The main-based evidence branch now sets D4D_PROFILE=bridge2ai with the existing function-scoped monkeypatch inside the vocabulary-specific test. The original file replacement and assertions are unchanged. Independent read-only review found no issue; monkeypatch restores the incoming environment even after failure.

Validation deliberately supplied D4D_PROFILE=neutral to each pytest process. The vocabulary canary passed first (1test,1.100s), then the text parametrization passed (1test,1.539s), both with zero errors/failures/skips. Commands used the existing project Python, PYTHONPATH=src, -p no:cacheprovider, --maxfail=1, external /private/tmp/d4d-profile5833-{vocab,text} basetemp, and the exact test_vocabulary_replacement_after_hashing_cannot_poison_cache[vocabulary] or [text] selector. Logs and JUnit are retained under tmp/vocabulary-profile-5833/ in the lead worktree. No new test or runner was added.

- Reviewed test SHA256: 35befa7f122eacfd171bebe67080631b36a0761114bff0e441a2c309abf8f636
- vocabulary.xml SHA256: 03abaca925decd18b7f9be8f72acea1e9ea14e0978cc674c384e0f3326afde9f
- text.xml SHA256: bc9fd2ab194ed78a2b3b46e3d65e8f080cf26f78d56f6a6e03bf79354a5f8ef3
