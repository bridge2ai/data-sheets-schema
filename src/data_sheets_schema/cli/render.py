"""Render command group for D4D CLI."""

import click
import json
import collections
import sys
from pathlib import Path
from data_sheets_schema.constants import METHODS
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


def _normalize_evaluation_output_stem(input_file):
    """Normalize concise evaluation filenames to canonical HTML stems."""
    stem = Path(input_file).stem

    if stem.endswith('_evaluation_rubric20'):
        return stem[: -len('_evaluation_rubric20')] + '_evaluation'

    for method in sorted(METHODS, key=len, reverse=True):
        method_suffix = f"_{method}_evaluation"
        if stem.endswith(method_suffix):
            return stem[: -len(method_suffix)] + '_evaluation'

    return stem


def _resolve_evaluation_output(input_file, output, rubric):
    """Resolve evaluation output path and final rubric choice."""
    selected_rubric = rubric
    if selected_rubric == 'auto':
        selected_rubric = _detect_evaluation_rubric(input_file)

    if output:
        return Path(output), selected_rubric

    input_path = Path(input_file)
    output_stem = _normalize_evaluation_output_stem(input_path)

    if selected_rubric == 'rubric20':
        if output_stem.endswith('_evaluation'):
            output_stem = f"{output_stem}_rubric20"
        elif not output_stem.endswith('_rubric20'):
            output_stem = f"{output_stem}_rubric20"
    elif output_stem.endswith('_evaluation_rubric20'):
        output_stem = output_stem[: -len('_rubric20')]

    return input_path.with_name(f"{output_stem}.html"), selected_rubric


def _render_evaluation_html(input_file, output, rubric):
    """Render a single evaluation JSON file to HTML."""
    resolved_output, selected_rubric = _resolve_evaluation_output(input_file, output, rubric)

    if selected_rubric == 'rubric10':
        from scripts.render_evaluation_html_rubric10_semantic import render_evaluation_file
    elif selected_rubric == 'rubric20':
        from scripts.render_evaluation_html_rubric20_semantic import render_evaluation_file
    else:
        raise click.ClickException(f"Unsupported rubric: {selected_rubric}")

    rendered_path = render_evaluation_file(input_file, resolved_output)
    return rendered_path, selected_rubric

@click.group()
def render():
    """Render datasheets and evaluation outputs to HTML."""
    pass

@render.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output HTML file (default: derived from input and template)')
@click.option('--template', type=click.Choice(['human-readable', 'evaluation', 'linkml']),
              default='human-readable',
              help='HTML template style')
@click.option('--skip-validation', is_flag=True, default=False,
              help='Skip linkml-validate check before rendering')
def html(input_file, output, template, skip_validation):
    """Render a structured file to HTML."""
    require_repo_context("d4d render html")

    if not output and template != 'evaluation':
        output = Path(input_file).with_suffix('.html')

    # Validate D4D YAML before rendering (skipped for evaluation JSONs and linkml templates).
    # Acts as a gate: refuses to render invalid YAML unless --skip-validation is passed.
    if template == 'human-readable' and not skip_validation:
        setup_repo_imports()
        from src.evaluation.evaluate_d4d import validate_d4d_yaml
        if not validate_d4d_yaml(Path(input_file)):
            raise click.ClickException(
                f"Validation failed for {input_file}. "
                "Fix the YAML or pass --skip-validation to render anyway."
            )

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
@click.option('--method', default=None,
              help='Only this method directory, e.g. claudecode_agent.')
@click.option('--label', 'labels', multiple=True,
              help='Only these run labels. Repeatable.')
@click.option('--project', 'projects', multiple=True,
              help='Only these projects. Repeatable.')
@click.option('--publish', is_flag=True,
              help="Also write each record to the flat, unlabelled path the "
                   "docs build reads. Only meaningful for one label per "
                   "method — see the warning it prints.")
@click.option('--execute', is_flag=True,
              help='Render. Without this, list what would be rendered.')
def generate_all(method, labels, projects, publish, execute):
    """Render every D4D record in the run-labelled corpus to HTML.

    This used to print instructions and generate nothing, and the script it
    pointed at read `data/sheets_concatenated`, a directory that no longer
    exists. Neither knew about run labels, so the output path
    `data/d4d_html/concatenated/{method}/{PROJECT}.html` had no room for one and
    a project rendered from two replicates overwrote itself (#176).

    Output is `.../{method}/{label}/{PROJECT}.html`, which cannot collide.
    """
    require_repo_context("d4d render generate-all")
    setup_repo_imports()
    from src.html.human_readable_renderer import render_yaml_file

    concat = Path("data/d4d_concatenated")
    out_root = Path("data/d4d_html/concatenated")
    if not concat.is_dir():
        raise click.ClickException(f"{concat} not found; nothing to render.")

    jobs = []
    for record in sorted(concat.glob("*/*/*_d4d.yaml")):
        m, label = record.parts[2], record.parts[3]
        project = record.name[: -len("_d4d.yaml")]
        if method and m != method:
            continue
        if labels and label not in labels:
            continue
        if projects and project not in projects:
            continue
        jobs.append((record, m, label, project))

    if not jobs:
        raise click.ClickException(
            "no records matched. `d4d runs list` shows the methods and labels "
            "available.")

    methods = {m for _, m, _, _ in jobs}
    selected_labels = {l for _, _, l, _ in jobs}
    click.echo(f"{len(jobs)} record(s) across {len(methods)} method(s), "
               f"{len(selected_labels)} label(s)")
    if publish and len(selected_labels) > 1:
        # The flat path has no room for a label, so publishing several means
        # later ones overwrite earlier ones and which survives depends on sort
        # order — a silent choice of what the docs show.
        click.echo(
            f"⚠️  --publish with {len(selected_labels)} labels: the flat copy "
            "has no room for a label, so later labels overwrite earlier ones "
            "and which one survives depends on sort order. Publish one label "
            "at a time.", err=True)

    if not execute:
        for record, m, label, project in jobs[:20]:
            click.echo(f"   {m}/{label}/{project}")
        if len(jobs) > 20:
            click.echo(f"   ... and {len(jobs) - 20} more")
        click.echo("\nDry run. Re-run with --execute to render.")
        return

    rendered = failed = 0
    for record, m, label, project in jobs:
        target = out_root / m / label / f"{project}.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            render_yaml_file(str(record), str(target))
            rendered += 1
            if publish:
                flat = out_root / m / f"{project}.html"
                flat.write_bytes(target.read_bytes())
        except Exception as exc:                       # noqa: BLE001
            failed += 1
            click.echo(f"   ❌ {m}/{label}/{project}: {exc}", err=True)

    click.echo(f"\n{rendered} rendered, {failed} failed -> {out_root}/"
               "{method}/{label}/")
    if publish:
        click.echo(f"Also copied to the flat path the docs build reads.")


@render.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(),
              help='Output HTML file (default: canonical name derived from input and rubric)')
@click.option('--rubric', type=click.Choice(['auto', 'rubric10', 'rubric20']),
              default='auto',
              help='Evaluation rubric to render')
def evaluation(input_file, output, rubric):
    """Render evaluation JSON to HTML."""
    require_repo_context("d4d render evaluation")

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
