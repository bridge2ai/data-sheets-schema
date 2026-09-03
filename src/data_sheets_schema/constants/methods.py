"""D4D generation methods constants.

This module centralizes the various methods used for generating D4D datasheets.
"""

# D4D generation methods
METHODS = [
    # Despite the name, these were NOT hand-curated. They were produced through
    # a ChatGPT chat interface by pasting in the prompt, schema and input docs,
    # which makes this a generation arm like any other. The identifier is kept
    # because published URLs and rendered output already use it; see
    # CURATED_PROVENANCE_NOTE below and issue #177.
    "curated",                  # ChatGPT chat interface (see note below)
    "gpt5",                     # GPT-5 generated
    "claudecode",               # Claude Code deterministic (legacy API-based)
    "claudecode_agent",         # Claude Code agent (current - v5+); API-runtime baseline runs up to v7 also live here (#690)
    "claudecode_agent_core",    # Claude Code agent — D4D Core schema (exchange layer)
    "claudecode_api",           # Claude API runtime, baseline arm, from generic_v8 on (#690, v8 plan D6)
    "claudecode_api_core",      # ... its D4D Core counterpart
    "claudecode_assistant",     # Claude Code assistant (interactive)
    "rocrate_mapped",           # RO-Crate via UPSTREAM's ro-crate-linkml.yaml, no model
    "rocrate_static_map",       # RO-Crate via OUR mapping table, no model
    "claudecode_agent_crate",   # Claude Code agent, crate-augmented evidence
    "claudecode_agent_crate_core",  # ... its D4D Core counterpart
    "claudecode_agent_healthsheet",  # AI-READI only: healthsheet as sole input
    "claudecode_agent_healthsheet_core",  # ... its D4D Core counterpart
    "claudecode_agent_crate_only",   # crate as sole input (no documents)
    "claudecode_agent_crate_only_core",  # ... its D4D Core counterpart
]

# Current recommended method
CURRENT_METHOD = "claudecode_agent"

# Legacy methods (for backward compatibility)
LEGACY_METHODS = ["claudecode"]

# API-based methods (require API keys)
API_METHODS = ["gpt5", "claudecode"]

# Interactive methods
INTERACTIVE_METHODS = ["claudecode_agent", "claudecode_assistant"]

# Reference methods — records not produced by a generation run, usable as
# ground truth.
#
# Deliberately empty. `curated` was listed here, which asserted programmatically
# that a ChatGPT-chat arm was the reference; anything scoring or validating
# against REFERENCE_METHODS would have treated it as truth. Nothing in the repo
# currently earns this tier: every D4D record present was produced by some
# generator. Leave it empty until something does.
REFERENCE_METHODS: list[str] = []

# What the `curated` records actually are, recorded here because the files
# themselves carry no provenance headers at all.
CURATED_PROVENANCE_NOTE = (
    "Generated through a ChatGPT chat interface by pasting in the prompt, "
    "schema and input documents. Not hand-curated and not a reference. The "
    "records also document superseded releases — AI-READI v2.0.0 (1,067 "
    "participants), VOICE v2.0 (442 participants), CM4AI B35XWX v1.4 — so "
    "they are not comparable to records generated from the current corpus, "
    "which describes AI-READI v3.0.0, VOICE 3.1.0 (833 participants) and "
    "CM4AI HIGT4C. There is no CHORUS record. See issue #177."
)


# ---------------------------------------------------------------------------
# RO-Crate contribution experiment
# ---------------------------------------------------------------------------
# Three arms measuring what upstream RO-Crate packages add to a D4D record.
# The two with-crate forks must consume *different* inputs, or they collapse
# into the same measurement: the deterministic fork maps an already-D4D-shaped
# rendering, so feeding that same rendering to the de novo fork would test
# transcription rather than extraction.

GENERATION_ARMS = {
    "baseline": {
        "method": "claudecode_agent",
        "core_method": "claudecode_agent_core",
        "input": "data/preprocessed/concatenated/{project}_preprocessed.txt",
        "model_involved": True,
        "measures": "what the document corpus alone supports",
    },
    "deterministic_upstream": {
        "method": "rocrate_mapped",
        "core_method": None,
        "input": "data/ro-crate_packages/{project}/processed/{project}_crate_d4d.yaml",
        "model_involved": False,
        "requires": "an upstream ro-crate-linkml.yaml (absent for VOICE)",
        "measures": "fidelity of UPSTREAM's crate-to-D4D mapping, repaired only "
                    "as far as schema validity requires",
    },
    "deterministic_ours": {
        "method": "rocrate_static_map",
        "core_method": None,
        "input": "data/ro-crate_packages/{project}/processed/{project}_crate_mapped_d4d.yaml",
        "model_involved": False,
        "requires": "ro-crate-metadata.json only, which every crate has",
        "measures": "fidelity of OUR mapping table; every filled field carries "
                    "its declared SKOS mapping type and information loss",
    },
    # AI-READI only. It is the sole GC publishing a Healthsheet, so this arm
    # cannot be run elsewhere and must never be pooled with the others. The
    # healthsheet also remains in AI-READI's standard corpus: the corpus
    # reflects what upstream actually publishes rather than a levelled set.
    "healthsheet_only": {
        "method": "claudecode_agent_healthsheet",
        "core_method": "claudecode_agent_healthsheet_core",
        "input": "data/preprocessed/concatenated/{project}_healthsheet_only.txt",
        "model_involved": True,
        "projects": ["AI_READI"],
        "measures": "what one structured upstream source yields alone, with no "
                    "publications, documentation, license or protocol",
    },
    # The crate-arm counterpart to healthsheet_only: one structured upstream
    # source, no documents. Answers "how much of a datasheet can the crate
    # support alone?" — distinct from de_novo, which asks what the crate adds
    # to documents.
    "crate_only": {
        "method": "claudecode_agent_crate_only",
        "core_method": "claudecode_agent_crate_only_core",
        "input": "data/preprocessed/concatenated/{project}_crate_only.txt",
        "model_involved": True,
        "projects": ["CHORUS", "CM4AI", "VOICE"],
        "measures": "what one RO-Crate supports on its own, with no documents",
    },
    "de_novo": {
        "method": "claudecode_agent_crate",
        "core_method": "claudecode_agent_crate_core",
        "input": "data/preprocessed/concatenated/{project}_preprocessed_with_crate.txt",
        "model_involved": True,
        "measures": "extraction — what an agent recovers from documents plus "
                    "crate evidence",
    },
}

# Arms whose outputs come from a model and therefore vary between runs.
STOCHASTIC_ARMS = [k for k, v in GENERATION_ARMS.items() if v["model_involved"]]
