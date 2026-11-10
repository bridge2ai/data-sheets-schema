Read-only review of commit `41e0d1c1330d52f4bee34d018a8a958fffb99315`, `scripts/adhoc/native_final_record_acceptance_20261110.py:77–78`, found that the advertised 30-second wrapper reserves only two seconds after its outer alarm for cleanup.

The inherited `d76_process_deadline_20261102.py:126–130` interruption path may inspect an owned process group after PermissionError. That inspection alone allows three seconds (`:37–38`), followed by possible reap and evidence writing. The one-shot outer alarm supplies no further bound. Thus the stated total cap is not guaranteed on that failure path.

The first receipt canary completed normally in 0.779 seconds; this is an independently identified failure-path defect, not a claim that that run timed out.

Fix the bounded diagnostic wrapper's cleanup allowance and timeout claim without widening native execution scope or weakening refusal when cleanup is unknown. Relates to existing deadline work in #5746 but concerns this newly added component-check wrapper. Affected new file is not yet on main.
