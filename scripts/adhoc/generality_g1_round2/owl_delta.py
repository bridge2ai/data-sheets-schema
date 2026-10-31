# Purpose: G1 review (F6) - RDF-level delta of project/owl/data_sheets_schema.owl.ttl
# between base and head (serialization churn vs semantic change).
# Inputs: argv[1] base TTL, argv[2] head TTL. Output: triple counts and the delta.
# Reviewer helper, generality G1 review (0ba88ba12), 2026-10-29.
import sys
from rdflib import Graph
from rdflib.compare import to_isomorphic, graph_diff
a, b = Graph().parse(sys.argv[1], format='turtle'), Graph().parse(sys.argv[2], format='turtle')
both, only_a, only_b = graph_diff(to_isomorphic(a), to_isomorphic(b))
print('triples base', len(a), 'head', len(b), 'common', len(both))
for t in sorted(only_a): print('  - ', [str(x)[:110] for x in t])
for t in sorted(only_b): print('  + ', [str(x)[:110] for x in t])
