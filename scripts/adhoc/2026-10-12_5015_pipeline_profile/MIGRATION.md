# Retained pipeline profiler

Purpose: reproduce the measured #5015 long-node attribution. Date: 2026-10-12. Related issue: bridge2ai/data-sheets-schema#5015; no PR yet.

Original source: `/private/tmp/d4d-agent-performance-20261012-vq8rgbu9/implementation/profiling/d4d_target_profile.py`. The migrated script adds only a documentation header; executable AST and embedded target list are unchanged. Original README is retained verbatim as historical invocation evidence. Original and migrated SHA-256 values are recorded in the companion migration manifest.

The original invocation's profiler-directory PYTHONPATH entry must point to this script's containing directory if using the retained copy. The ordinary owned checkout `src` entry and exact node, serial gate, optional output argument, external output path, source-origin checks and restoration logic remain unchanged. No execution or new profiling result is claimed by this migration. Root owns all project runtime.
