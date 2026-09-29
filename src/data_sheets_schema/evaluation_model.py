"""The model that judges records, resolved in one place (#2928).

Five LLM instruments that score a D4D record — the support and fitness
scorers in `evidence_score`, the referent judge in `merge`, the equivalence
judge in `agreement`, the form-subtype classifier in `form_defects` — used to
fall back, when no model was passed, to `api_runner._model_settings()["name"]`:
the *generation* model. For those paths nothing separated "which model wrote
the records" from "which model judged them", so their support, fitness,
referent, equivalence and form-subtype judgements share the generator's
family. Rubric scores come by other routes: on the Claude-generated arms that
`arm_comparison` reports, every evaluation is same-family as well, while the
legacy gpt5-method rubric scores were judged cross-family.

This module is the seam. `evaluation_model_settings()` is what those five
paths ask when they were given no model, and it answers with a `basis` naming
where the answer came from. The API rubric judge
(`evaluation/evaluate_d4d_llm.py`) is not one of them: it never fell back to
the generation model and keeps its own pinned default (#3326). There is no evaluation config yet — where it lives
is an owner decision (#2928: `.github/workflows/` ships in the wheel, a YAML
under `src/data_sheets_schema/` enters future audit closures) — so today the
answer is the generation model, under the basis `defaults_to_generation_model`.
That is deliberately *exactly* the old resolution: a judge cache is scoped on
the model name (`JudgementContext`, #243), and a default that moved would make
every cached judgement fall out of scope (#351, #462).

`model_family()` and `same_family()` let a report state what it cannot yet
measure: whether the evaluator shares the generator's family. A family is read
off the model token, never the route: `google/claude-opus-5-high` is a Claude
model served on CBORG's `google/` route, not a Google model.
"""

from __future__ import annotations

import re
from typing import Any

BASIS_GENERATION_DEFAULT = "defaults_to_generation_model"

# The sentence a report comparing arms on judged scores carries until a
# cross-family second rating exists (#2928 acceptance criterion 4).
SAME_FAMILY_DISCLAIMER = (
    "Evaluator and generator are the same model family wherever the "
    "same-family column reads yes: self-preference is unmeasured, since no "
    "cross-family second rating of these scores exists yet (#2928).")


def evaluation_model_settings() -> dict[str, Any]:
    """The judge model to use when a caller passed none, and why.

    Returns `name`, `basis` and `generation_model`. Read at call time, never
    cached here: the generation config can be monkeypatched or edited within a
    process, and the old fallbacks read it at call time too.
    """
    from data_sheets_schema import api_runner
    generation = api_runner._model_settings()["name"]
    return {"name": generation, "basis": BASIS_GENERATION_DEFAULT,
            "generation_model": generation}


def evaluation_model_name() -> str:
    """`evaluation_model_settings()["name"]` — the form every fallback needs."""
    return evaluation_model_settings()["name"]


# Token prefixes, matched against each candidate model token (see `_tokens`).
# Ordered: the first match wins.
_FAMILIES: tuple[tuple[str, str], ...] = (
    ("claude", "claude"),
    ("gpt", "gpt"),
    ("chatgpt", "gpt"),
    ("o1", "gpt"),
    ("o3", "gpt"),
    ("o4", "gpt"),
    ("gemini", "gemini"),
    ("gemma", "gemini"),
    ("llama", "llama"),
    ("mistral", "mistral"),
    ("mixtral", "mistral"),
    ("command", "command"),
    ("deepseek", "deepseek"),
    ("qwen", "qwen"),
)


def _tokens(name: str) -> list[str]:
    """Candidate model tokens, rightmost first.

    A route (`google/…`) or provider (`openai:…`) prefix precedes the token;
    a Bedrock version (`…-v1:0`) follows it; so each `/`- or `:`-separated
    part is a candidate and the first that names a family wins.
    """
    text = re.sub(r"\[[^\]]*\]$", "", name.strip().lower())   # claude-opus-5[1m]
    parts = [p for p in re.split(r"[/:]", text) if p]
    return [p.split("anthropic.", 1)[1] if "anthropic." in p else p   # us.anthropic.…
            for p in reversed(parts)]


def model_family(name: str | None) -> str | None:
    """The model family a model identifier names, or None when unrecognised.

    `google/claude-opus-5-high`, `claude-opus-5[1m]`,
    `claude-sonnet-4-5-20250929` and `claude-fable-5` are all `claude`;
    `openai:gpt-5` is `gpt`. An unrecognised or empty name is None, never a
    guess: "unknown" and "different" are different claims.
    """
    if not name or not isinstance(name, str):
        return None
    for token in _tokens(name):
        for prefix, family in _FAMILIES:
            if re.match(rf"{re.escape(prefix)}(?![a-z])", token):
                return family
    return None


def same_family(evaluator: str | None, generator: str | None) -> bool | None:
    """Whether the evaluator and the generator are one model family.

    None when either family is unknown — a missing model block is not
    evidence of independence.
    """
    a, b = model_family(evaluator), model_family(generator)
    if a is None or b is None:
        return None
    return a == b


def same_family_label(evaluator: str | None, generator: str | None) -> str:
    """`yes` / `no` / `unknown`, for a report column."""
    verdict = same_family(evaluator, generator)
    return "unknown" if verdict is None else ("yes" if verdict else "no")
