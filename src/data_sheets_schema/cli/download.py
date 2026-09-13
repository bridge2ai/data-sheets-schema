"""Download command group for D4D CLI.

Commands for downloading and preprocessing data sources.
"""

import click

from data_sheets_schema.registry import load_registry, project_choice, projects_for
import sys

import yaml
from pathlib import Path
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

DEFAULT_SOURCE_SHEET_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "1jBD6sTp6TDemy6v75PGAHSVz5yfIAXZ8zdDPbmOGATM/export?format=csv"
)


@click.group()
def download():
    """Download and preprocess data sources."""
    pass

@download.command('list-projects')
@click.option('--manifest', type=click.Path(), default='data/preprocessed/source_manifest.yaml',
              show_default=True, help='the source manifest that is the registry (#623)')
@click.option('--plain', is_flag=True, help='one name per line, nothing else (for scripts and Make)')
def list_projects(manifest, plain):
    """The projects the selected manifest declares — the one registry the
    CLI and the Make targets read (#623, #637)."""
    reg = load_registry(manifest)
    names = reg.projects()
    if reg.path is None or not reg.path.exists():
        # Loud in both modes: a Make loop fed an empty list by a silent
        # failure "completes" having done nothing (#1367 review, must-fix 8).
        click.echo(f"manifest {manifest} does not exist; no projects", err=True)
        sys.exit(1)
    if plain:
        for n in names:
            click.echo(n)
        return
    click.echo(f"{reg.path}: {len(names)} project(s)")
    for n in names:
        extras = []
        if reg.source_dir(n):
            extras.append(f"source_dir={reg.source_dir(n)}")
        if reg.raw_dir(n):
            extras.append(f"raw_dir={reg.raw_dir(n)}")
        click.echo(f"   {n}" + (f"  ({', '.join(extras)})" if extras else ""))


@download.command()
@click.option('--project', callback=project_choice, required=True,
              help='Project to download')
@click.option('--output-dir', type=click.Path(), default='data/raw',
              help='Output directory for downloads')
@click.option('--sheet-url', default=DEFAULT_SOURCE_SHEET_CSV, show_default=True,
              help='Public CSV export URL or local CSV file')
@click.option(
    '--manifest',
    type=click.Path(exists=True), is_eager=True,
    default='data/preprocessed/source_manifest.yaml',
    show_default=True,
    help='Canonical source selection manifest',
)
def sources(project, output_dir, sheet_url, manifest):
    """Download source documents from Google Sheet."""
    require_repo_context("d4d download sources")

    click.echo(f"📥 Downloading sources for {project}...")

    # Import and call the download script
    setup_repo_imports()
    from src.download.organized_dataset_extractor import main as download_main

    # Set up args for the download script
    old_argv = sys.argv
    sys.argv = ['organized_dataset_extractor.py',
                sheet_url,
                '-o', output_dir,
                '--projects', project,
                '--manifest', manifest]

    try:
        download_main()
        click.echo(f"✓ Downloaded {project} sources to {output_dir}/{project}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv

@download.command()
@click.option('--project', callback=project_choice,
              help='Preprocess specific project only (default: all)')
@click.option('--input-dir', type=click.Path(), default='data/raw',
              help='Input directory with raw downloads')
@click.option('--output-dir', type=click.Path(), default='data/preprocessed/individual',
              help='Output directory for preprocessed files')
@click.option(
    '--manifest',
    type=click.Path(exists=True), is_eager=True,
    default='data/preprocessed/source_manifest.yaml',
    show_default=True,
    help='Canonical source selection manifest',
)
def preprocess(project, input_dir, output_dir, manifest):
    """Preprocess raw sources to standard text format."""
    require_repo_context("d4d download preprocess")

    if project:
        click.echo(f"🔄 Preprocessing {project}...")
    else:
        click.echo("🔄 Preprocessing all projects...")

    # Import and call the preprocess script
    setup_repo_imports()
    from src.download.preprocess_sources import main as preprocess_main

    # Set up args for the preprocess script
    old_argv = sys.argv
    sys.argv = ['preprocess_sources.py',
                '-i', input_dir,
                '-o', output_dir,
                '--manifest', manifest]
    if project:
        sys.argv.extend(['-p', project])

    try:
        preprocess_main()
        click.echo(f"✓ Preprocessed files saved to {output_dir}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv

@download.command()
@click.option('--project', callback=project_choice, required=True,
              help='Project to concatenate')
@click.option('--input-dir', type=click.Path(file_okay=False),
              default='data/preprocessed/individual',
              help='Fallback root for projects without a declared source_dir')
@click.option('--output-file', type=click.Path(),
              help='Output file path (default: the selected registry bundle destination)')
@click.option('--output-dir', type=click.Path(), default=None,
              help='Fallback directory for projects without a declared bundle path')
@click.option(
    '--manifest',
    type=click.Path(exists=True), is_eager=True,
    default='data/preprocessed/source_manifest.yaml',
    show_default=True,
    help='Canonical source selection manifest',
)
def concatenate(project, input_dir, output_file, output_dir, manifest):
    """Concatenate preprocessed files by project."""
    require_repo_context("d4d download concatenate")

    if not output_file:
        output_file = str(load_registry(manifest).bundle(project, Path(output_dir) if output_dir else None))

    click.echo(f"📑 Concatenating {project} files...")

    # Import and call the concatenate script
    setup_repo_imports()
    from src.download.concatenate_documents import main as concat_main

    # A project may select from another project's downloads. VOICE_PEDIATRIC
    # is documented inside VOICE's corpus and has no directory of its own, and
    # the override used to build its bundle lived only in the command someone
    # happened to type (#302). Declared in the manifest, it rebuilds from the
    # manifest.
    input_path = load_registry(manifest).preprocessed_directory(project, Path(input_dir))
    if not input_path.is_dir():
        click.echo(f"❌ Error: Input directory not found: {input_path}", err=True)
        sys.exit(1)

    # Set up args for the concatenate script
    old_argv = sys.argv
    sys.argv = ['concatenate_documents.py',
                '-i', str(input_path),
                '-o', output_file,
                '-e', '.txt',
                '--manifest', manifest,
                '--project', project]

    try:
        concat_main()
        click.echo(f"✓ Concatenated file saved to {output_file}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv


@download.command()
@click.option('--project', callback=project_choice,
              help='Limit to one project (default: all)')
@click.option('--manifest', type=click.Path(exists=True), is_eager=True,
              default='data/preprocessed/source_manifest.yaml', show_default=True,
              help='Canonical source selection manifest')
@click.option('--only', multiple=True, metavar='ID',
              help='Fetch only these manifest source ids (repeatable)')
@click.option('--force', is_flag=True,
              help='Re-fetch sources already present. Overwrites corpus files — '
                   'this invalidates comparability with runs that consumed them.')
@click.option('--dry-run', is_flag=True, help='Report what would be fetched')
def supplements(project, manifest, only, force, dry_run):
    """Fetch manifest-declared sources the input sheet cannot provide.

    `d4d download sources` can only fetch what the GC Input Documents sheet
    lists. Curated historical supplements, API-captured records, and selections
    the sheet has since dropped are invisible to it, so a fresh clone gets a
    smaller corpus than the one generation runs consumed. This rebuilds from the
    manifest, which is the canonical selection.
    """
    require_repo_context("d4d download supplements")
    setup_repo_imports()
    from data_sheets_schema.fetch import fetch_missing, load_sources, missing

    manifest_path = Path(manifest)
    projects = [project] if project else None
    sources = load_sources(manifest_path, projects)
    absent = missing(sources)

    click.echo(f"📚 {len(sources)} manifest sources; {len(absent)} missing locally")
    if not absent and not force:
        click.echo("✓ Local corpus already matches the manifest")
        return
    if force:
        click.echo("⚠️  --force will overwrite files that generation runs consumed")

    plan = fetch_missing(manifest_path, projects, force=force,
                         dry_run=dry_run, only=only or None)

    for r in plan.results:
        icon = {"fetched": "✓", "skipped_present": "·", "dry_run": "→",
                "manual": "✋", "failed": "❌", "no_url": "❌"}.get(r.status, "?")
        size = f"  ({r.bytes_written:,}b)" if r.bytes_written else ""
        click.echo(f"  {icon} {r.source.project:9} {r.source.id:30} {r.detail}{size}")

    click.echo(f"\nfetched={plan.count('fetched')} "
               f"dry_run={plan.count('dry_run')} "
               f"present={plan.count('skipped_present')} "
               f"manual={plan.count('manual')} "
               f"failed={len(plan.failed)}")
    if plan.count('fetched'):
        click.echo("Next: d4d download preprocess, then d4d download concatenate")
    if plan.failed:
        sys.exit(1)


@download.command('audit-manifest')
@click.option('--project', callback=project_choice,
              help='Limit to one project (default: all)')
@click.option('--manifest', type=click.Path(exists=True), is_eager=True,
              default='data/preprocessed/source_manifest.yaml', show_default=True)
def audit_manifest(project, manifest):
    """Report manifest-declared sources against what is on disk."""
    require_repo_context("d4d download audit-manifest")
    setup_repo_imports()
    from data_sheets_schema.fetch import audit

    a = audit(Path(manifest), [project] if project else None)
    click.echo(f"📋 {a['present']}/{a['total']} sources complete "
               f"(raw + preprocessed present)")
    for p, n in a['by_project'].items():
        click.echo(f"   {p:9} {n} sources")
    if a['missing_raw']:
        click.echo(f"\n❌ missing raw ({len(a['missing_raw'])}) "
                   f"— run: d4d download supplements")
        for s in a['missing_raw']:
            click.echo(f"     {s.project:9} {s.id:30} {s.url[:70]}")
    if a['missing_processed']:
        click.echo(f"\n⚠️  raw present but not preprocessed "
                   f"({len(a['missing_processed'])}) "
                   f"— run: d4d download preprocess")
        for s in a['missing_processed']:
            click.echo(f"     {s.project:9} {s.id}")
    if a['manual']:
        click.echo(f"\n✋ manual captures ({len(a['manual'])}) — no command can "
                   f"regenerate these; back them up")
        for s in a['manual']:
            click.echo(f"     {s.project:9} {s.id:30} "
                       f"{'present' if s.has_raw else 'ABSENT — UNRECOVERABLE'}")
    if a['unrecoverable']:
        click.echo(f"\n❌ {len(a['unrecoverable'])} manual source(s) are absent "
                   f"and cannot be re-fetched by any means")
    if not a['missing_raw'] and not a['missing_processed']:
        click.echo("\n✓ local corpus matches the manifest")


@download.command('scope')
@click.option('--project', callback=project_choice,
              help='Limit to one project (default: all)')
@click.option('--check', 'do_check', is_flag=True,
              help='Also check generated records against the declaration.')
@click.option('--strict', is_flag=True,
              help='Exit non-zero if any record is about a related-but-'
                   'distinct dataset.')
@click.option('--record', 'selected_records', multiple=True,
              type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help='With --check and --project: check only these exact records (repeatable).')
@click.option('--manifest', type=click.Path(exists=True), is_eager=True,
              default='data/preprocessed/source_manifest.yaml', show_default=True)
def scope_cmd(project, do_check, strict, selected_records, manifest):
    """What each project's record is about, and whether the records agree.

    Scope is a property of the dataset, not of the prompt (#422). The VOICE
    launch prompt of 2026-08-07 carried a paragraph naming the project, the
    pediatric dataset and a file not to read; declaring the same thing here
    makes it checkable and makes every future dataset inherit the check
    instead of needing its own paragraph.
    """
    if selected_records and (not do_check or not project):
        raise click.UsageError("--record requires --check and --project")
    require_repo_context("d4d download scope")
    setup_repo_imports()
    from data_sheets_schema.scope import (all_scopes, check_manifest,
                                          check_record, malformed_entries,
                                          related_ids)

    m = Path(manifest)
    scopes = all_scopes(m)
    names = [project] if project else sorted(set(scopes) | set(load_registry(m).projects()))
    for name in names:
        s = scopes.get(name)
        if not s:
            click.echo(f"{name:16} no scope declared", err=True)
            continue
        click.echo(f"{name}")
        click.echo(f"   about     {s.get('referent')}  <{s.get('referent_id')}>")
        # A malformed entry is named here, where the declaration is listed
        # (#1157): the listing used to raise on a non-mapping entry before
        # any check ran, and `check_manifest` reports the same rows below.
        rows: dict[int, list] = {}
        for r in malformed_entries(name, m):
            rows.setdefault(r["index"], []).append(r)          # an entry can carry two problems (#1177 review, SF-A)
        for i, entry in enumerate(s.get("related_but_distinct") or []):
            here = rows.get(i, [])
            if any(r["skipped"] for r in here):
                for r in here:
                    click.echo(f"   ⚠️  {name}: related_but_distinct[{i}]: {r['problem']} — that dataset is unchecked")
                continue
            click.echo(f"   not about {entry.get('name')}  <{entry.get('id')}>")
            click.echo(f"             express as `{entry.get('express_as')}`"
                       + (f"; in this bundle as {entry['in_bundle']}"
                          if entry.get("in_bundle") else ""))
            for r in here:
                click.echo(f"   ⚠️  {name}: related_but_distinct[{i}]: {r['problem']}")

    problems = check_manifest(m)
    for p in problems:
        click.echo(f"❌ {p['project']:16} {p['problem']}", err=True)

    bad = []
    if do_check:
        from data_sheets_schema.api_runner import CONCAT_DIR
        from data_sheets_schema.scope import foreign_references
        checked = 0
        unreadable, absorbed = [], []
        # Core records too. Sweeping only `*_d4d.yaml` reported 16 records
        # where the corpus holds 32: a core record is a record, and the
        # pediatric identifiers appear in both halves of the pair.
        records = list(selected_records) if selected_records else sorted([
            *CONCAT_DIR.glob("*/*/*_d4d.yaml"), *CONCAT_DIR.glob("*/*/*_d4d_core.yaml")])
        for rec in records:
            name = project if selected_records else rec.name.replace("_d4d_core.yaml", "").replace("_d4d.yaml", "")
            if project and name != project:
                continue
            if name not in scopes:
                continue
            checked += 1
            status, why = check_record(name, rec, m)
            if status == "out_of_scope":
                bad.append((rec, why))
            elif status == "unreadable":
                unreadable.append((rec, why))
                continue
            refs = foreign_references(name, rec, m)
            if refs:
                absorbed.append((rec, refs))
        click.echo(f"\n{checked} record(s) checked against the declaration")
        for rec, why in bad:
            click.echo(f"   ❌ {rec}\n      {why}")
        if not bad:
            click.echo("   ✓ none is about a dataset its project declares "
                       "distinct")
        for rec, why in unreadable:
            click.echo(f"   ⚠️  unreadable {rec}: {why}")

        # Reported, never fatal (#441). `check_record` settles what a record is
        # *about*; this is the shape one level down — the other dataset placed
        # inside this one's resources or distribution. Citing the related
        # dataset's page is legitimate, absorbing it is not, and the line
        # between them is a judgement this surfaces rather than settles.
        if absorbed:
            n = sum(len(r) for _, r in absorbed)
            click.echo(f"\n⚠️  {len(absorbed)} record(s), {n} value(s) place a "
                       "related-but-distinct dataset outside its declared slot:")
            for rec, refs in absorbed:
                click.echo(f"   {rec}")
                for r in refs[:4]:
                    click.echo(f"      {r['path']} = {r['value']}")
                if len(refs) > 4:
                    click.echo(f"      … {len(refs) - 4} more")
        # Say what the check does not cover. A record can stay in scope by its
        # `id` and still describe the other cohort in its prose, which is what
        # #292 actually looked like; the identifier is the part a rule can
        # settle, and claiming more would be the same overreach as the
        # paragraph this replaces.
        if any(related_ids(n, m) for n in names):
            click.echo("   (checked on the record's `id`; prose that discusses "
                       "a related dataset is legitimate and not inspected)")

    if problems or (strict and (bad or (selected_records and unreadable))):
        sys.exit(1)


@download.command('audit-bundles')
@click.option('--project', callback=project_choice,
              help='Limit to one project (default: all)')
@click.option('--strict', is_flag=True,
              help='Exit non-zero if any derived bundle is stale.')
@click.option('--manifest', type=click.Path(exists=True), is_eager=True,
              default='data/preprocessed/source_manifest.yaml', show_default=True)
def audit_bundles(project, strict, manifest):
    """Rebuild every derived bundle into a temp file and compare it to disk.

    A bundle derived from something that changed is stale, and until now
    nothing said so. #421 stripped curator prose out of the document bundles;
    the crate bundles embed those verbatim and were not rebuilt, so for a day
    the de novo arm read 9 curation notes the baseline arm no longer saw, and
    the two arms were described everywhere as the same corpus (#446).

    Rebuild-and-compare rather than mtime: `crate_only` and `healthsheet_only`
    are legitimately older than the document bundles because they do not derive
    from them, so an mtime rule would report three false positives today. Every
    builder is deterministic, so a difference is staleness and never noise.
    """
    require_repo_context("d4d download audit-bundles")
    setup_repo_imports()
    import contextlib
    import hashlib
    import io
    import tempfile

    from data_sheets_schema.rocrate_normalize import build_crate_bundle

    from data_sheets_schema.registry import default_manifest_path
    from data_sheets_schema.chunking import manifest_for, manifest_status_for
    import shlex

    concat = Path('data/preprocessed/concatenated')
    reg = load_registry(manifest)
    targets = projects_for(manifest, project)
    if strict:
        from data_sheets_schema.registry import validate_context
        if reg.path is None or not reg.path.is_file():
            raise click.ClickException(f"selected manifest does not exist: {reg.path}")
        raw = reg.data.get("projects")
        if not isinstance(raw, dict):
            raise click.ClickException("selected manifest projects must be a mapping")
        declared = reg.projects()
        invalid = [str(key) for key in raw
                   if key not in declared and not (
                       isinstance(key, str) and key.endswith("_source_dir")
                       and key[:-len("_source_dir")] in declared
                       and isinstance(raw[key], str) and raw[key])]
        if invalid:
            raise click.ClickException("invalid project declarations: " + ", ".join(invalid))
        if not targets:
            raise click.ClickException("selected manifest declares no bundle audit targets")
        for name in targets:
            validate_context(reg, name)
    study = reg.path is not None and reg.path.resolve() == default_manifest_path().resolve()
    md5 = lambda p: hashlib.md5(p.read_bytes()).hexdigest()  # noqa: E731

    stale, checked, unchecked, manifests = [], 0, [], 0
    incomplete = False
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name in targets:
            current = reg.bundle(name, concat)
            if not current.is_file():
                unchecked.append((current, 'declared document bundle is missing'))
                incomplete = True
            else:
                src = reg.source_dir(name) or Path('data/preprocessed/individual') / name
                out = tmp / f"{name}_preprocessed.txt"
                try:
                    from src.download.concatenate_documents import main as concat_main
                    argv = sys.argv
                    sys.argv = ['concatenate_documents.py', '-i', str(src),
                                '-o', str(out), '-e', '.txt',
                                '--manifest', str(manifest), '--project', name]
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):
                            concat_main()
                    finally:
                        sys.argv = argv
                    if not out.is_file():
                        raise ValueError('the declared sources produced no bundle')
                    checked += 1
                    if md5(out) != md5(current):
                        stale.append((current, shlex.join([
                            'd4d', 'download', 'concatenate', '--project', name,
                            '--manifest', str(manifest)])))
                except (Exception, SystemExit) as exc:
                    unchecked.append((current, f'{type(exc).__name__}: {exc}'))
                    incomplete = True

            # Additional study arms are only targets of the study registry.
            # A custom registry cannot audit files belonging to a namesake.
            if study:
                crate = concat / f"{name}_preprocessed_with_crate.txt"
                if crate.exists():
                    try:
                        out = tmp / f"{name}_with_crate.txt"
                        with contextlib.redirect_stdout(io.StringIO()):
                            _, included, _ = build_crate_bundle(name, out_path=out)
                        missing = _crate_evidence_in(crate) - set(included)
                        if missing:
                            unchecked.append((crate, 'this checkout is missing crate artifacts the '
                                              f"bundle was built from: {', '.join(sorted(missing))}"))
                        else:
                            checked += 1
                            if md5(out) != md5(crate):
                                stale.append((crate, f'd4d rocrate bundle --project {name}'))
                    except Exception as exc:
                        unchecked.append((crate, f'{type(exc).__name__}: {exc}'))
                for suffix in ('_crate_only.txt', '_healthsheet_only.txt'):
                    other = concat / f"{name}{suffix}"
                    if other.exists():
                        unchecked.append((other, 'no rebuild route registered here'))

            for bundle in reg.bundles(name, concat):
                if not bundle.is_file():
                    continue  # the required document was reported above
                status, detail = manifest_status_for(bundle)
                if status == 'off_rule' and not study:
                    from data_sheets_schema.chunking import (canonical_name, load_manifest,
                                                              validate_manifest_mapping)
                    try:
                        validate_manifest_mapping(load_manifest(manifest_for(bundle)),
                                                  bundle.read_bytes(), canonical_name(bundle))
                    except (OSError, ValueError) as exc:
                        status, detail = 'unreadable', str(exc)
                rebuild = shlex.join(['d4d', 'bundle', 'chunk', '--bundle', str(bundle)])
                if status in ('current', 'stale', 'off_rule'):
                    manifests += 1
                if status == 'stale' or (status == 'off_rule' and study):
                    stale.append((manifest_for(bundle), rebuild))
                elif status in ('missing', 'unreadable', 'no_bundle'):
                    unchecked.append((manifest_for(bundle), detail))
                    # Study-only historical gaps remain visible. Explicit
                    # external inputs must all be auditable in strict mode.
                    incomplete |= not study

    click.echo(f"📦 {checked} derived bundle(s) rebuilt and compared; "
               f"{manifests} chunk manifest(s) rebuilt under their recorded rule (#707)")
    for path, command in stale:
        click.echo(f"   ❌ stale  {path}\n      rebuild: {command}")
    if not stale and not unchecked and checked:
        click.echo("   ✓ every declared bundle and chunk manifest matches its inputs")
    elif not stale and checked:
        click.echo("   ✓ every rebuilt bundle matches what its inputs produce; unchecked targets are listed below")
    elif not stale:
        click.echo("   · no bundle was checked; unchecked targets remain")
    for path, why in unchecked:
        click.echo(f"   ·  unchecked {path}: {why}")
    if strict and (stale or incomplete):
        sys.exit(1)


def _crate_evidence_in(bundle: Path) -> set[str]:
    """The artifact names a crate bundle's own header says it was built from.

    `build_crate_bundle` writes a `CRATE EVIDENCE INCLUDED` block listing each
    file as `  + name — description`. Reading it back is what lets the audit
    tell "this bundle is out of date" from "this checkout has fewer inputs than
    the machine that built it" — two findings that look identical if only the
    bytes are compared.
    """
    names: set[str] = set()
    inside = False
    for line in bundle.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("CRATE EVIDENCE INCLUDED"):
            inside = True
            continue
        if inside:
            if line.startswith("CRATE ARTIFACTS WITHHELD"):
                break
            stripped = line.strip()
            if stripped.startswith("+ "):
                names.add(stripped[2:].split(" — ")[0].strip())
    return names


@download.command("priority")
@click.option("--project", default=None, help="list this project's sources, strongest first")
@click.option("--decide", "decide_ids", default=None,
              help="comma-separated source ids; which of them settles a disagreement")
@click.option("--strict", is_flag=True, help="exit 1 if any source_type is unranked")
@click.pass_context
def priority_cmd(ctx, project, decide_ids, strict):
    """Which source wins when two of them state different things.

    The selected manifest declares source_priority tiers and any explicit
    source overrides or supersession. Use d4d --manifest or D4D_MANIFEST to
    select that declaration.

    A tier is about how directly a source speaks for the released dataset, not
    about how much anyone trusts its authors. Equal tiers do not decide.
    """
    import sys

    from data_sheets_schema.source_priority import (decide as decide_between,
                                                    ranked, tiers,
                                                    unranked_types)
    from data_sheets_schema.registry import selected_manifest

    manifest = load_registry(selected_manifest(ctx)).data
    if decide_ids:
        if not project:
            raise click.ClickException("--decide needs --project")
        ids = [x.strip() for x in decide_ids.split(",") if x.strip()]
        result = decide_between(project, ids, manifest)
        for c in result["candidates"]:
            click.echo(f"   tier {c['priority']}  {c['id']:32} {c['basis']}")
        for u in result["unknown"]:
            click.echo(f"   ?       {u:32} not declared for {project}", err=True)
        click.echo(f"\n{'winner: ' + result['winner'] if result['winner'] else 'no winner'}"
                   f"\n{result['reason']}")
    elif project:
        for s in ranked(project, manifest):
            click.echo(f"   tier {s['priority']}  {s['id']:32} "
                       f"{str(s.get('source_type') or ''):26} {s['priority_basis']}")
    else:
        table = {}
        for source_type, tier in tiers(manifest).items():
            table.setdefault(tier, []).append(source_type)
        for tier in sorted(table):
            click.echo(f"   tier {tier}  {', '.join(sorted(table[tier]))}")

    missing = unranked_types(manifest)
    if missing:
        click.echo("\n⚠️  source_types in use that no tier covers:")
        for proj, types in sorted(missing.items()):
            click.echo(f"     {proj:16} {', '.join(types)}")
        click.echo("   An unranked source cannot win a disagreement, which is "
                   "safe — but it also cannot lose on the record.")
    if strict and missing:
        sys.exit(1)
