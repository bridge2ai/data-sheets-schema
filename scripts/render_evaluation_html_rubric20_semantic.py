#!/usr/bin/env python3
"""
Render rubric20-semantic evaluation JSON files to HTML
"""
import json
from pathlib import Path
from datetime import datetime


def generate_evaluation_html(eval_data, output_path):
    """Generate HTML from rubric20 evaluation JSON data"""

    # Extract metadata from root level and nested structures
    project = eval_data.get("project", "Unknown")
    rubric = eval_data.get("rubric", "rubric20-semantic")
    d4d_file = eval_data.get("d4d_file", "N/A")
    method = eval_data.get("method", "N/A")
    timestamp = eval_data.get("evaluation_timestamp", "N/A")
    model_info = eval_data.get("model", {})

    # Extract overall score
    overall = eval_data.get("overall_score", {})
    total_score = overall.get("total_points", 0)
    max_score = overall.get("max_points", 84)
    percentage = overall.get("percentage", 0)

    # Calculate grade
    if percentage >= 95:
        grade = "A+"
    elif percentage >= 90:
        grade = "A"
    elif percentage >= 85:
        grade = "B+"
    elif percentage >= 80:
        grade = "B"
    elif percentage >= 75:
        grade = "C+"
    elif percentage >= 70:
        grade = "C"
    else:
        grade = "D"

    # Extract categories (with nested questions)
    categories = eval_data.get("categories", [])

    # Extract semantic analysis
    semantic = eval_data.get("semantic_analysis", {})

    # Start HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rubric20-Semantic Evaluation: {project}</title>
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
            max-width: 1400px;
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

        h4 {{
            color: #5a6c7d;
            margin-top: 15px;
            margin-bottom: 8px;
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

        .category-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .category-card {{
            background: #fff;
            border: 1px solid #e1e8ed;
            border-radius: 6px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}

        .category-header {{
            font-size: 0.85em;
            color: #7f8c8d;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .category-title {{
            font-size: 1.1em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 15px;
        }}

        .category-score {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
            margin-bottom: 5px;
        }}

        .category-percentage {{
            color: #7f8c8d;
            font-size: 0.95em;
        }}

        .question {{
            background: #fff;
            border: 1px solid #e1e8ed;
            border-radius: 6px;
            margin-bottom: 20px;
            overflow: hidden;
        }}

        .question-header {{
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #e1e8ed;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .question-title {{
            font-weight: 600;
            color: #2c3e50;
        }}

        .question-number {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-right: 8px;
        }}

        .question-score {{
            font-size: 1.1em;
            font-weight: bold;
            padding: 5px 15px;
            border-radius: 20px;
        }}

        .score-perfect {{ background: #2ecc71; color: white; }}
        .score-high {{ background: #27ae60; color: white; }}
        .score-good {{ background: #f39c12; color: white; }}
        .score-medium {{ background: #e67e22; color: white; }}
        .score-low {{ background: #e74c3c; color: white; }}

        .question-body {{
            padding: 20px;
        }}

        .detail {{
            margin-bottom: 15px;
        }}

        .detail-label {{
            font-weight: 600;
            color: #34495e;
            margin-bottom: 5px;
            display: block;
        }}

        .detail-content {{
            color: #555;
            line-height: 1.5;
        }}

        .evidence-list {{
            list-style: none;
            padding: 0;
        }}

        .evidence-item {{
            padding: 8px 12px;
            margin-bottom: 5px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #3498db;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}

        .semantic-checks {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 4px;
            padding: 12px;
            margin-top: 10px;
        }}

        .semantic-section {{
            background: #e8f4f8;
            border: 1px solid #3498db;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .semantic-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}

        .semantic-item {{
            background: white;
            padding: 12px;
            border-radius: 4px;
            border-left: 3px solid #3498db;
        }}

        .semantic-item.passed {{
            border-left-color: #2ecc71;
        }}

        .semantic-item.failed {{
            border-left-color: #e74c3c;
        }}

        .semantic-item.warning {{
            border-left-color: #f39c12;
        }}

        .list-section {{
            margin-top: 20px;
        }}

        .list-item {{
            padding: 10px 15px;
            margin-bottom: 8px;
            background: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #3498db;
        }}

        .list-item.strength {{
            background: #d4edda;
            border-left-color: #28a745;
        }}

        .list-item.weakness {{
            background: #f8d7da;
            border-left-color: #dc3545;
        }}

        .list-item.recommendation {{
            background: #e7f3ff;
            border-left-color: #2196f3;
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

        .category-section {{
            margin-bottom: 40px;
        }}

        .issue-item {{
            background: #fff;
            border: 1px solid #e1e8ed;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 10px;
        }}

        .issue-type {{
            font-weight: 600;
            color: #e74c3c;
            margin-bottom: 5px;
        }}

        .issue-severity {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            margin-left: 10px;
        }}

        .severity-high {{ background: #e74c3c; color: white; }}
        .severity-medium {{ background: #f39c12; color: white; }}
        .severity-low {{ background: #95a5a6; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Rubric20-Semantic Evaluation Report</h1>
        <div class="metadata">
            <div class="metadata-grid">
                <div class="metadata-item">
                    <div class="metadata-label">Project</div>
                    <div class="metadata-value">{project}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">D4D File</div>
                    <div class="metadata-value">{Path(d4d_file).name}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Evaluator Model</div>
                    <div class="metadata-value">{model_info.get('name', 'Unknown')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Rubric Type</div>
                    <div class="metadata-value">{rubric}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Temperature</div>
                    <div class="metadata-value">{model_info.get('temperature', 'N/A')}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Evaluation Date</div>
                    <div class="metadata-value">{timestamp}</div>
                </div>
            </div>
        </div>

        <div class="score-card">
            <div class="score-large">{total_score}/{max_score}</div>
            <div class="score-subtitle">{percentage:.1f}% Overall Score · Grade: {grade}</div>
        </div>

        <h2>Category Performance</h2>
        <div class="category-grid">
"""

    # Add category cards
    for cat in categories:
        cat_name = cat.get('name', 'Unknown')
        questions = cat.get('questions', [])

        # Calculate category totals from questions
        cat_score = sum(q.get('score', 0) for q in questions)
        cat_max = sum(q.get('max_score', 5) for q in questions)
        cat_pct = (cat_score / cat_max * 100) if cat_max > 0 else 0

        html += f"""
            <div class="category-card">
                <div class="category-header">Category</div>
                <div class="category-title">{cat_name}</div>
                <div class="category-score">{cat_score}/{cat_max}</div>
                <div class="category-percentage">{cat_pct:.1f}%</div>
            </div>
"""

    html += """
        </div>
"""

    # Add questions organized by category
    html += """
        <h2>Question-Level Assessment</h2>
"""

    for cat in categories:
        cat_name = cat.get('name', 'Unknown')
        questions = cat.get('questions', [])
        html += f"""
        <div class="category-section">
            <h3>{cat_name}</h3>
"""

        for q in questions:
            q_num = q.get('id', 0)
            q_text = q.get('name', 'Unknown')
            q_desc = q.get('description', '')
            q_score = q.get('score', 0)
            q_max = q.get('max_score', 5)
            q_pct = (q_score / q_max * 100) if q_max > 0 else 0
            q_type = q.get('score_type', '0-5 scale')
            q_label = q.get('score_label', '')
            justification = q.get('quality_note', '')
            evidence = q.get('evidence', '')
            semantic_analysis = q.get('semantic_analysis', '')

            # Determine score class
            if q_pct == 100:
                score_class = "score-perfect"
            elif q_pct >= 80:
                score_class = "score-high"
            elif q_pct >= 60:
                score_class = "score-good"
            elif q_pct >= 40:
                score_class = "score-medium"
            else:
                score_class = "score-low"

            html += f"""
            <div class="question">
                <div class="question-header">
                    <div class="question-title">
                        <span class="question-number">Q{q_num}.</span>
                        {q_text}
                        <span class="badge badge-success">{q_type}</span>
                    </div>
                    <div class="question-score {score_class}">{q_score}/{q_max}</div>
                </div>
                <div class="question-body">
                    <div class="detail">
                        <span class="detail-label">Assessment</span>
                        <div class="detail-content">{justification}</div>
                    </div>
"""

            if evidence:
                html += f"""
                    <div class="detail">
                        <span class="detail-label">Evidence Found</span>
                        <div class="detail-content">{evidence}</div>
                    </div>
"""

            if semantic_analysis:
                html += f"""
                    <div class="detail">
                        <span class="detail-label">Semantic Analysis</span>
                        <div class="detail-content">{semantic_analysis}</div>
                    </div>
"""

            html += """
                </div>
            </div>
"""

        html += """
        </div>
"""

    # Add semantic analysis summary
    html += """
        <h2>Semantic Analysis Summary</h2>
"""

    # Correctness validations
    if 'correctness_checks' in semantic:
        corr = semantic['correctness_checks']
        html += """
        <div class="semantic-section">
            <h3>Correctness Validations</h3>
            <div class="semantic-grid">
"""
        for key, value in corr.items():
            status_class = "passed" if "valid" in str(value).lower() or "correct" in str(value).lower() else ""
            html += f"""
                <div class="semantic-item {status_class}">
                    <strong>{key.replace('_', ' ').title()}:</strong><br>{value}
                </div>
"""
        html += """
            </div>
        </div>
"""

    # Consistency checks
    if 'consistency_checks' in semantic:
        cons = semantic['consistency_checks']
        html += """
        <div class="semantic-section">
            <h3>Consistency Checks</h3>
"""
        if isinstance(cons, dict):
            html += """
            <div class="semantic-grid">
"""
            for key, value in cons.items():
                if key in ['passed', 'failed', 'warnings']:
                    html += f"""
                <div class="semantic-item">
                    <strong>{key.title()}:</strong> {value}
                </div>
"""
            html += """
            </div>
"""
        html += """
        </div>
"""

    # Issues detected
    if 'issues_detected' in semantic:
        issues = semantic['issues_detected']
        if issues:
            html += """
        <h3>Issues Detected</h3>
"""
            for issue in issues:
                issue_type = issue.get('type', 'Unknown')
                severity = issue.get('severity', 'low')
                fields = issue.get('fields_involved', [])
                recs = issue.get('recommendations', '')

                html += f"""
        <div class="issue-item">
            <div class="issue-type">
                {issue_type}
                <span class="issue-severity severity-{severity}">{severity.upper()}</span>
            </div>
            <div><strong>Fields:</strong> {', '.join(fields) if isinstance(fields, list) else fields}</div>
            <div><strong>Recommendation:</strong> {recs}</div>
        </div>
"""

    # Strengths
    strengths = overall.get('strengths', [])
    if strengths:
        html += """
        <h2>Key Strengths</h2>
        <div class="list-section">
"""
        for strength in strengths:
            html += f"""
            <div class="list-item strength">{strength}</div>
"""
        html += """
        </div>
"""

    # Weaknesses
    weaknesses = overall.get('weaknesses', [])
    if weaknesses:
        html += """
        <h2>Areas for Improvement</h2>
        <div class="list-section">
"""
        for weakness in weaknesses:
            html += f"""
            <div class="list-item weakness">{weakness}</div>
"""
        html += """
        </div>
"""

    # Recommendations
    recommendations = overall.get('recommendations', [])
    if recommendations:
        html += """
        <h2>Recommendations</h2>
        <div class="list-section">
"""
        for rec in recommendations:
            html += f"""
            <div class="list-item recommendation">{rec}</div>
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
    """Process rubric20-semantic claudecode_agent evaluation JSON files and generate HTML"""

    input_dir = Path("data/evaluation_llm/rubric20_semantic/concatenated")
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
            output_path = output_dir / f"{project_name}_evaluation_rubric20.html"

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
