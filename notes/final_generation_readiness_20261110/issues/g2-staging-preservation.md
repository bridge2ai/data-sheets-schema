Read-only review of G2's prepared `scripts/adhoc/g2_collection_type_release_20261110.py` found that lines 141–143 delete an existing staging directory with `shutil.rmtree` before a run.

That loses the prior attempt's artifacts, conflicting with this task's requirement to preserve failed evidence. No execution or deletion has occurred in the reviewed task.

Require a fresh output/staging directory or refuse if it already exists. Retain any failed attempt and use a new explicit path for a retry. Do not add cleanup or worktree deletion to this helper.
