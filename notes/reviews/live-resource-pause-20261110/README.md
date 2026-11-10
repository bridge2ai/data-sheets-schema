# Owner-authorized temporary process pause

On 2026-11-10 UTC, the owner explicitly approved temporarily pausing the busy
PFASCommunityAgents Python worker group and CultureBotAI website Python job
while D4D secured its diagnostic evidence. The lead verified PID, process start
time, process group and working directory before sending SIGSTOP. The website
job was paused and verified first, then the PFAS controller and Python workers.
No process was terminated and no artifact was deleted.

- Website: PID 92782, process group 89865; see `website.json`.
- PFAS: controller PID 92016, process group 91896, 14 Python processes in total;
  see `pfas.json`. The parent git/just/uv processes were not signaled.
- Verification: every targeted process had a stopped (`T`) state.
- Immediately afterward: free space 2.4 GiB; load averages 26.64/39.28/31.53.
  These observations do not establish which job caused the earlier disk loss.

The native U3-M diagnostic had already failed to save terminal artifacts due to
ENOSPC. The pause does not rehabilitate that run. Its configuration restoration
and explicit resource-aborted report remain the immediate recovery priority.

## Resume

From this documentation worktree, use the saved identity-checking helper:

```bash
/usr/bin/python3 -B scripts/adhoc/pause_contending_jobs_20261110.py resume website
/usr/bin/python3 -B scripts/adhoc/pause_contending_jobs_20261110.py resume pfas
```

Resume is part of this temporary intervention, after the D4D recovery checkpoint
is safely saved. The helper refuses reused identities and records resumption in
the journals. If a process has exited, inspect the journal and current process
table rather than guessing a replacement PID. The recorded wall-clock pause
must remain visible when interpreting affected jobs' timings.

## Recovery completed

The final U3-M report was atomically published at 05:36 UTC and independently
verified against SHA-256
`e994010eae8c965a8d8bf746f969aac4f8853b103efb1bad49256789e04098dd`.
The private configurations were restored and the report retains the diagnostic
as resource-aborted with freshness unknown.

The lead resumed the website process at 05:38:02 UTC and the 14 PFAS processes
at 05:38:05 UTC using the identity-checking helper. A subsequent process-table
read verified that all 15 recorded PIDs were present and none had a stopped
state. Both JSON journals contain their resumption timestamps. No termination
or deletion occurred. Disk space remained volatile, so the recovery does not
authorize new expensive D4D validation runs.
