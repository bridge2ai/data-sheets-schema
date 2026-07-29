# CHORUS — GC-specific prompt components

## fact

The CHORUS document bundle is **substantially thinner than the other three
projects'** — roughly 36 KB against 322–421 KB. This is a property of the input
sheet, not of the project: column E populates only a NIH RePORTER project page,
a cohort-2 webinar, a project website, and one curated GitHub organization
overview. The sheet carries no publication, license, IRB, or DUA row for CHORUS
where it does for the others.

Absent evidence here means absent from the sheet, not absent upstream. Report
what the bundle supports and leave the rest unpopulated; do not compensate for
the corpus being thin.

---

**No `decision-rule` component.** CHORUS's 2026-07-27 prompt carried "prefer
omission over inference", and removing it cost 12 points of three-way agreement
(84.2% → 72.3%). That rule was not CHORUS-specific in substance, only in
application, so it now sits in the generic base and applies to every project.
Restoring it here would double-state a uniform rule and reintroduce the
asymmetry that made it look like tuning.

**No `referent-pin` component.** CHORUS has one referent — a single data
manifest release — and the unpinned runs did not disagree about it.
