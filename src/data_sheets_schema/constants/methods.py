"""D4D generation methods constants.

This module centralizes the various methods used for generating D4D datasheets.
"""

# D4D generation methods
METHODS = [
    "curated",                  # Hand-curated reference datasheets
    "gpt5",                     # GPT-5 generated
    "claudecode",               # Claude Code deterministic (legacy API-based)
    "claudecode_agent",         # Claude Code agent (current - v5+)
    "claudecode_agent_core",    # Claude Code agent — D4D Core schema (exchange layer)
    "claudecode_assistant"      # Claude Code assistant (interactive)
]

# Current recommended method
CURRENT_METHOD = "claudecode_agent"

# Legacy methods (for backward compatibility)
LEGACY_METHODS = ["claudecode"]

# API-based methods (require API keys)
API_METHODS = ["gpt5", "claudecode"]

# Interactive methods
INTERACTIVE_METHODS = ["claudecode_agent", "claudecode_assistant"]

# Reference methods (not generated)
REFERENCE_METHODS = ["curated"]
