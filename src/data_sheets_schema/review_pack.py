"""The review pack: what a reviewer of a generated record needs, assembled
deterministically from the record's own provenance (#787).

The receipt validator (#708) is deterministic and leaves three questions to
judgement — whether a `nothing_relevant` chunk truly held nothing, whether a
verbatim snippet supports the value under it, whether the value is the right
reading of the passage — and a fourth no rubric can ask without the rule
text: whether the record followed the instruction it was sent. A pack turns
"review this record" into a fixed list of items, each with a pointer (chunk
id and line span, or slot path with its cited chunk and snippet), so the
review is specific, samplable, and checkable afterwards (`review_check`).

Everything comes from the provenance record: the instruction is
`prompts.request` (its text is re-rendered from the spec, or read from the
launcher's file when given), the bundle is `inputs.bundle_path`, the manifest
is `inputs.chunks`, the receipts are beside the core record. The sample is
seeded by the record's request hash, so two reviewers of one record see the
same items.
"""
from __future__ import annotations

import hashlib
import random
import re
from pathlib import Path
from typing import Any

import yaml
from data_sheets_schema.schema_view import shared_view


class UnreadableYAML(yaml.YAMLError):
    """A file the pack reads would not parse — named, because the pack
    reads several (the record, the full record, the receipt, the manifest)
    and PyYAML's mark names the string it was handed, not the file (#1124
    round 5)."""

    def __init__(self, path: Path, exc: yaml.YAMLError):
        super().__init__(f"{path} could not be read as YAML: {exc}")
        self.path = path


def _load_yaml(path: Path, text: str | None = None) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8") if text is None else text) or {}
    except yaml.YAMLError as exc:
        raise UnreadableYAML(path, exc) from exc

#: The closed verdict vocabulary a review must use, per item kind.
VERDICTS = {
    "chunk_nothing_relevant": ("confirmed", "missed_content", "cannot_tell"),
    # `weak`: the snippet is verbatim and the passage is real, but it does
    # not answer the slot's question (a bare repository name receipting a
    # de-identification method) — #793.
    "slot_receipted": ("supported", "weak", "misread", "unsupported", "cannot_tell"),
    # `inferred`: no passage states it; it follows from stated lines. The
    # rules say such a value is an inference the record should not carry,
    # so it is adverse, but it is not the same finding as a fabrication.
    "slot_receiptless": ("bundle_supports", "inferred", "not_in_bundle", "exempt_by_nature", "cannot_tell"),
    "slot_reshaped": ("still_supported", "changed_meaning", "cannot_tell"),
    "rule": ("followed", "violated", "not_applicable", "cannot_tell"),
    # A `semantic-review-required` pair warning (#691): the deterministic
    # checker matched related full/core content and cannot judge whether the
    # relation holds semantically. `consistent`: the matched content says the
    # same thing; `divergent`: it does not, with paths and what differs.
    "pair_warning": ("consistent", "divergent", "cannot_tell"),
}
#: The verdicts that count against the record, per kind — derived, so a
#: verdict added above cannot be silently uncounted (#792).
AFFIRMATIVE = {"confirmed", "supported", "bundle_supports", "exempt_by_nature", "still_supported",
               "followed", "not_applicable", "consistent"}
ADVERSE = {k: tuple(v for v in vs if v not in AFFIRMATIVE and v != "cannot_tell") for k, vs in VERDICTS.items()}
def _anchored(rel: Path) -> Path:
    """cwd-proof (#822): a relative repo path resolved against the package
    root, so pack content cannot depend on the launch directory."""
    return rel if rel.is_absolute() else Path(__file__).resolve().parents[2] / rel


PAIR_SCHEMAS = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml",
                "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml")
SCHEMA_FILES = ("src/data_sheets_schema/schema/data_sheets_schema_all.yaml (class Dataset; slot descriptions)",
                "src/data_sheets_schema/schema/data_sheets_schema_core_all.yaml (class CoreDataset)")
#: What a reviewer cannot resolve from the pack alone is its own verdict, not
#: a pass: the pack reports how many, like UNMEASURABLE.
CANNOT_TELL = "cannot_tell"

DEFAULT_SAMPLE = {"receipted_slots": 25, "receiptless_slots": 25, "reshaped_slots": 25}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_paths(provenance: Path) -> dict[str, Path]:
    from data_sheets_schema.backfill_checks import record_paths as _rp
    p = _rp(provenance)
    core_dir = provenance.parent
    p["receipt"] = core_dir / f"{p['project']}_coverage_receipt.yaml"
    p["claims"] = core_dir / f"{p['project']}_receipts.yaml"
    p["review"] = core_dir / f"{p['project']}_review.yaml"
    p["pack"] = core_dir / f"{p['project']}_review_pack.yaml"
    p["review_b"] = core_dir / f"{p['project']}_review_b.yaml"
    p["instruction"] = core_dir / f"{p['project']}_review_instruction.md"
    return p


def instruction_text(record: dict[str, Any], instruction_file: Path | None) -> tuple[str | None, str]:
    """(text, basis). The launcher's file when given and its hash matches the
    record; else re-rendered from the recorded spec; else None."""
    req = ((record.get("prompts") or {}).get("request")) or {}
    want = req.get("sha256")
    if instruction_file is not None and instruction_file.exists():
        text = instruction_file.read_text(encoding="utf-8")
        got = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if want and got == want:
            return text, f"file {instruction_file} (sha256 matches the record)"
        return text, f"file {instruction_file} (sha256 does NOT match the record's request)"
    spec = req.get("spec")
    if isinstance(spec, dict) and spec.get("condition"):
        try:
            from data_sheets_schema.api_runner import RunSpec, resolve_prompt
            run = record.get("run") or {}
            s = RunSpec(project=run.get("project"), arm=spec.get("arm", ""), method=run.get("method", "claudecode_agent"),
                        bundle=Path(spec.get("bundle", "")), label=run.get("label", ""),
                        condition=spec["condition"], manifest_line=spec.get("manifest_line", ""),
                        run_date=spec.get("run_date", ""), runtime=spec.get("runtime", ""),
                        provider=spec.get("provider"))
            text = resolve_prompt(s)
            got = hashlib.sha256(text.encode("utf-8")).hexdigest()
            return text, ("re-rendered from the recorded spec (sha256 matches)" if got == want
                          else "re-rendered from the recorded spec (sha256 does NOT match — the prompt file has moved)")
        except Exception as exc:                                     # noqa: BLE001
            return None, f"could not re-render: {exc}"
    return None, "no instruction recoverable: the record has no spec and no file was given"


def rules_from(instruction: str) -> list[dict[str, str]]:
    """The instruction's rule bullets, each a checklist item. Bullets under
    the uniform rules and every `ADDED IN vN` block; continuation lines
    joined; the block named so a verdict can say which version's rule."""
    out: list[dict[str, str]] = []
    block = "uniform"
    cur: list[str] | None = None

    def flush() -> None:
        nonlocal cur
        if cur:
            text = " ".join(l.strip() for l in cur).strip()
            out.append({"id": f"rule-{len(out) + 1:02d}", "block": block, "text": text})
        cur = None

    started = False
    for line in instruction.splitlines():
        m = re.match(r"--- ADDED IN (v\d+) ---", line)
        if m:
            flush(); block = m.group(1); started = True; continue
        if re.match(r"--- END ADDED IN", line):
            flush(); continue
        if line.startswith("UNIFORM DECISION RULES"):
            flush(); block = "uniform"; started = True; continue
        if line.startswith("RETURN:"):
            flush(); break
        if not started:
            continue
        if line.startswith("- "):
            flush(); cur = [line[2:]]
        elif cur is not None and line.startswith("  ") and line.strip():
            cur.append(line)
        elif cur is not None and not line.strip():
            flush()
    flush()
    return out


#: What the pack shows for a receipt path the final record no longer has —
#: a leaf phase 4 deleted, an index into a list it collapsed. Distinct from
#: a genuine null leaf, which the pack shows as `null` (#808).
UNRESOLVED = "<path does not resolve in the record>"


def _value_at(record: Any, path: str, limit: int = 300) -> Any:
    """The record's value at a slot path, truncated for the pack (#791);
    :data:`UNRESOLVED` when the path does not reach a value."""
    cur = record
    for part in re.findall(r"[\w]+|\[\d+\]", path):
        try:
            if part.startswith("["):
                # a list index against a string would return a character —
                # a receipt path into a value reconcile collapsed to one string
                # does not resolve, it is not a one-letter value
                if not isinstance(cur, list):
                    return UNRESOLVED
                cur = cur[int(part[1:-1])]
            else:
                if not isinstance(cur, dict) or part not in cur:
                    return UNRESOLVED
                cur = cur[part]
        except (KeyError, IndexError, TypeError):
            return UNRESOLVED
    s = cur if isinstance(cur, (int, float, bool)) or cur is None else str(cur)
    return s[:limit] + "…" if isinstance(s, str) and len(s) > limit else s


def _raw_value(record: Any, path: str) -> Any:
    """The untruncated value at a path; a one-item list of a scalar is that
    scalar (`data_topic: [B2AI_TOPIC:43]`)."""
    from data_sheets_schema.receipts import _resolve_value
    ok, v = _resolve_value(record, path)
    if ok and isinstance(v, list) and len(v) == 1 and isinstance(v[0], str):
        return v[0]
    return v if ok else None


def _registry_label(value: Any) -> str | None:
    """The pinned registry label for a `values_from` CURIE (#912): the digest
    shows the model `id=name` pairs for B2AI_TOPIC / B2AI_SUBSTRATE, the
    pack showed the reviewer the bare CURIE; seven of the twelve v7 review
    files say the term cannot be checked (verdicts `exempt_by_nature` x5,
    `cannot_tell` x1). Scans every pinned vocabulary rather than the slot's
    own `values_from` — safe while the vocabularies are self-prefixed and
    disjoint (#917 scopes it). None for anything else."""
    if not isinstance(value, str) or ":" not in value:
        return None
    try:
        from data_sheets_schema.schema_digest import vocabularies
        for terms in vocabularies().values():
            if value in terms:
                return str(terms[value])
    except Exception:                                         # noqa: BLE001
        return None
    return None


ID_ORIGINS = ("minted", "constructed", "stated")

#: What may follow a base inside the bundle for the match to be the base
#: itself and not a prefix of a longer URL (`…/datasets/3` inside
#: `…/datasets/30` or `…/datasets/3/access`; #1108 review, finding 5).
_URL_CONTINUATION = re.compile(r"[A-Za-z0-9/_#?=&%~]")
#: `.` and `-` continue a URL only when what follows them does too
#: (`…/4.0/`, `…/2024.05.21/`); a URL ending a sentence — the commonest
#: way one appears in prose, thirteen in the AI_READI bundle alone — is the
#: URL itself (#1117 round 2). A trailing `/` is deliberately a
#: continuation: `…/dataset` and `…/dataset/` are different resources.
_URL_JOINER = re.compile(r"[.\-]")


def _canonical_identifier(value: str) -> str:
    """A resolver URL of a declared prefix as its CURIE, lower-cased; else the
    value as written, lower-cased. The record's own id and a fragment's base
    can be the same identifier in two forms — #974's normaliser writes the
    CURIE, an agentic run may write the URL — and a self-mint must not read
    as a label on someone else's identifier (#1108 review, finding 8). 0 of
    the corpus's 953 constructed ids are this case today; the guard is for
    the shape the normaliser creates."""
    value = value.strip()
    try:
        from data_sheets_schema.api_runner import _identifier_form_tables, curie_form
        _, bases = _identifier_form_tables()
        value = curie_form(value, bases) or value
    except Exception:                                         # noqa: BLE001
        pass
    # Scheme and host fold; the path compares exactly — URL paths are
    # case-sensitive, as `api_runner._split_base` says (#1117 round 2).
    m = re.match(r"^(https?://[^/]+/?)(.*)$", value, re.I)
    if m:
        return m.group(1).lower() + m.group(2)
    prefix, sep, local = value.partition(":")
    return (prefix.lower() + sep + local) if sep else value.lower()


def _id_origin(value: Any, record_id: str | None) -> tuple[str, str | None]:
    """(origin, base). `minted`: a urn or a fragment on the record's own id
    (`receipts._minted`, or the same id in resolver/CURIE alias form).
    `constructed`: a fragment on some *other* base — the record built a
    label on an identifier it did not mint (#901: the AI_READI v7 rep1
    `file_collections[*].id` are `https://fairhub.io/datasets/3#cardiac_ecg`
    on the attested fairhub page, and the two-way minted flag filed them
    with the DOIs). `stated`: no fragment, or an empty one; the value is
    used as a world-facing reference as written."""
    from data_sheets_schema.receipts import _minted
    if not isinstance(value, str):
        return "stated", None
    value = value.strip()
    if _minted(value, record_id):
        return "minted", None
    base, sep, fragment = value.partition("#")
    if not sep or not base or not fragment:
        return "stated", None                                 # no fragment, or nothing constructed
    if record_id and _canonical_identifier(base) == _canonical_identifier(str(record_id)):
        return "minted", None                                 # the record's own id in another form
    return "constructed", base


def _base_in(base: str, bundle_text: str) -> bool:
    """The base appears in the bundle as itself — not as the prefix of a
    longer URL — in either its written form or its resolver/CURIE alias."""
    forms = {base}
    try:
        from data_sheets_schema.api_runner import _identifier_form_tables, curie_form
        _, bases = _identifier_form_tables()
        curie = curie_form(base, bases)
        if curie:
            forms.add(curie)
        else:
            prefix, _, local = base.partition(":")
            for b, pfx in bases:
                if pfx == prefix and local:
                    forms.add(b + local)
    except Exception:                                         # noqa: BLE001
        pass
    for form in forms:
        start = 0
        while True:
            i = bundle_text.find(form, start)
            if i < 0:
                break
            nxt = bundle_text[i + len(form):i + len(form) + 1]
            nxt2 = bundle_text[i + len(form) + 1:i + len(form) + 2]
            continues = bool(nxt) and (bool(_URL_CONTINUATION.match(nxt))
                                       or (bool(_URL_JOINER.match(nxt)) and bool(nxt2)
                                           and bool(_URL_CONTINUATION.match(nxt2))))
            if not continues:
                return True
            start = i + 1
    return False


def _id_slots(full: Any, root_class: str | None = None,
              bundle_text: str | None = None) -> tuple[list[dict[str, Any]], str | None]:
    """Every populated `…id` leaf of the record with whether the schema
    *forces* the id (#803) and whether the value is a *mint* (#823): `File`,
    `FileCollection`, `DataSubset` — and `Person` — ids are LinkML
    identifiers, so a record that documents those parts cannot omit the id.
    `forced` speaks only to the id's presence given the object; `minted`
    (a urn, or a fragment on the record's own id — `receipts._minted`) is
    what separates a labelled part from a world-facing reference, whose
    truth the evidence rules judge, not the fragment rule.

    `origin` (#901) is the three-way form of that flag: `minted`,
    `constructed` (a fragment on a base the record did not mint — carries
    `base`, and `base_in_bundle` when the bundle text is given: whether
    the base appears in it as itself — not as the prefix of a longer URL —
    in its written or alias form, so the reviewer can tell a label on an
    attested page from a label on an invented one), `stated`. The caller
    is responsible for passing the bytes the record read: `build_pack`
    checks the bundle's md5 against the record's and passes nothing on a
    drift, naming the gap. `minted`
    stays as the boolean it was; `constructed` entries are `minted: false`
    as before, now told apart from the DOIs they were filed with.

    Returns (entries, gap): entries carry {path, class, identifier, required,
    forced, minted, origin[, base, base_in_bundle]}; a path whose class the
    walk cannot resolve is listed with resolvable: false rather than
    guessed. gap names why the flags are unavailable (no schema, no
    SchemaView, unknown root class) — named, not filled; exception class
    only, so pack bytes stay machine-neutral."""
    try:
        from linkml_runtime import SchemaView

        from data_sheets_schema.constants.schemas import SCHEMA_PATH
        from data_sheets_schema.receipts import _minted, populated_leaves
        schema_path = Path(SCHEMA_PATH)
        if not schema_path.is_absolute():                     # cwd-proof (#822)
            schema_path = Path(__file__).resolve().parents[2] / schema_path
        sv = shared_view(schema_path)
    except Exception as e:                                    # noqa: BLE001
        return [], f"id slot flags unavailable: {type(e).__name__}"
    root = root_class or (full.get("conforms_to_class") if isinstance(full, dict) else None) or "Dataset"
    if not sv.get_class(root, strict=False):
        return [], f"id slot flags unavailable: root class {root} not in the schema"
    record_id = full.get("id") if isinstance(full, dict) and isinstance(full.get("id"), str) else None
    out: list[dict[str, Any]] = []
    for path, value in populated_leaves(full):
        if path == "id" or not path.endswith(".id"):          # the record's own id is exempt (#722)
            continue
        cls: str | None = root
        try:
            for name in [n for n in re.findall(r"[\w]+|\[\d+\]", path) if not n.startswith("[")][:-1]:
                rng = sv.induced_slot(name, cls).range
                cls = rng if rng and sv.get_class(rng, strict=False) else None
                if cls is None:
                    break
            if cls is None:
                out.append({"path": path, "resolvable": False})
                continue
            slot = sv.induced_slot("id", cls)
            ident, req = bool(slot.identifier), bool(slot.required)
            origin, base = _id_origin(value, record_id)
            entry = {"path": path, "class": cls, "identifier": ident, "required": req,
                     "forced": ident or req, "minted": origin == "minted", "origin": origin}
            if origin == "constructed":
                entry["base"] = base
                entry["base_in_bundle"] = _base_in(base, bundle_text) if bundle_text is not None else None
            out.append(entry)
        except Exception:                                     # noqa: BLE001
            out.append({"path": path, "resolvable": False})
    return out, None


def build_pack(provenance: Path, instruction_file: Path | None = None,
               sample: dict[str, int] | None = None, *, write_instruction: bool = True,
               instruction_out: list[str] | None = None) -> dict[str, Any]:
    """The pack as a dict — always the pack, nothing else in it. With
    `write_instruction` (the default) the rendered instruction is written
    beside the record as a side effect; `write_pack` passes False and writes
    it only on the path that also writes the pack, so a refused rewrite
    leaves both files as it found them (#1124 review, MF-R1). The text then
    travels out of band, appended to `instruction_out`, never as a key of
    the returned mapping (round 3, SF-R3a: a caller that dumped the mapping
    would have written a pack with an extra key and a different sha256)."""
    from data_sheets_schema.backfill_checks import _split_header
    from data_sheets_schema.chunking import chunk_texts, load_manifest
    from data_sheets_schema.receipts import claim_receipts, load_receipt

    if not write_instruction and instruction_out is None:
        # The third state — neither written nor returned — would hand back a
        # pack pinning an instruction file nobody wrote (#1124 round 4).
        raise ValueError("build_pack: with write_instruction=False the instruction text goes to "
                         "instruction_out, which was not given")
    sample = {**DEFAULT_SAMPLE, **(sample or {})}
    record = _load_yaml(provenance, _split_header(provenance.read_text(encoding="utf-8"))[1])
    paths = record_paths(provenance)
    run = record.get("run") or {}
    inputs = record.get("inputs") or {}
    seed = ((record.get("prompts") or {}).get("request") or {}).get("sha256") or _sha(provenance)
    rng = random.Random(seed)

    pack: dict[str, Any] = {
        # 4: receipted items carry resolved_path/resolution (#899)
        # 5: id_slots entries carry origin minted|constructed|stated, with
        #    base_in_bundle attested only against the bytes the record read (#901)
        "pack_version": 5,
        "run": {"label": run.get("label"), "project": run.get("project"), "method": run.get("method"),
                "condition": (((record.get("prompts") or {}).get("request") or {}).get("spec") or {}).get("condition")},
        # The path only: `review check --write` adds a block to this record,
        # so a hash of it here would make every re-run pack a different pack
        # (#792). The request hash below is what pins the run.
        "provenance": {"path": str(provenance),
                       "request_sha256": ((record.get("prompts") or {}).get("request") or {}).get("sha256")},
        "seed": seed,
        "schema": list(SCHEMA_FILES),
        "gaps": [],
    }

    text, basis = instruction_text(record, instruction_file)
    ipath = paths["instruction"]
    if text and write_instruction:
        ipath.write_text(text, encoding="utf-8")            # the reviewer reads the instruction, not its hash (#791)
    elif text and instruction_out is not None:
        instruction_out.append(text)
    pack["instruction"] = {"basis": basis, "path": str(ipath) if text else None,
                           "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
                           "chars": len(text) if text else 0}
    pack["rules"] = rules_from(text) if text else []
    if not text:
        pack["gaps"].append("instruction: " + basis)

    bundle = Path(inputs["bundle_path"]) if inputs.get("bundle_path") else None
    chunks_in = inputs.get("chunks") or {}
    manifest_path = Path(chunks_in["path"]) if chunks_in.get("path") else None
    pack["bundle"] = {"path": str(bundle) if bundle else None, "md5": inputs.get("bundle_md5"),
                      "manifest": str(manifest_path) if manifest_path else None}
    pack["records"] = {"full": str(paths["full"]), "core": str(paths["core"]),
                       "report": str(paths["report"]),
                       "receipt": str(paths["receipt"]) if paths["receipt"].exists() else None,
                       "claims": str(paths["claims"]) if paths["claims"].exists() else None}

    # --- every minted id, with whether the schema forced it (#803): the
    # instruction's fragment rule cannot be judged without this — a rule-14
    # verdict on an identifier slot charges the record with the schema.
    full_record = _load_yaml(paths["full"]) if paths["full"].exists() else {}
    # The bytes `base_in_bundle` is attested against are the bytes the
    # record read, or nothing: 136 records are drifted (CLAUDE.md, #452), and
    # the AI_READI 2026-09-01 rep1 record that motivated #901 is one of them.
    # A pack that checked today's file and printed the recorded md5 beside
    # the result would attest against bytes the record never saw (#1108
    # review, finding 4). Relative paths resolve against the repo root, as
    # the schema does (#822).
    bundle_text, bundle_state = None, "no bundle_path recorded"
    if bundle:
        bpath = bundle if bundle.is_absolute() else Path(__file__).resolve().parents[2] / bundle
        pack["bundle"]["resolved_path"] = str(bpath)          # which root the bytes came from (round 2, note 6)
        if not bpath.exists():
            bundle_state = f"bundle not on disk ({bpath})"
        else:
            raw = bpath.read_bytes()
            on_disk = hashlib.md5(raw).hexdigest()
            recorded = inputs.get("bundle_md5")
            if not recorded:
                bundle_state = f"no bundle_md5 recorded (on disk {on_disk})"
            elif on_disk != recorded:
                bundle_state = f"bundle drifted (recorded {recorded}, on disk {on_disk} at {bpath})"
            else:
                bundle_text, bundle_state = raw.decode("utf-8", errors="replace"), "current"
    id_entries, id_gap = (_id_slots(full_record, bundle_text=bundle_text) if full_record
                          else ([], "id slot flags unavailable: no full record"))
    pack["id_slots"] = {"entries": id_entries,
                        "bundle_state": bundle_state,
                        # the record's own id, so the licensed-form call (a second
                        # identifier for this dataset vs a third party's) can be
                        # made from the pack (round 2, note 7)
                        "record_id": full_record.get("id") if isinstance(full_record, dict) else None,
                        "note": "forced: the schema declares this class's id as an identifier or required, "
                                "so the record could not omit the id given the object — it settles the id's "
                                "presence, not the object's. origin (#901): minted is a urn or a fragment on "
                                "the record's own id (in any form); constructed is a fragment on an "
                                "identifier the record did not mint (base named; base_in_bundle says whether "
                                "that base appears in the bytes the record read, as itself and not as the "
                                "prefix of a longer URL, in its written or alias form; null when those bytes "
                                "are not on disk — see bundle_state); stated is a reference used as written. "
                                "The fragment rule is judged on minted AND constructed entries: the rule "
                                "licenses a fragment on an identifier the evidence supplies, so a constructed "
                                "id on this dataset's own attested identifier (its DOI, its landing page) is "
                                "the licensed form and is judged exactly as a mint — a forced one never "
                                "violates, an unforced one must be pointed at; one built on another entity's "
                                "identifier (an organisation, a person, another dataset) is the false claim "
                                "the identifier rule names; one whose base is not in the bundle is an "
                                "unsupported reference under the evidence rules, and its fragment inherits "
                                "that. stated entries are the evidence rules' business only. minted (boolean) "
                                "is kept for packs that read it: it is origin == minted. resources[*].id is "
                                "also consumed by `d4d derive core`'s projection."}
    if id_gap:
        pack["gaps"].append(id_gap)
    if full_record and bundle_state != "current" and any(e.get("origin") == "constructed" for e in id_entries):
        pack["gaps"].append(f"id_slots.base_in_bundle unavailable: {bundle_state}")

    # --- class-ranged attributes that are references (#805, #916): a string
    # is the only form that validates there, so a rule that asks for the
    # class's fields (rule-08 on the v7 packs) does not apply. Six of twelve
    # v7 reviews charged `principal_investigator: <name>` under it.
    try:
        from data_sheets_schema.schema_digest import build as _build_digest
        refs = sorted(f"{n.name}.{k} → {v}" for n in _build_digest("Dataset").nested
                      for k, v in n.ranges.items() if "(reference" in v)
    except Exception as e:                                    # noqa: BLE001
        refs, ref_gap = [], f"reference attributes unavailable: {type(e).__name__}"
        pack["gaps"].append(ref_gap)
    pack["reference_attributes"] = {
        "entries": refs,
        "note": "A class-ranged attribute that is not inlined is a reference: the record must hold a "
                "string there (an inline object fails validation, #805), so a rule asking for the "
                "class's declared fields does not apply to it — judge the string's support, not its shape."}

    # --- chunks marked nothing_relevant: every one, with its lines
    items: list[dict[str, Any]] = []
    if paths["receipt"].exists() and manifest_path and manifest_path.exists():
        try:
            receipt = load_receipt(paths["receipt"])
        except yaml.YAMLError as exc:
            raise UnreadableYAML(paths["receipt"], exc) from exc
        try:
            manifest = load_manifest(manifest_path)
        except yaml.YAMLError as exc:
            raise UnreadableYAML(manifest_path, exc) from exc
        span = {c["id"]: c for c in manifest["chunks"]}
        pack["bundle"]["lines"] = manifest.get("bundle_lines")
        pack["bundle"]["chunks"] = [{"id": c["id"], "lines": c["lines"], "source": c["source"]} for c in manifest["chunks"]]
        for e in receipt.get("chunks") or []:
            if e.get("status") == "nothing_relevant" and e.get("id") in span:
                c = span[e["id"]]
                items.append({"id": f"chunk-{e['id']}", "kind": "chunk_nothing_relevant",
                              "chunk": e["id"], "lines": c["lines"], "source": c["source"],
                              "agent_reason": e.get("reason"),
                              "question": "Does this chunk hold anything the record should carry and does not? "
                                          "Open the lines; answer against the full record."})
        # --- slots
        full = full_record
        # Receipt paths are joined to the final record by entry identity
        # against the phase-1 snapshot (#899): reconciliation's inserts and
        # reorders otherwise shift a receipt onto a neighbouring entry and
        # the reviewer scores a bundle-attested value `unsupported`. The
        # item carries the path as written and where it resolves.
        from data_sheets_schema.receipts import phase1_snapshot, phase1_snapshot_path
        original = phase1_snapshot(paths["receipt"])
        snapshot_file = phase1_snapshot_path(paths["receipt"])
        # Not a gap: the agentic path writes no snapshot by design (its
        # Phase 3 re-receipts what it changes), so an index join there is
        # the instrument, not a defect in this pack. A snapshot that exists
        # and will not parse IS a gap (#1124 round 6): the join falls back
        # to index, and the pack must not say there was no snapshot — the
        # reviewer reads `basis` to decide whether an index shift may be
        # scored unsupported.
        if original is not None:
            pack["receipt_join"] = {"basis": "identity", "snapshot": "intermediate/ phase-1 full record"}
        elif snapshot_file is not None:
            pack["receipt_join"] = {"basis": "index",
                                    "reason": f"the phase-1 snapshot {snapshot_file.name} is present but "
                                              "unreadable; receipt paths joined by index, not entry identity (#899)"}
            pack["gaps"].append(f"phase-1 snapshot unreadable: {snapshot_file}")
        else:
            pack["receipt_join"] = {"basis": "index", "reason": "no phase-1 snapshot under intermediate/; "
                                                                "receipt paths joined by index, not entry identity (#899)"}
        claims = claim_receipts(receipt, full, original)
        rc = record.get("receipts") or {}
        receipted = sorted(claims["slots"])
        rng.shuffle(receipted)
        for slot in receipted[: sample["receipted_slots"]]:
            claim = claims["slots"][slot]
            rs = claim["receipts"]
            # With a snapshot, a None resolution means the receipted entry is
            # gone: the reviewer sees UNRESOLVED, never the value of whatever
            # now sits at the written index (#907 review, A).
            at = claim.get("resolved_path") if original is not None else slot
            item = {"id": f"slot-{len(items) + 1:03d}", "kind": "slot_receipted", "slot": slot,
                    "value": _value_at(full, at) if at else UNRESOLVED,
                    "receipts": [{"chunk": r["chunk"], "lines": span.get(r["chunk"], {}).get("lines"),
                                  "snippet": r["snippet"]} for r in rs],
                    "question": "Read the passage each snippet sits in. Does it support the record's value at "
                                "this slot, as the slot's description asks, and is the value the right reading? "
                                f"A value of {UNRESOLVED!r} means the final record has no value at this path: "
                                "answer cannot_tell unless the receipt's statement survives elsewhere."}
            if original is not None:
                item["resolved_path"] = claim.get("resolved_path")
                item["resolution"] = claim.get("resolution")
                if at and at != slot:
                    item["question"] += (" The receipt was written at `slot`; the entry it receipted now sits "
                                         "at `resolved_path` (followed by identity, #899) — judge the value there.")
                if "value_at_receipt" in claim:
                    item["value_at_receipt"] = claim["value_at_receipt"]
                    item["question"] += (" A later phase rewrote this value after the receipt: `value_at_receipt` "
                                         "is what the receipt attested, `value` is what the record now says — "
                                         "judge whether the passage supports the current value.")
            label = _registry_label(_raw_value(full, at) if at else None)
            if label:
                item["value_label"] = label
            items.append(item)
        # The receiptless set from the receipt and the record themselves,
        # not the record's 50-entry walk-order prefix (#790): every populated,
        # non-exempt leaf no receipt path covers, sorted, then sampled.
        from data_sheets_schema.receipts import _covers, exempt, populated_leaves
        record_id = full.get("id") if isinstance(full.get("id"), str) else None
        # A claim whose identity resolution is None (entry gone, index
        # reused, not in the snapshot) covers nothing — never the written
        # index (#907 review).
        covering = {(c["resolved_path"] if original is not None else s)
                    for s, c in claims["slots"].items()} - {None}
        without = sorted(p for p, v in populated_leaves(full)
                         if not exempt(p, v, record_id) and not any(_covers(r, p) for r in covering))
        rng.shuffle(without)
        for slot in without[: sample["receiptless_slots"]]:
            item = {"id": f"slot-{len(items) + 1:03d}", "kind": "slot_receiptless", "slot": slot,
                    "value": _value_at(full, slot),
                    "question": "No receipt names a passage for this value. Find one in the bundle, or "
                                "conclude it is inferred from stated lines, or that the bundle does not "
                                "state it, or that the slot is of a kind that has no passage."}
            label = _registry_label(_raw_value(full, slot))
            if label:
                item["value_label"] = label
            items.append(item)
        reshaped = list(((rc.get("slots") or {}).get("reshaped_by_reconcile")) or [])
        for slot in reshaped[: sample["reshaped_slots"]]:
            items.append({"id": f"slot-{len(items) + 1:03d}", "kind": "slot_reshaped", "slot": slot,
                          "question": "A later phase reshaped this path after the receipt. Does the value now "
                                      "at the reshaped location still say what the receipted passage says?"})
        pack["counts"] = {"nothing_relevant_chunks": sum(1 for i in items if i["kind"] == "chunk_nothing_relevant"),
                          "receipted_slots_total": len(claims["slots"]),
                          "receiptless_slots_total": len(without),
                          "reshaped_slots_total": len(reshaped),
                          "sampled": {"receipted": min(sample["receipted_slots"], len(claims["slots"])),
                                      "receiptless": min(sample["receiptless_slots"], len(without))}}
    else:
        pack["gaps"].append("no coverage receipt or chunk manifest: chunk and slot items cannot be built")
        pack["counts"] = {}

    for r in pack["rules"]:
        items.append({"id": r["id"], "kind": "rule", "block": r["block"], "text": r["text"],
                      "question": "Did the record follow this rule? Cite the slot(s) that show it, or the violation."})
    # --- semantic-review-required pair warnings (#691): the provenance block
    # stores only a count, so the deterministic checker is re-run on the two
    # records; failure to run is a named gap, never a silent absence.
    try:
        from data_sheets_schema.d4d_pair_consistency import (
            load_pair_schema, pair_predates_current_schema, validate_pair_data)
        full_p, core_p = Path(pack["records"]["full"]), Path(pack["records"]["core"])
        if full_p.exists() and core_p.exists():
            rep = validate_pair_data(
                _load_yaml(full_p),
                _load_yaml(core_p),
                load_pair_schema(*(_anchored(Path(x)) for x in PAIR_SCHEMAS)),
                schema_moved=pair_predates_current_schema(core_p),
                run_digest=(record.get("schema") or {}).get("digest_md5"))
            n = 0
            for w in rep.warnings:
                if getattr(w, "code", None) != "semantic-review-required":
                    continue
                n += 1
                items.append({"id": f"pair-{n:02d}", "kind": "pair_warning",
                              "path": w.path, "checker_message": w.message,
                              "question": "The deterministic checker matched this related full/core "
                                          "content but cannot judge the relation semantically. Open "
                                          "both records at the path; do the matched values say the "
                                          "same thing? Answer with the paths compared and what "
                                          "differs, if anything."})
        else:
            pack["gaps"].append("pair warnings: full or core record missing; the checker did not run")
    except Exception as e:                                    # noqa: BLE001
        # The class alone says nothing once `_load_yaml` wraps the parse
        # (#1124 round 6): name the file where the loader named it.
        pack["gaps"].append("pair warnings unavailable: "
                            + (str(e) if isinstance(e, UnreadableYAML) else type(e).__name__))

    pack["items"] = items
    pack["verdicts"] = {k: list(v) for k, v in VERDICTS.items()}
    return pack


class PackAttested(RuntimeError):
    """The pack on disk is pinned by hash and a rewrite would move it
    underneath that pin (#1095)."""

    def __init__(self, path: Path, pins: list[dict[str, str]], force_hint: str = "force=True"):
        self.path, self.pins, self.force_hint = path, pins, force_hint
        super().__init__(self.describe(force_hint))

    def describe(self, force_hint: str) -> str:
        """The refusal, naming each pin's class (#1124 review, N9): a pin the
        write would move, one whose pack is not on disk, one that could not
        be read — and the override in the caller's own vocabulary (N8)."""
        who = []
        for p in self.pins:
            sha = str(p.get("sha256", ""))
            if sha.startswith("unreadable"):
                who.append(f"{p['by']} {p['path']} (unreadable {sha[len('unreadable '):]}: nothing is known about "
                           "what would move; fix that file — forcing cannot read it either)")
            elif p.get("pack_on_disk") is False:
                who.append(f"{p['by']} {p['path']} (its pack is not on disk; this write would not reproduce it)")
            else:
                who.append(f"{p['by']} {p['path']} (this write would move the file under it)")
        return (f"{self.path} is pinned by hash by " + "; ".join(who) + f". Pass {force_hint} only as a "
                "deliberate act, and redo the attesting review afterwards — "
                "`d4d review check` reports review_of_another_pack until it is.")


def pack_pin_state(provenance: Path) -> str | None:
    """What `d4d runs check` reports for a record's pack pin (#1095; #1124
    review, SF2): None when the record pins no pack or the pack on disk is
    the one it pins; `missing` when the pack is gone; `rewritten` when the
    file hashes to something else. The pack path is derived from the
    record's own location, never read off the recorded string (N5)."""
    from data_sheets_schema.backfill_checks import _split_header
    try:
        record = _load_yaml(provenance, _split_header(provenance.read_text(encoding="utf-8"))[1])
    except Exception:                                         # noqa: BLE001
        return None
    rec_sha = (((record.get("review") or {}).get("artifacts") or {}).get("pack") or {}).get("sha256")
    if not rec_sha:
        return None
    pack = record_paths(provenance)["pack"]
    if not pack.exists():
        return "missing"
    return None if hashlib.sha256(pack.read_bytes()).hexdigest() == rec_sha else "rewritten"


def pack_pins(provenance: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """(current, stale): who pins the pack by sha256 — the provenance record's
    `review.artifacts.pack.sha256`, and every `{P}_review*.yaml` beside it
    whose `pack_sha256` names a pack. `current` pins hash to the file as it
    is; `stale` pins name a pack the file no longer is — it moved once
    already, or it is gone (#1095; #1124 review, MF1: a deleted pack must
    not remove the guard, since the agent is told to run `d4d review pack`
    exactly then). Files that do not parse are returned under `unreadable`
    in the third position of `pack_pins_report`; here they are folded into
    `stale` with `sha256: "unreadable (<error>)"`, so a caller of the
    2-tuple that treats "no pin" as permission fails closed, not open (SF3;
    #1124 review, SF-R1: the first version dropped them)."""
    current, stale, unreadable = pack_pins_report(provenance)
    return current, stale + [{"by": u["by"], "path": u["path"], "sha256": f"unreadable ({u['error']})",
                              "pack_on_disk": None} for u in unreadable]


def pack_pins_report(provenance: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    from data_sheets_schema.backfill_checks import _split_header
    paths = record_paths(provenance)
    pack = paths["pack"]
    on_disk = hashlib.sha256(pack.read_bytes()).hexdigest() if pack.exists() else None
    current, stale, unreadable = [], [], []
    try:
        record = _load_yaml(provenance, _split_header(provenance.read_text(encoding="utf-8"))[1])
    except Exception as exc:                                  # noqa: BLE001
        record = {}
        unreadable.append({"by": "provenance record", "path": str(provenance), "error": type(exc.__cause__ or exc).__name__})
    rec_sha = (((record.get("review") or {}).get("artifacts") or {}).get("pack") or {}).get("sha256")
    if rec_sha:
        (current if rec_sha == on_disk else stale).append(
            {"by": "provenance record", "path": str(provenance), "sha256": rec_sha,
             "pack_on_disk": on_disk is not None})
    project = paths["project"]
    for f in sorted(pack.parent.glob(f"{project}_review*.yaml")):
        if f == pack:
            continue
        try:
            sha = _load_yaml(f).get("pack_sha256")
        except Exception as exc:                              # noqa: BLE001
            unreadable.append({"by": "review", "path": str(f), "error": type(exc.__cause__ or exc).__name__})
            continue
        if sha:
            (current if sha == on_disk else stale).append(
                {"by": "review", "path": str(f), "sha256": sha, "pack_on_disk": on_disk is not None})
    return current, stale, unreadable


def write_pack(provenance: Path, instruction_file: Path | None = None,
               sample: dict[str, int] | None = None, *, force: bool = False,
               force_hint: str = "force=True") -> tuple[Path, dict[str, Any]]:
    """Write the pack beside the record — refusing, unless forced, to rewrite
    a pack that a review or the record pins by hash (#1095): a
    `d4d-review-record` run regenerated the pack it was reviewing, moving
    the committed `pack_version: 3` file to 4 underneath the sha256 its own
    record attests and breaking the pairing `d4d review agree` depends on.
    Regenerating a pack is a deliberate act, like rotating a prompt pin."""
    current, stale, unreadable = pack_pins_report(provenance)
    out = record_paths(provenance)["pack"]
    blind = [{"by": u["by"], "path": u["path"], "sha256": f"unreadable ({u['error']})"} for u in unreadable]
    if blind and not force:
        # Before building: a provenance record that will not parse would
        # raise inside `build_pack` as a bare ParserError rather than as the
        # named refusal this guard exists to give (#1124 review, SF-R2).
        raise PackAttested(out, blind, force_hint)
    instruction_out: list[str] = []
    pack = build_pack(provenance, instruction_file, sample, write_instruction=False,
                      instruction_out=instruction_out)
    from data_sheets_schema.provenance import _NoAliasDumper
    text = yaml.dump(pack, Dumper=_NoAliasDumper, sort_keys=False, allow_unicode=True, width=10_000)
    new_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # The guard is on the effect, not the act (#1124 review, SF1): build
    # first, and refuse only when the bytes would move under a live pin —
    # a byte-identical rewrite (the pack is deterministic, seeded by the
    # record's request hash) is not a rewrite. A pin whose file is gone
    # (MF1) is a live pin the write would orphan; an unreadable pin file
    # is treated as live (SF3), so the guard fails closed.
    if not force:
        would_move = [p for p in current if p["sha256"] != new_sha]
        orphaned = [p for p in stale if not p.get("pack_on_disk") and p["sha256"] != new_sha]
        if would_move or orphaned:
            raise PackAttested(out, would_move + orphaned, force_hint)
    out.write_text(text, encoding="utf-8")                  # the pinned artifact first
    if instruction_out:
        Path(pack["instruction"]["path"]).write_text(instruction_out[0], encoding="utf-8")
    return out, pack


def check_review(pack: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    """Does the review answer the pack? Every item once, with a verdict from
    its kind's vocabulary and a pointer that exists in the pack; the counts
    are affirmative and `cannot_tell` is its own number (#787)."""
    findings: list[dict[str, Any]] = []
    by_id = {i["id"]: i for i in pack.get("items") or []}
    answered: dict[str, dict[str, Any]] = {}
    for a in review.get("items") or []:
        if not isinstance(a, dict) or a.get("id") not in by_id:
            findings.append({"kind": "answer_for_unknown_item", "id": a.get("id") if isinstance(a, dict) else None})
            continue
        if a["id"] in answered:
            findings.append({"kind": "item_answered_twice", "id": a["id"]}); continue
        kind = by_id[a["id"]]["kind"]
        if a.get("verdict") not in VERDICTS[kind]:
            findings.append({"kind": "verdict_not_in_vocabulary", "id": a["id"], "verdict": a.get("verdict"),
                             "allowed": list(VERDICTS[kind])})
        if not str(a.get("evidence") or "").strip():
            findings.append({"kind": "verdict_without_evidence", "id": a["id"]})
        answered[a["id"]] = a
    unanswered = [i for i in by_id if i not in answered]
    if not review.get("pack_sha256"):
        findings.append({"kind": "review_without_pack_hash"})      # which pack was answered? (#792)
    elif pack.get("_sha256") and review["pack_sha256"] != pack["_sha256"]:
        findings.append({"kind": "review_of_another_pack", "pack": pack["_sha256"], "review": review["pack_sha256"]})
    by_kind: dict[str, dict[str, int]] = {}
    for iid, a in answered.items():
        k = by_id[iid]["kind"]; d = by_kind.setdefault(k, {})
        d[str(a.get("verdict"))] = d.get(str(a.get("verdict")), 0) + 1
    adverse = sum(v for k, d in by_kind.items() for verdict, v in d.items() if verdict in ADVERSE.get(k, ()))
    cannot = sum(d.get(CANNOT_TELL, 0) for d in by_kind.values())
    return {"checked": True, "items_total": len(by_id), "items_answered": len(answered),
            "unanswered": unanswered[:50], "unanswered_truncated": max(0, len(unanswered) - 50) or None,
            "by_kind": by_kind, "adverse": adverse, "cannot_tell": cannot,
            "findings": findings,
            "summary": (f"items {len(answered)}/{len(by_id)} answered · {adverse} adverse · {cannot} cannot_tell"
                        + (f" · {len(findings)} finding(s)" if findings else ""))}


# ---------------------------------------------------------------- reliability
def _verdict_class(verdict: Any) -> str:
    if verdict == "cannot_tell":
        return "cannot_tell"
    return "affirmative" if verdict in AFFIRMATIVE else "adverse"


def agree(pack: dict[str, Any], review_a: dict[str, Any], review_b: dict[str, Any]) -> dict[str, Any]:
    """Test–retest agreement between two independent reviews of ONE pack.

    Deterministic and offline. Both reviews must pin the pack's sha256 — two
    ratings of different packs are not paired observations. Cohen's kappa is
    computed on the collapsed affirmative/adverse/cannot_tell trichotomy: the
    full vocabulary has too many cells for ~50 items, and the trichotomy is
    what every downstream count (adverse rate) actually uses. Items either
    review left unanswered are excluded from kappa and counted apart. kappa
    is None when the marginals make chance agreement 1 (all items one class
    in both reviews — agreement is perfect but the statistic is undefined).
    """
    for name, rev in (("a", review_a), ("b", review_b)):
        if rev.get("pack_sha256") != pack.get("_sha256"):
            raise ValueError(f"review {name} pins {rev.get('pack_sha256')!r}, not this pack")
    va = {str(i.get("id")): i.get("verdict") for i in review_a.get("items") or []}
    vb = {str(i.get("id")): i.get("verdict") for i in review_b.get("items") or []}
    ids = [str(i.get("id")) for i in pack.get("items") or []]
    kinds = {str(i.get("id")): i.get("kind") for i in pack.get("items") or []}
    paired, unanswered = [], []
    for i in ids:
        # An item without a verdict is unanswered, not a rating: a missing
        # or null verdict must not class as adverse (#861).
        if va.get(i) is not None and vb.get(i) is not None:
            paired.append((i, va[i], vb[i]))
        else:
            unanswered.append(i)
    classes = ("affirmative", "adverse", "cannot_tell")
    n = len(paired)
    conf = {a: {b: 0 for b in classes} for a in classes}
    exact = 0
    disagreements = []
    by_kind: dict[str, dict[str, int]] = {}
    for i, a, b in paired:
        ca, cb = _verdict_class(a), _verdict_class(b)
        conf[ca][cb] += 1
        k = by_kind.setdefault(kinds.get(i, "?"), {"paired": 0, "class_agree": 0, "exact": 0})
        k["paired"] += 1
        if ca == cb:
            k["class_agree"] += 1
        if a == b:
            exact += 1; k["exact"] += 1
        if ca != cb:
            disagreements.append({"id": i, "kind": kinds.get(i), "a": a, "b": b})
    po = (sum(conf[c][c] for c in classes) / n) if n else None
    kappa = None
    if n:
        pe = sum((sum(conf[c].values()) / n) * (sum(conf[r][c] for r in classes) / n) for c in classes)
        kappa = round((po - pe) / (1 - pe), 3) if pe < 1 else None
    adverse_a = sum(1 for _i, a, _b in paired if _verdict_class(a) == "adverse")
    adverse_b = sum(1 for _i, _a, b in paired if _verdict_class(b) == "adverse")
    return {"paired_items": n, "unanswered_in_either": unanswered,
            "percent_class_agreement": round(100 * po, 1) if po is not None else None,
            "percent_exact_agreement": round(100 * exact / n, 1) if n else None,
            "kappa_class": kappa,
            "confusion": conf,
            "adverse_a": adverse_a, "adverse_b": adverse_b,
            "adverse_delta": adverse_b - adverse_a,
            "by_kind": by_kind,
            "disagreements": disagreements,
            "basis": "Cohen's kappa on affirmative/adverse/cannot_tell over items answered by both; "
                     "exact agreement is on the full vocabulary; single pack, both reviews pin its sha256"}
