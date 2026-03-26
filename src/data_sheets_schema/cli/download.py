"""Download command group for D4D CLI.

Commands for downloading and preprocessing data sources.
"""

import click
import sys
from pathlib import Path
from data_sheets_schema.constants import PROJECTS
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context

@click.group()
def download():
    """Download and preprocess data sources."""
    pass

@download.command()
@click.option('--project', type=click.Choice(PROJECTS), required=True,
              help='Project to download')
@click.option('--output-dir', type=click.Path(), default='data/raw',
              help='Output directory for downloads')
def sources(project, output_dir):
    """Download source documents from Google Sheet."""
    click.echo(f"📥 Downloading sources for {project}...")

    # Import and call the download script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from src.download.organized_dataset_extractor import main as download_main

    # Set up args for the download script
    old_argv = sys.argv
    sys.argv = ['organized_dataset_extractor.py',
                '--output-dir', output_dir,
                '--projects', project]

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
def preprocess(project, input_dir, output_dir):
    """Preprocess raw sources to standard text format."""
    require_repo_context("d4d download preprocess")

    if project:
        click.echo(f"🔄 Preprocessing {project}...")
    else:
        click.echo(f"🔄 Preprocessing all projects...")

    # Import and call the preprocess script
    setup_repo_imports()
    from src.download.preprocess_sources import main as preprocess_main

    # Set up args for the preprocess script
    old_argv = sys.argv
    sys.argv = ['preprocess_sources.py',
                '-i', input_dir,
                '-o', output_dir]
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
def concatenate(project, input_dir, output_file):
    """Concatenate preprocessed files by project."""
    if not output_file:
        output_file = f"data/preprocessed/concatenated/{project}_preprocessed.txt"

    click.echo(f"📑 Concatenating {project} files...")

    # Import and call the concatenate script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from src.download.concatenate_documents import main as concat_main

    input_path = Path(input_dir) / project
    if not input_path.exists():
        click.echo(f"❌ Error: Input directory not found: {input_path}", err=True)
        sys.exit(1)

    # Set up args for the concatenate script
    old_argv = sys.argv
    sys.argv = ['concatenate_documents.py',
                '-i', str(input_path),
                '-o', output_file]

    try:
        concat_main()
        click.echo(f"✓ Concatenated file saved to {output_file}")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
    finally:
        sys.argv = old_argv
