"""The commands a native overlay allows, importable without running the preparer.

CLI subcommands (`<py> -m data_sheets_schema.cli <group> <command> *`) and the
module entry points the native instruction prescribes. `provenance backfill`
is mentioned by the playbook only to say a native run must not use it.
"""
PLAYBOOK_COMMANDS = ('agents playbook', 'agents digest', 'bundle chunk', 'download scope', 'download priority',
                     'download list-projects', 'receipts check', 'derive core', 'provenance record',
                     'provenance annotate-observed', 'provenance backfill-checks', 'runs check', 'runs validate',
                     'runs list', 'prompt render', 'api render-prompt', 'api prompts check', 'schema check-digest')
MODULE_ENTRY_POINTS = ('d4d_pair_consistency', 'agentic_observed', 'evidence_assertions', 'source_review')
MENTIONED_NOT_PRESCRIBED = ('provenance backfill',)
