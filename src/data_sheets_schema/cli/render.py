"""Render command group for D4D CLI."""

import click
import json
import sys
from pathlib import Path
from data_sheets_schema.cli._repo_utils import setup_repo_imports, require_repo_context


def _detect_evaluation_rubric(input_file):
    """Detect rubric type from an evaluation JSON file."""
    with open(input_file, 'r', encoding='utf-8') as f:
        eval_data = json.load(f)

    rubric_value = str(eval_data.get('rubric', '')).lower()
    if rubric_value in {'rubric10', 'rubric20'}:
        return rubric_value

    if 'summary_scores' in eval_data or 'element_scores' in eval_data:
        return 'rubric10'
    if 'overall_score' in eval_data or 'categories' in eval_data:
        return 'rubric20'

    raise click.ClickException(
        "Could not detect evaluation rubric from JSON structure. "
        "Use --rubric to specify rubric10 or rubric20."
    )


def _render_evaluation_html(input_file, output, rubric):
    """Render a single evaluation JSON file to HTML."""
    selected_rubric = rubric
    if selected_rubric == 'auto':
        selected_rubric = _detect_evaluation_rubric(input_file)

    if selected_rubric == 'rubric10':
        from scripts.render_evaluation_html_rubric10_semantic import render_evaluation_file
    elif selected_rubric == 'rubric20':
        from scripts.render_evaluation_html_rubric20_semantic import render_evaluation_file
    else:
        raise click.ClickException(f"Unsupported rubric: {selected_rubric}")

    rendered_path = render_evaluation_file(input_file, output)
    return rendered_path, selected_rubric

@click.group()
def render():
    """Render datasheets and evaluation outputs to HTML."""
    pass

@render.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output HTML file (default: <input_file>.html)')
@click.option('--template', type=click.Choice(['human-readable', 'evaluation', 'linkml']),
              default='human-readable',
              help='HTML template style')
def html(input_file, output, template):
    """Render a structured file to HTML."""
    require_repo_context("d4d render html")

    if not output:
        output = Path(input_file).with_suffix('.html')

    click.echo(f"🎨 Rendering {input_file} to HTML ({template} style)...")

    # Import and call the rendering script
    setup_repo_imports()

    try:
        if template == 'human-readable':
            from src.html.human_readable_renderer import render_yaml_file

            rendered_path = render_yaml_file(input_file, output)
            css_path = Path(rendered_path).parent / 'datasheet-common.css'
            click.echo(f"✓ HTML saved to {rendered_path}")
            if css_path.exists():
                click.echo(f"✓ Stylesheet saved to {css_path}")

        elif template == 'evaluation':
            rendered_path, selected_rubric = _render_evaluation_html(input_file, output, 'auto')
            click.echo(f"✓ Evaluation HTML saved to {rendered_path} ({selected_rubric})")

        elif template == 'linkml':
            from src.html.process_text_files import render_structured_file_to_linkml_html

            rendered_path = render_structured_file_to_linkml_html(input_file, output)
            click.echo(f"✓ LinkML HTML saved to {rendered_path}")

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


@render.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output HTML file (default: <input_file>.html)')
@click.option('--rubric', type=click.Choice(['auto', 'rubric10', 'rubric20']),
              default='auto',
              help='Evaluation rubric to render')
def evaluation(input_file, output, rubric):
    """Render evaluation JSON to HTML."""
    require_repo_context("d4d render evaluation")

    if not output:
        output = Path(input_file).with_suffix('.html')

    click.echo(f"📊 Rendering evaluation {input_file} to HTML...")

    setup_repo_imports()

    try:
        rendered_path, selected_rubric = _render_evaluation_html(input_file, output, rubric)
        click.echo(f"✓ Evaluation HTML saved to {rendered_path} ({selected_rubric})")
    except ImportError as e:
        click.echo(f"❌ Error: Evaluation renderer not available: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
