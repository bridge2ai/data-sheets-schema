# Declared evaluation cohorts

Evaluation audits and campaign review packs require an explicit
`evaluation_cohort_v1` YAML/JSON manifest. They have no default project roster,
version comparison, generation labels or replicate count.

```yaml
format: evaluation_cohort_v1
cells:
  - arm: comparison-a
    projects: [EXTERNAL]
    replicates: [2, 7]
    label_template: 'registered-series_rep{replicate}'
    method: claudecode_api
    condition: generic_v10
    input_arm: baseline
```

Each cell expands its explicitly listed projects and replicates into exact
labels. Only `{project}` and `{replicate}` substitution is supported. Multiple
cells can assign different labels to one comparison arm. Duplicate identities
are refused. The manifest's path, SHA256 and byte count are recorded in the
audit and the private review key.

For registered packages, the audit grouping arm must have a matching manifest
assignment for the bound project, label, method, condition and input arm.
The summary exposes the bound generation identity beside the grouping arm.

Use `scripts/audit_evaluation_comparability.py --roster-manifest FILE` and
`scripts/build_blind_review_pack.py --cohort-manifest FILE` with the other
explicit inputs shown in each command's help. The pack's existing `--manifest`
selects record paths; `--cohort-manifest` independently defines the expected
campaign membership. Synthetic packs need no campaign manifest.

The files in `configs/evaluation/legacy_bridge2ai_*.example.yaml` are named
historical examples, not defaults or declarations of an active campaign.

For registered evaluation, `--comparison-arm` declares the identity to blind.
The input-condition arm in the immutable generation registration has a different
role. The gate also checks the bound method and provenance condition, and
refuses leaked identifiers instead of editing scientific text.

The audit confines packages and records to `--root`. A repeatable
`--authority-root DIRECTORY` explicitly permits external pinned authorities,
such as generation registrations. These reads retain byte limits and snapshot
checks. The registration is never rewritten or relocated.
