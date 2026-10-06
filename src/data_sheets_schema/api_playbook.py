"""Frozen opt-in API instruction adaptation; historical renderers remain intact."""
from pathlib import Path
import hashlib

POLICY_PATH = Path("src/download/prompts/api_playbook_v1.md")
POLICY_SHA256 = "6870fd69c6ca377b6f6a349b0161f503ef742176228074db57325b7368db6015"


def policy_text(*, version: int = 1) -> str:
    """Fail closed on changed policy bytes, including during historical replay."""
    if type(version) is not int or version not in (1, 2, 3):
        raise ValueError("unsupported API playbook version")
    if version in (2, 3):
        from .shared_generation import captured_assets, API_POLICY, ROUTING_API_POLICY
        return captured_assets(version=version - 1)[API_POLICY if version == 2 else ROUTING_API_POLICY].decode("utf-8").split("## Prompt body", 1)[1].strip()
    from data_sheets_schema.resources import resource_path
    raw = resource_path(POLICY_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError("API playbook v1 policy differs from its frozen SHA256; use a new version")
    return raw.decode("utf-8").split("## Prompt body", 1)[1].strip()


def adapt_template(body: str, *, version: int = 1) -> str:
    """Adapt the registered base only, before substitutions or tuned evidence.

    Select explicit sections, never scrub user/bundle text. Refuse a changed
    template layout rather than accidentally retaining a filesystem directive
    or dropping a condition's decision rules. Original prompt files stay pinned.
    """
    markers = ("READ FIRST, IN THIS ORDER, AND FOLLOW EXACTLY:",
               "VERSION LABEL — use verbatim in every output path:",
               "OUTPUTS — do not write outside these three:",
               "HEADER BLOCK — use exactly:",
               "CORE HEADER BLOCK — use exactly", "AFTER Phase 4, write a LIVE provenance record:",
               "VALIDATE both files before finishing:", "ABSOLUTE CONSTRAINT —",
               "UNIFORM DECISION RULES —", "RETURN:")
    positions = []
    for marker in markers:
        if body.count(marker) != 1:
            raise ValueError(f"API playbook v1 cannot adapt prompt section {marker!r}")
        positions.append(body.index(marker))
    if positions != sorted(positions):
        raise ValueError("API playbook v1 cannot adapt reordered prompt sections")
    declarations = body[positions[1]:positions[2]].strip().replace(
        markers[1], "RUN VERSION LABEL:", 1)
    header = body[positions[3]:positions[4]].strip().replace(
        "# Generation Method: schema-grounded agentic, phase 1",
        "# Generation Method: schema-grounded API, full generation").replace(
        "# Mode: four-phase project agent,", "# Mode: API phase controller,")
    rules = body[positions[8]:positions[9]].strip()
    ending = body[positions[9]:].strip()
    if ending != ("RETURN: full slot count, core slot count, whether both validated, and the\n"
                   "reconciliation outcome. Return data, not prose."):
        raise ValueError("API playbook v1 cannot adapt changed completion instruction")
    return (policy_text(version=version) + "\n\n" + declarations + "\n\n" + header
            + "\n\n" + rules + "\n\nRETURN: follow only the final phase instruction's "
            "artifact format; the controller manages files and checks.\n")


def policy_identity(*, version: int = 1) -> dict:
    policy_text(version=version)
    if version == 1:
        return {"path": str(POLICY_PATH), "sha256": POLICY_SHA256}
    from .shared_generation import API_POLICY, ASSET_HASHES, ROUTING_API_POLICY, ROUTING_ASSET_HASHES
    path = API_POLICY if version == 2 else ROUTING_API_POLICY
    return {"path": path, "sha256": {**ASSET_HASHES, **ROUTING_ASSET_HASHES}[path]}
