"""Input-only execution identities shared by D consumers and orchestration.

Admission, actuation, signal handling and saved authority verification live in
native_execution_orchestration. No consumer imports that orchestration module.
"""
GATES = ('terminal', 'shutdown', 'first_stop', 'live_attribution', 'saved_attribution',
         'phase_history', 'tool_history', 'schema', 'pair', 'receipts', 'evidence',
         'observation', 'accounting', 'runtime_authority', 'keep_awake')
UNASSESSED = {'scientific_acceptance': 'not_assessed', 'provider_billing': 'not_verified',
              'evidence_authentication': 'not_cryptographically_authenticated'}
