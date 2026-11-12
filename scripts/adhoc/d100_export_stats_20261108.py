"""D100 / PR #5543 fix, 2026-11-08: refresh TSVs from repository stats.
Input: level-4 JSON from d4d schema stats, current merged schema.
Output: basic/extended data/schema_stats exports; curated RAI/property lists retained.
"""
import csv
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.claude/agents/scripts'))
import schema_stats_extended as extended

stats = json.loads(Path(sys.argv[1]).read_text())
schema_version = str(extended.SchemaView(str(extended.find_full_schema())).schema.version)
if str(stats['schema_version']) != schema_version:
    raise ValueError('Input statistics version differs from the repository schema')
# The legacy extended exporter resolves its output relative to cwd.
os.chdir(ROOT)
out = ROOT / 'data/schema_stats'
combined = []

def write(name, headers, rows, section):
    rows = list(rows)
    with (out / name).open('w', newline='') as handle:
        writer = csv.writer(handle, delimiter='\t', lineterminator='\n')
        writer.writerow(headers)
        writer.writerows(rows)
    if section == 'Level 3 Reuse':
        combined.extend([[section, row[1], row[2], 'classes'] for row in rows])
    elif section == 'Level 4 Quality':
        combined.extend([[section, row[0], row[2], f'{row[1]}: {row[3]}'] for row in rows])
    elif section != 'Level 4 Recommendations':
        combined.extend([[section, *row] for row in rows])

s = stats['summary']; c = stats['classes']; slots = stats['slots']; d = stats['detailed']; q = stats['quality']
write('level1_summary.tsv', ['Metric', 'Count'], [(k.replace('_', ' ').title(), v) for k, v in s.items()], 'Level 1')
write('level2_class_categories.tsv', ['Category', 'Count'], [('Abstract Classes', c['abstract_count']), ('Concrete Classes', c['concrete_count'])], 'Level 2')
write('level2_classes_by_module.tsv', ['Module', 'Class Count'], c['by_module'].items(), 'Level 2 Modules')
write('level2_slot_categories.tsv', ['Category', 'Count'], [(label, slots[key]) for label, key in [('Required Slots', 'required_count'), ('Optional Slots', 'optional_count'), ('Multivalued Slots', 'multivalued_count'), ('Single-valued Slots', 'single_valued_count'), ('Identifier Slots', 'identifier_count')]], 'Level 2 Slots')
write('level2_slots_by_range_type.tsv', ['Range Type', 'Slot Count'], slots['by_range'].items(), 'Level 2 Ranges')
write('level3_inheritance_depth.tsv', ['Depth Level', 'Class Count'], [(f'Depth {k}', v) for k, v in d['classes_by_depth'].items()] + [('Max Inheritance Depth', d['max_inheritance_depth'])], 'Level 3 Depth')
write('level3_top_reused_slots.tsv', ['Rank', 'Slot Name', 'Usage Count'], [(i, r['slot'], r['usage_count']) for i, r in enumerate(d['top_reused_slots'], 1)], 'Level 3 Reuse')
write('level4_quality_metrics.tsv', ['Quality Check', 'Status', 'Count', 'Examples'], [(k.replace('_', ' ').capitalize(), 'PASS' if not q[k] else ('WARNING' if k == 'single_use_slots' else 'ISSUE'), q[k], ', '.join(q['examples'][k]) or 'None') for k in q if k != 'examples'], 'Level 4 Quality')
# Preserve editorial recommendation wording, updating only measured counts.
path = out / 'level4_recommendations.tsv'
with path.open(newline='') as handle:
    rows = list(csv.reader(handle, delimiter='\t'))
recommendation_keys = {
    'slots without explicit range': 'slots_without_range',
    'orphaned classes': 'orphaned_classes',
    'single-use slots': 'single_use_slots',
}
seen_labels = set()
for row in rows[1:]:
    label = row[0].split(' ', 1)[1]
    assert label not in seen_labels, f'Duplicate recommendation label: {label}'
    seen_labels.add(label)
    row[0] = str(q[recommendation_keys[label]]) + ' ' + label
assert seen_labels == set(recommendation_keys), (
    f'Incomplete recommendation rows: {seen_labels} != {set(recommendation_keys)}'
)
write(path.name, rows[0], rows[1:], 'Level 4 Recommendations')
with (out / 'ALL_STATS_COMBINED.tsv').open('w', newline='') as handle:
    writer = csv.writer(handle, delimiter='\t', lineterminator='\n')
    writer.writerow(['SECTION', 'Metric', 'Value', 'Details'])
    writer.writerows(combined)
extended.main()
print('Refreshed basic and extended exports for schema', schema_version)
