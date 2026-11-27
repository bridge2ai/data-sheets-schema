"""A review pack states its bundle paths relative to the resource root (#6379).

The pack is pinned by sha256 in its review and in the provenance record. Two
absolute paths (`bundle.manifest`, `bundle.resolved_path`) made the same pack
differ between two checkouts of one commit and put the generating machine's
directory layout into a committed file.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from data_sheets_schema import resources, review_pack


def test_a_path_under_the_resource_root_is_stated_relative_to_it(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    target = root / "data" / "preprocessed" / "chunks" / "x_chunks.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("chunks: []\n")
    monkeypatch.setattr(resources, "resource_root", lambda: (root, "checkout"))

    assert review_pack._pack_path(target) == "data/preprocessed/chunks/x_chunks.yaml"


def test_two_checkouts_at_different_locations_state_the_same_path(tmp_path, monkeypatch):
    stated = []
    for name in ("first", "second/nested"):
        root = tmp_path / name
        target = root / "data" / "bundle.txt"
        target.parent.mkdir(parents=True)
        target.write_text("text\n")
        monkeypatch.setattr(resources, "resource_root", lambda root=root: (root, "checkout"))
        stated.append(review_pack._pack_path(target))

    assert stated == ["data/bundle.txt", "data/bundle.txt"]


def test_a_path_under_no_root_is_stated_as_given(tmp_path, monkeypatch):
    root = tmp_path / "checkout"
    root.mkdir()
    elsewhere = tmp_path / "another_corpus" / "bundle.txt"
    elsewhere.parent.mkdir()
    elsewhere.write_text("text\n")
    monkeypatch.setattr(resources, "resource_root", lambda: (root, "checkout"))

    assert review_pack._pack_path(elsewhere) == str(elsewhere)


def test_a_symlinked_root_does_not_make_the_path_absolute(tmp_path, monkeypatch):
    real = tmp_path / "real"
    (real / "data").mkdir(parents=True)
    (real / "data" / "bundle.txt").write_text("text\n")
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setattr(resources, "resource_root", lambda: (link, "checkout"))

    assert review_pack._pack_path(real / "data" / "bundle.txt") == "data/bundle.txt"


def test_the_four_places_a_pack_states_the_bundle_through_pack_path_are_relative_without_the_corpus(tmp_path, monkeypatch):
    """The four places `build_pack` passes the bundle through `_pack_path`, on
    a fixture: the manifest, the resolved path, the drifted sentence and the
    not-on-disk sentence, and the gap line that repeats either sentence. The
    corpus tests below reach the first three only through whatever records are
    committed, and no committed record has lost its bundle (review 3 of PR
    #6380, finding H1). `bundle.path` is not one of the four: it repeats the
    record's own spelling, which this fixture records absolute."""
    from tests.test_review_pack import Pack

    location = str(tmp_path.resolve())
    packs = {}
    for state, options in (("current", {}), ("drifted", {"drift_after": True}), ("gone", {"drop_bundle": True})):
        root = tmp_path / state
        root.mkdir()
        # a record with constructed ids, so that a drifted or missing bundle also leaves the gap line
        provenance, instruction = Pack._run(None, root, full=Pack._constructed_full(None), **options)
        monkeypatch.setattr(resources, "resource_root", lambda root=root: (root, "checkout"))
        packs[state] = review_pack.build_pack(provenance, instruction)

    for state, pack in packs.items():
        assert pack["bundle"]["manifest"] == "P_chunks.yaml", state
        assert pack["bundle"]["resolved_path"] == "P_preprocessed.txt", state
        assert location not in pack["id_slots"]["bundle_state"], state
    assert packs["current"]["id_slots"]["bundle_state"] == "current"
    assert packs["drifted"]["id_slots"]["bundle_state"].endswith(" at P_preprocessed.txt)")
    assert packs["gone"]["id_slots"]["bundle_state"] == "bundle not on disk (P_preprocessed.txt)"
    for state in ("drifted", "gone"):
        gaps = [gap for gap in packs[state]["gaps"] if gap.startswith("id_slots.base_in_bundle unavailable: ")]
        assert len(gaps) == 1 and gaps[0].endswith("P_preprocessed.txt)") and location not in gaps[0], (state, gaps)


def test_a_path_reached_through_a_link_is_stated_by_its_target(tmp_path, monkeypatch):
    """Review 3 of PR #6380, finding H5: links are followed before the path is
    compared with the root.

    The second assertion records a known limitation and is not a requirement:
    a link inside the root that points outside it is stated as given, which
    in a pack is absolute and names the link. Whether that should become the
    unresolved in-root spelling or the resolved target is undecided (#6425,
    H5); change this assertion deliberately when it is decided."""
    root = tmp_path / "checkout"
    (root / "data").mkdir(parents=True)
    (root / "data" / "bundle.txt").write_text("text\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "bundle.txt").write_text("text\n")
    (tmp_path / "way_in").symlink_to(root / "data", target_is_directory=True)
    (root / "way_out").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(resources, "resource_root", lambda: (root, "checkout"))

    assert review_pack._pack_path(tmp_path / "way_in" / "bundle.txt") == "data/bundle.txt"
    assert review_pack._pack_path(root / "way_out" / "bundle.txt") == str(root / "way_out" / "bundle.txt")


@pytest.mark.corpus
def test_a_pack_built_from_a_committed_record_carries_no_absolute_bundle_path():
    root, kind = resources.resource_root()
    if kind != "checkout":
        pytest.skip("needs a checkout with the corpus")
    core = Path(root) / "data" / "d4d_concatenated"
    records = sorted(core.glob("*_core/*/*_provenance.yaml"))
    built = None
    for provenance in reversed(records):          # reverse path order: the method directory sorted last is tried first
        pack = review_pack.build_pack(provenance, None, None, write_instruction=False, instruction_out=[])
        if pack["bundle"].get("manifest") and pack["bundle"].get("resolved_path"):
            built = pack
            break
    assert built is not None, "no committed record resolves both a bundle and a chunk manifest"

    assert not Path(built["bundle"]["manifest"]).is_absolute()
    assert not Path(built["bundle"]["resolved_path"]).is_absolute()
    assert built["bundle"]["resolved_path"] == built["bundle"]["path"]


@pytest.mark.corpus
def test_no_text_of_a_pack_states_where_the_checkout_is(monkeypatch):
    """The whole pack, not only the two bundle keys: a record whose bundle has
    drifted says so in `bundle_state` and in `gaps`, and that sentence named
    the bundle by its absolute path (review 1 of PR #6380, finding A1).

    The record is named relative to the root, from the root, as `d4d review
    pack` names it: the pack repeats the caller's spelling of the record's own
    paths (`provenance.path`, `records.*`, `instruction.path`), which this
    change does not touch."""
    import yaml

    root, kind = resources.resource_root()
    if kind != "checkout":
        pytest.skip("needs a checkout with the corpus")
    monkeypatch.chdir(root)
    location = str(Path(root).resolve())
    records = sorted(Path("data/d4d_concatenated").glob("*_core/*/*_provenance.yaml"))
    seen = {"drifted": 0, "current": 0}
    unbuilt = []
    for provenance in reversed(records):       # reverse path order, as above
        if all(seen.values()):
            break
        try:
            pack = review_pack.build_pack(provenance, None, None, write_instruction=False, instruction_out=[])
        except Exception as error:             # a record this generator cannot pack is another test's subject
            unbuilt.append(f"{provenance}: {type(error).__name__}: {error}")
            continue
        state = str((pack.get("id_slots") or {}).get("bundle_state") or "")
        kind_of_record = "drifted" if state.startswith("bundle drifted") else "current" if state == "current" else None
        text = yaml.safe_dump(pack, sort_keys=False, allow_unicode=True, width=10_000)
        assert location not in text, f"{provenance}: the pack names the checkout's location"      # every pack built
        if kind_of_record == "drifted":
            assert not Path(state.rsplit(" at ", 1)[1].rstrip(")")).is_absolute(), state
        if kind_of_record is not None:
            seen[kind_of_record] += 1
    assert all(seen.values()), (f"the corpus did not offer both a drifted and a current record: {seen}; "
                                f"{len(unbuilt)} record(s) could not be packed, the first: {unbuilt[:1]}")
