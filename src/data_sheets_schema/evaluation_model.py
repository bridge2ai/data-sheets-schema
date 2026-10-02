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
the generation model and deliberately keeps its own pinned default (#3326).
`evaluation_config.yaml` beside this module ships with `model: null`, preserving
that generation default. A nonempty model name selects a different evaluator
without editing generation settings. Selection metadata is disclosure, not part
of judge cache identity: the model and the existing instrument keys remain the
cache boundary. No historical cache entry is rewritten.

`model_family()` and `same_family()` let a report state what it cannot yet
measure: whether the evaluator shares the generator's family. A family is read
off the model token, never the route: `google/claude-opus-5-high` is a Claude
model served on CBORG's `google/` route, not a Google model.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from typing import Any

import yaml

BASIS_GENERATION_DEFAULT = "defaults_to_generation_model"
CONFIG_PATH = Path(__file__).with_name("evaluation_config.yaml")

# The sentence a report comparing arms on judged scores carries until a
# cross-family second rating exists (#2928 acceptance criterion 4).
SAME_FAMILY_DISCLAIMER = (
    "Evaluator and generator are the same model family wherever the "
    "same-family column reads yes: self-preference is unmeasured, since no "
    "cross-family second rating of these scores exists yet (#2928).")


def evaluation_model_settings(*, config_path: Path | None = None) -> dict[str, Any]:
    """Resolve the packaged configuration at call time, without a provider.

    The config follows the imported implementation, not the working directory.
    Missing, malformed or unknown settings fail before a judge call. Explicit
    caller models use ``model_selection`` and need not read a default config.
    """
    from data_sheets_schema import api_runner
    from data_sheets_schema.duplicate_keys import find_duplicate_keys
    path = Path(config_path) if config_path is not None else CONFIG_PATH
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    if find_duplicate_keys(text, strict=True):
        raise ValueError("evaluation config has duplicate keys")
    config = yaml.safe_load(text)
    if (not isinstance(config, dict) or set(config) != {"version", "model"}
            or type(config["version"]) is not int or config["version"] != 1):
        raise ValueError("evaluation config requires version: 1 and model")
    selected = config["model"]
    if selected is not None and (not isinstance(selected, str) or not selected.strip()
                                 or selected != selected.strip()):
        raise ValueError("evaluation model must be null or a nonempty trimmed identifier")
    generation = api_runner._model_settings()["name"]
    return {"name": generation if selected is None else selected,
            "basis": BASIS_GENERATION_DEFAULT if selected is None else "evaluation_config",
            "generation_model": generation,
            "configuration": {"path": "src/data_sheets_schema/evaluation_config.yaml"
                              if config_path is None else str(path),
                              "sha256": hashlib.sha256(raw).hexdigest(), "version": 1}}


def model_selection(model: str | None) -> dict[str, Any]:
    """Bind one selection for a judge, retaining an explicit override's basis."""
    if model is None:
        return evaluation_model_settings()
    if not isinstance(model, str) or not model.strip() or model != model.strip():
        raise ValueError("explicit evaluation model must be a nonempty trimmed identifier")
    return {"name": model, "basis": "explicit_override"}


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
