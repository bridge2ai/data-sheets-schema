#!/usr/bin/env python3
"""
Render rubric10-semantic evaluation JSON files to HTML
"""
import json
from pathlib import Path
from datetime import datetime


def generate_evaluation_html(eval_data, output_path):
    """Generate HTML from evaluation JSON data"""

    metadata = eval_data.get("evaluation_metadata", {})
    element_scores = eval_data.get("element_scores", [])
    summary = eval_data.get("summary_scores", {})
    semantic = eval_data.get("semantic_analysis", {})
    recommendations = eval_data.get("recommendations", {})

    # Calculate overall stats
    total_score = summary.get("total_score", 0)
    max_score = summary.get("total_max_score", 50)
    percentage = summary.get("overall_percentage", 0)

    # Start HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rubric10-Semantic Evaluation: {metadata.get('dataset_id', 'Unknown')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #1a1a1a;
            margin-bottom: 10px;
            font-size: 2em;
        }}

        h2 {{
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #3498db;
        }}

        h3 {{
            color: #34495e;
            margin-top: 20px;
            margin-bottom: 10px;
        }}

        .metadata {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 30px;
            border-left: 4px solid #3498db;
        }}

        .metadata-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
        }}

        .metadata-item {{
            display: flex;
            flex-direction: column;
        }}

        .metadata-label {{
            font-size: 0.85em;
            color: #7f8c8d;
            margin-bottom: 4px;
        }}

        .metadata-value {{
            font-weight: 500;
            color: #2c3e50;
        }}

        .score-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 30px;
        }}

        .score-large {{
            font-size: 3em;
            font-weight: bold;
            margin-bottom: 10px;
        }}

        .score-subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .element {{
            background: #fff;
            border: 1px solid #e1e8ed;
            border-radius: 6px;
            margin-bottom: 20px;
            overflow: hidden;
        }}

        .element-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #e1e8ed;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .element-title {{
            font-weight: 600;
            color: #2c3e50;
        }}

        .element-score {{
            font-size: 1.1em;
            font-weight: bold;
            padding: 5px 15px;
            border-radius: 20px;
            background: #ecf0f1;
        }}

        .score-high {{ background: #2ecc71; color: white; }}
        .score-medium {{ background: #f39c12; color: white; }}
        .score-low {{ background: #e74c3c; color: white; }}

        .sub-element {{
            padding: 15px 20px;
            border-bottom: 1px solid #f1f3f5;
        }}

        .sub-element:last-child {{
            border-bottom: none;
        }}

        .sub-element-name {{
            font-weight: 500;
            color: #34495e;
            margin-bottom: 8px;
        }}

        .sub-element-score {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }}

        .score-1 {{ background: #2ecc71; color: white; }}
        .score-0 {{ background: #e74c3c; color: white; }}

        .detail {{
            margin-top: 8px;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 4px;
            font-size: 0.9em;
        }}

        .detail-label {{
            font-weight: 600;
            color: #7f8c8d;
            margin-right: 5px;
        }}

        .semantic-section {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .validation-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .validation-item {{
            background: white;
            padding: 12px;
            border-radius: 4px;
            border-left: 3px solid #3498db;
        }}

        .gap-list {{
            list-style: none;
            padding: 0;
        }}

        .gap-item {{
            padding: 10px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #e74c3c;
        }}

        .gap-item.medium {{
            border-left-color: #f39c12;
        }}

        .gap-item.low {{
            border-left-color: #95a5a6;
        }}

        .strength {{
            background: #d4edda;
            border-left-color: #28a745;
        }}

        .weakness {{
            background: #f8d7da;
            border-left-color: #dc3545;
        }}

        .recommendation-section {{
            margin-top: 20px;
        }}

        .recommendation-item {{
            padding: 12px;
            margin-bottom: 10px;
            background: #e7f3ff;
            border-radius: 4px;
            border-left: 3px solid #2196f3;
        }}

        .recommendation-item.critical {{
            background: #fee;
            border-left-color: #e74c3c;
        }}

        .recommendation-item.important {{
            background: #fff3cd;
            border-left-color: #ffc107;
        }}

        .timestamp {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e1e8ed;
            color: #7f8c8d;
            font-size: 0.9em;
        }}

        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.8em;
            font-weight: 600;
            margin-left: 8px;
        }}

        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Rubric10-Semantic Evaluation Report</h1>
        <div class="metadata">
            <div class="metadata-grid">
                <div class="metadata-item">
                    <div class="metadata-label">Dataset</div>
                    <div class="metadata-value">{metadata.get('dataset_id', 'Unknown')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Generation Method</div>
                    <div class="metadata-value">{metadata.get('method', 'Unknown')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Evaluator</div>
                    <div class="metadata-value">{metadata.get('evaluator', 'Unknown')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Rubric Type</div>
                    <div class="metadata-value">{metadata.get('rubric_type', 'Unknown')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Temperature</div>
                    <div class="metadata-value">{metadata.get('temperature', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Evaluation Date</div>
                    <div class="metadata-value">{metadata.get('evaluation_timestamp', 'Unknown')}</div>
                </div>
            </div>
        </div>

        <div class="score-card">
            <div class="score-large">{total_score}/{max_score}</div>
            <div class="score-subtitle">{percentage:.1f}% Overall Score</div>
        </div>
"""

    # Add element scores
    html += """
        <h2>Element Scores</h2>
"""

    # Handle both list and dict formats for element_scores
    if isinstance(element_scores, dict):
        # Convert dict to list format
        element_list = []
        for key, value in sorted(element_scores.items()):
            if isinstance(value, dict):
                # Extract element number from key
                elem_num = key.split('_')[1] if '_' in key else '0'

                # Convert sub_elements to sub_element_scores format
                sub_element_scores = []
                if 'sub_elements' in value:
                    # CHORUS/CM4AI/VOICE format with nested sub_elements dict
                    for sub_key, sub_value in sorted(value['sub_elements'].items()):
                        if isinstance(sub_value, dict):
                            # Extract sub-element name from key (e.g., "1.1_persistent_identifier" -> "Persistent Identifier")
                            sub_name = sub_key.split('_', 1)[1].replace('_', ' ').title() if '_' in sub_key else sub_key.replace('_', ' ').title()

                            sub_element_scores.append({
                                'name': sub_name,
                                'fields': sub_value.get('field', sub_value.get('fields', [])),  # Handle both 'field' and 'fields'
                                'score': sub_value.get('score', 0),
                                'rationale': sub_value.get('rationale', 'N/A'),
                                'semantic_notes': sub_value.get('semantic_note', sub_value.get('semantic_notes', ''))  # Handle both variants
                            })

                element_list.append({
                    'element_id': elem_num,
                    'element_name': value.get('element_name', value.get('name', key.replace('_', ' ').title())),
                    'element_score': value.get('element_score', value.get('score', 0)),
                    'element_max_score': value.get('max_score', 5),
                    'element_percentage': value.get('element_score_percentage', value.get('percentage', 0)),
                    'sub_element_scores': sub_element_scores
                })
            else:
                # Value is just a number
                element_list.append({
                    'element_id': key.split('_')[1] if '_' in key else '0',
                    'element_name': key.replace('_', ' ').title(),
                    'element_score': value,
                    'element_max_score': 5,
                    'element_percentage': (value / 5) * 100,
                    'sub_element_scores': []
                })
        element_scores = element_list

    # Also handle array format elements that have sub_elements instead of sub_element_scores
    for element in element_scores:
        # If element has sub_elements but empty sub_element_scores, convert it
        if 'sub_elements' in element and not element.get('sub_element_scores'):
            sub_elem = element['sub_elements']
            converted_subs = []

            if isinstance(sub_elem, list):
                # VOICE format: sub_elements is an array
                for sub in sub_elem:
                    if isinstance(sub, dict):
                        converted_subs.append({
                            'name': sub.get('name', ''),
                            'fields': sub.get('fields_found', sub.get('fields', sub.get('field', []))),
                            'score': sub.get('score', 0),
                            'rationale': sub.get('evidence', sub.get('rationale', 'N/A')),
                            'semantic_notes': sub.get('semantic_note', sub.get('semantic_notes', ''))
                        })
            elif isinstance(sub_elem, dict):
                # Already handled in dict conversion above, but check again for hybrid formats
                for sub_key, sub_value in sorted(sub_elem.items()):
                    if isinstance(sub_value, dict):
                        sub_name = sub_key.split('_', 1)[1].replace('_', ' ').title() if '_' in sub_key else sub_key.replace('_', ' ').title()
                        converted_subs.append({
                            'name': sub_name,
                            'fields': sub_value.get('field', sub_value.get('fields', [])),
                            'score': sub_value.get('score', 0),
                            'rationale': sub_value.get('rationale', 'N/A'),
                            'semantic_notes': sub_value.get('semantic_note', sub_value.get('semantic_notes', ''))
                        })

            element['sub_element_scores'] = converted_subs

    for element in element_scores:
        elem_score = element.get('element_score', 0)
        elem_max = element.get('element_max_score', 5)
        elem_pct = element.get('element_percentage', 0)

        # Determine score class
        if elem_pct >= 80:
            score_class = "score-high"
        elif elem_pct >= 50:
            score_class = "score-medium"
        else:
            score_class = "score-low"

        html += f"""
        <div class="element">
            <div class="element-header">
                <div class="element-title">Element {element.get('element_id')}: {element.get('element_name')}</div>
                <div class="element-score {score_class}">{elem_score}/{elem_max} ({elem_pct:.0f}%)</div>
            </div>
"""

        # Add sub-elements
        for sub in element.get('sub_element_scores', []):
            score = sub.get('score', 0)
            score_class = f"score-{score}"

            html += f"""
            <div class="sub-element">
                <div class="sub-element-name">
                    {sub.get('name')}
                    <span class="sub-element-score {score_class}">{score}/1</span>
                </div>
                <div class="detail">
                    <span class="detail-label">Fields:</span> {', '.join(sub.get('fields', []))}
                </div>
                <div class="detail">
                    <span class="detail-label">Rationale:</span> {sub.get('rationale', 'N/A')}
                </div>
"""

            if sub.get('semantic_notes'):
                html += f"""
                <div class="detail">
                    <span class="detail-label">Semantic Notes:</span> {sub.get('semantic_notes')}
                </div>
"""

            html += """
            </div>
"""

        html += """
        </div>
"""

    # Add semantic analysis
    html += """
        <h2>Semantic Analysis</h2>
"""

    # Identifier validation
    if 'identifier_validation' in semantic:
        id_val = semantic['identifier_validation']
        html += """
        <div class="semantic-section">
            <h3>Identifier Validation</h3>
            <div class="validation-grid">
"""
        for key, value in id_val.items():
            if isinstance(value, str):
                html += f"""
                <div class="validation-item">
                    <strong>{key}:</strong><br>{value}
                </div>
"""
        html += """
            </div>
        </div>
"""

    # Completeness gaps
    if 'completeness_gaps' in semantic:
        gaps = semantic['completeness_gaps']

        html += """
        <h3>Completeness Gaps</h3>
"""

        for priority, gap_list in [('high_priority_missing', 'High Priority'),
                                     ('medium_priority_missing', 'Medium Priority'),
                                     ('low_priority_missing', 'Low Priority')]:
            if priority in gaps and gaps[priority]:
                priority_class = priority.split('_')[0]
                html += f"""
        <h4>{gap_list} Missing Fields</h4>
        <ul class="gap-list">
"""
                for gap in gaps[priority]:
                    html += f"""
            <li class="gap-item {priority_class}">{gap}</li>
"""
                html += """
        </ul>
"""

    # Strengths and weaknesses - check both semantic and top-level
    strengths_list = semantic.get('strengths', eval_data.get('strengths', []))
    weaknesses_list = semantic.get('weaknesses', eval_data.get('weaknesses', []))

    if strengths_list:
        html += """
        <h3>Strengths</h3>
        <ul class="gap-list">
"""
        for strength in strengths_list[:10]:  # Top 10
            html += f"""
            <li class="gap-item strength">{strength}</li>
"""
        html += """
        </ul>
"""

    if weaknesses_list:
        html += """
        <h3>Weaknesses</h3>
        <ul class="gap-list">
"""
        for weakness in weaknesses_list[:10]:  # Top 10
            html += f"""
            <li class="gap-item weakness">{weakness}</li>
"""
        html += """
        </ul>
"""

    # Recommendations - check both recommendations dict and top-level
    if not recommendations:
        recommendations = eval_data.get('recommendations', {})

    if recommendations:
        html += """
        <h2>Recommendations</h2>
"""

        # Check if recommendations is a simple list or a dict with priorities
        if isinstance(recommendations, list):
            html += """
        <div class="recommendation-section">
            <h3>Recommendations</h3>
"""
            for rec in recommendations:
                html += f"""
            <div class="recommendation-item">{rec}</div>
"""
            html += """
        </div>
"""
        elif isinstance(recommendations, dict):
            for priority, rec_list in [('critical', 'Critical'),
                                         ('important', 'Important'),
                                         ('optional', 'Optional')]:
                if priority in recommendations and recommendations[priority]:
                    html += f"""
        <div class="recommendation-section">
            <h3>{rec_list} Recommendations</h3>
"""
                    for rec in recommendations[priority]:
                        html += f"""
            <div class="recommendation-item {priority}">{rec}</div>
"""
                    html += """
        </div>
"""

    # Close HTML
    html += f"""
        <div class="timestamp">
            Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} using Bridge2AI Data Sheets Schema
        </div>
    </div>
</body>
</html>
"""

    # Write HTML file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def main():
    """Process claudecode_agent evaluation JSON files and generate HTML"""

    input_dir = Path("data/evaluation_llm/rubric10_semantic/concatenated")
    output_dir = Path("data/d4d_html/concatenated/claudecode_agent")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find claudecode_agent evaluation files
    eval_files = sorted(input_dir.glob("*claudecode_agent_evaluation.json"))

    if not eval_files:
        print(f"No claudecode_agent evaluation files found in {input_dir}")
        return

    print(f"Found {len(eval_files)} evaluation files to render")
    print(f"Output directory: {output_dir}\n")

    processed_count = 0

    for eval_file in eval_files:
        print(f"Processing: {eval_file.name}")

        try:
            # Read JSON
            with open(eval_file, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)

            # Generate output filename
            project_name = eval_file.stem.replace('_claudecode_agent_evaluation', '')
            output_path = output_dir / f"{project_name}_evaluation.html"

            # Generate HTML
            generate_evaluation_html(eval_data, output_path)

            print(f"  ✅ Generated: {output_path}")
            processed_count += 1

        except Exception as e:
            print(f"  ❌ Error processing {eval_file.name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"Processed {processed_count}/{len(eval_files)} files successfully")
    print(f"HTML files saved in: {output_dir}")


if __name__ == "__main__":
    main()
