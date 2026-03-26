"""Render command group for D4D CLI.

Commands for rendering D4D YAML to other formats.
"""

import click
import sys
from pathlib import Path

@click.group()
def render():
    """Render D4D YAML to other formats."""
    pass

@render.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output HTML file (default: <input_file>.html)')
@click.option('--template', type=click.Choice(['human-readable', 'evaluation', 'linkml']),
              default='human-readable',
              help='HTML template style')
def html(input_file, output, template):
    """Render D4D YAML to HTML."""
    if not output:
        output = Path(input_file).with_suffix('.html')

    click.echo(f"🎨 Rendering {input_file} to HTML ({template} style)...")

    # Import and call the rendering script
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

    try:
        if template == 'human-readable':
            from src.html.human_readable_renderer import main as render_main

            # Set up args for the renderer
            old_argv = sys.argv
            sys.argv = ['human_readable_renderer.py',
                        input_file,
                        '-o', str(output)]

            try:
                render_main()
                click.echo(f"✓ HTML saved to {output}")
            finally:
                sys.argv = old_argv

        elif template == 'evaluation':
            click.echo("ℹ️  Evaluation template requires evaluation data")
            click.echo("   Use: d4d evaluate presence --project X --method Y")
            click.echo("   Then find HTML in: data/d4d_html/concatenated/")
            sys.exit(1)

        elif template == 'linkml':
            click.echo("ℹ️  LinkML template for curated datasheets only")
            click.echo("   Use existing rendering workflow via Makefile")
            sys.exit(1)

    except ImportError as e:
        click.echo(f"❌ Error: Renderer not available: {e}", err=True)
        click.echo("Note: HTML rendering requires additional dependencies", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)

@render.command('generate-all')
@click.option('--method', type=click.Choice(['gpt5', 'claudecode_agent', 'claudecode_assistant', 'curated']),
              help='Generate HTML for specific method only')
def generate_all(method):
    """Generate HTML for all D4D files."""
    click.echo("🎨 Generating HTML for all D4D files...")

    # This would call the bulk HTML generation scripts
    click.echo("ℹ️  Bulk HTML generation:")
    click.echo("   Use: make gen-d4d-html")
    click.echo("")
    click.echo("   Or process individual files:")
    click.echo("   d4d render html <file.yaml> -o <output.html>")
