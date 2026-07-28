"""Download command group for D4D CLI.

Commands for downloading and preprocessing data sources.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.constants import PROJECTS
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

DEFAULT_SOURCE_SHEET_CSV = (
    "https://docs.google.com/spreadsheets/d/"
    "1jBD6sTp6TDemy6v75PGAHSVz5yfIAXZ8zdDPbmOGATM/export?format=csv"
)


@click.group()
def download():
    """Download and preprocess data sources."""
    pass

@download.command()
@click.option('--project', type=click.Choice(PROJECTS), required=True,
              help='Project to download')
@click.option('--output-dir', type=click.Path(), default='data/raw',
              help='Output directory for downloads')
@click.option('--sheet-url', default=DEFAULT_SOURCE_SHEET_CSV, show_default=True,
              help='Public CSV export URL or local CSV file')
@click.option(
    '--manifest',
    type=click.Path(exists=True),
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
@click.option('--project', type=click.Choice(PROJECTS),
              help='Preprocess specific project only (default: all)')
@click.option('--input-dir', type=click.Path(), default='data/raw',
              help='Input directory with raw downloads')
@click.option('--output-dir', type=click.Path(), default='data/preprocessed/individual',
              help='Output directory for preprocessed files')
@click.option(
    '--manifest',
    type=click.Path(exists=True),
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
@click.option('--project', type=click.Choice(PROJECTS), required=True,
              help='Project to concatenate')
@click.option('--input-dir', type=click.Path(exists=True),
              default='data/preprocessed/individual',
              help='Input directory with preprocessed files')
@click.option('--output-file', type=click.Path(),
              help='Output file path (default: data/preprocessed/concatenated/{PROJECT}_preprocessed.txt)')
@click.option(
    '--manifest',
    type=click.Path(exists=True),
    default='data/preprocessed/source_manifest.yaml',
    show_default=True,
    help='Canonical source selection manifest',
)
def concatenate(project, input_dir, output_file, manifest):
    """Concatenate preprocessed files by project."""
    require_repo_context("d4d download concatenate")

    if not output_file:
        output_file = f"data/preprocessed/concatenated/{project}_preprocessed.txt"

    click.echo(f"📑 Concatenating {project} files...")

    # Import and call the concatenate script
    setup_repo_imports()
    from src.download.concatenate_documents import main as concat_main

    input_path = Path(input_dir) / project
    if not input_path.exists():
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
@click.option('--project', type=click.Choice(PROJECTS),
              help='Limit to one project (default: all)')
@click.option('--manifest', type=click.Path(exists=True),
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
@click.option('--project', type=click.Choice(PROJECTS),
              help='Limit to one project (default: all)')
@click.option('--manifest', type=click.Path(exists=True),
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
