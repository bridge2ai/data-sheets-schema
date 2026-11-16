"""Complete evidence descriptions in the launch-cost report, 2026-11-16.

Input/output: report generator on this branch. Corrects boundary order against
saved call stacks and includes the exact saved collection result.
"""
from pathlib import Path

path = Path(__file__).with_name('report_launch_cost_20261116.py')
text = path.read_text()
text = text.replace("'The original seven outer registration calls protect: public entry before profile/runtime/attempt selection; current capture authority selection; '\n        'the fixed generic engine before capabilities; the common launch body before authorization; unchanged execution/evidence before admission; '",
    "'The original seven outer registration calls protect, in order: public entry before profile/runtime/attempt selection; '\n        'the fixed generic engine before capabilities; the common launch body before authorization; current capture authority inspection; '\n        'unchanged execution/evidence before admission; '")
text = text.replace("'Collection evidence is preserved in collection.log; expected FAIRSCAPE submodule errors are not repaired by this helper.', '',",
    "'Collection: ' + next(line for line in (S / 'collection.log').read_text().splitlines() if 'tests collected,' in line) + '. '\n        'The three expected FAIRSCAPE submodule errors are not repaired by this helper.', '',")
path.write_text(text)
text = path.read_text().replace("'src/data_sheets_schema/native_environment_manifest.py', 'tests/test_native_environment_census.py']]",
    "'src/data_sheets_schema/native_environment_manifest.py', 'tests/test_native_environment_census.py',\n        'scripts/adhoc/finalize_launch_report_20261116.py']]")
path.write_text(text)
text = path.read_text()
text = text.replace("    metrics = {'capture_to_launch':", "    authority_span = next(row for row in data['profiles'] if row['phase'] == '_current_authority')\n    authority_light = sum(row['seconds'] for row in lights if authority_span['start'] <= row['time'] <= authority_span['end'])\n    projected_authority = authority_span['seconds'] - authority_light * (1 - factor)\n    metrics = {'capture_to_launch':")
text = text.replace("'profiles': profiles}", "'profiles': profiles, 'conditional_capture_before_reservation': projected_prefix + projected_authority}")
text = text.replace("'the lead needs a committed candidate and fresh end-to-end measurement. The two-second target and freshness closure remain open.', '',", "'the lead needs a committed candidate and fresh end-to-end measurement. '\n        f'If the unreached second current-authority check costs the same as the modeled reached check, the projected age is already '\n        f'{projected_prefix + projected_authority:.3f} seconds before reservation, with dispatch work still excluded. '\n        'This conditional scenario exceeds the freshness limit; it is not an observed result. The two-second target and freshness closure remain open.', '',")
text = text.replace("'No census result is reused across calls. '", "'No census result is reused across calls. '")
text = text.replace("'The ancestor-count witness observes the syscall rather than the former Path method and keeps the same assertions.', '',", "'The ancestor-count witness observes the syscall rather than the former Path method and keeps the same assertions. '\n        'The local census canary accepted the same saved manifest before and after. Aggregate stat/lstat and hashing-call counts are identical, '\n        'as recorded in metrics.json; this does not exercise all concurrent mutation schedules or establish launch freshness.', '',")
path.write_text(text)
