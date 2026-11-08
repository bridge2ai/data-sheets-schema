"""Current-source verification and live evidence capture for C attribution.

This does not grant execution admission. Its outer caller must independently
obtain U3-D's full gate chain before any live operation.
"""
from __future__ import annotations

from . import native_shared_attribution as consumer
from . import native_shared_contract as c
from .native_shared_evidence import read_regular


class _LiveAttribution(consumer._Attribution):
    def _check_current(self, problems):
        try:
            full = read_regular(self._paths['full'], 'final_full', max_bytes=self._input_limit).captured
            report = read_regular(self._paths['report'], 'final_report', max_bytes=self._input_limit).captured
        except (TypeError, ValueError, KeyError, OSError) as exc:
            problems.append('current draft cannot be verified: ' + str(exc))
            return
        self._compare(problems, full.raw, report.raw, 'current captured')


def live(selection, *, execution_raw, spec, composition_raw):
    """Verify current preparation/C, then hand captured inputs to the observer."""
    from . import native_shared_controller_orchestration as controller
    consumer._joined(selection, execution_raw, spec, composition_raw)
    composition = c.strict_json(composition_raw, 'attribution composition', c.HARD_LIMITS['request_bytes'])
    fresh, fresh_spec, fresh_selection = controller.reconstruct_composition(composition_raw)
    consumer._need(c.canonical(fresh) == c.canonical(composition)
        and fresh_selection == selection
        and c.canonical(fresh_spec.render_spec()) == c.canonical(spec.render_spec()),
        'attribution current preparation differs from the supplied captured authority')
    return _LiveAttribution(selection, execution_raw=execution_raw, spec=spec,
                            composition_raw=composition_raw)
