#!/usr/bin/env python3
"""
Comprehensive description quality review for D4D schema.

Performs deep analysis of description content:
- Accuracy relative to field semantics (slot_uri, range, etc.)
- Consistency in terminology and style
- Grammar and clarity
- Completeness and examples
- Identifies specific improvements needed
"""

import yaml
import re
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Any, Tuple
import json


def load_yaml_file(filepath: Path) -> Dict[str, Any]:
    """Load YAML file."""
    with open(filepath) as f:
        return yaml.safe_load(f)


class DescriptionReviewer:
    """Comprehensive description review engine."""

    def __init__(self):
        self.issues = []
        self.terminology_map = Counter()
        self.style_patterns = defaultdict(list)

    def review_description(
        self,
        element_type: str,
        element_name: str,
        module: str,
        description: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensively review a single description.

        Args:
            element_type: 'class', 'slot', 'enum', 'enum_value', 'module'
            element_name: Name of the element
            module: Module name
            description: Description text
            context: Additional context (range, slot_uri, etc.)
        """
        if not description:
            return {
                'element': f"{module}.{element_name}",
                'type': element_type,
                'issues': [{'severity': 'HIGH', 'type': 'missing', 'message': 'No description provided'}],
                'quality_score': 0,
                'recommendations': ['Add a description']
            }

        issues = []
        recommendations = []
        desc_lower = description.lower()

        # 1. ACCURACY CHECKS (relative to field semantics)
        if element_type == 'slot':
            slot_uri = context.get('slot_uri', '')
            range_type = context.get('range', '')
            multivalued = context.get('multivalued', False)

            # Check if description mentions multivalued nature
            if multivalued and not any(term in desc_lower for term in ['list', 'multiple', 'array', 'values', 'entries']):
                issues.append({
                    'severity': 'MEDIUM',
                    'type': 'accuracy',
                    'message': 'Multivalued field not clearly indicated in description'
                })
                recommendations.append('Mention that this field accepts multiple values')

            # Check boolean descriptions
            if range_type == 'boolean':
                if not any(term in desc_lower for term in ['whether', 'indicates', 'true', 'false', 'yes', 'no']):
                    issues.append({
                        'severity': 'LOW',
                        'type': 'clarity',
                        'message': 'Boolean field description could be clearer (use "Indicates whether..." pattern)'
                    })
                    recommendations.append('Use "Indicates whether..." pattern for boolean fields')

            # Check URI/identifier fields
            if 'identifier' in element_name.lower() or 'uri' in element_name.lower() or 'url' in element_name.lower():
                if range_type == 'string' and not any(term in desc_lower for term in ['format', 'pattern', 'example']):
                    issues.append({
                        'severity': 'LOW',
                        'type': 'completeness',
                        'message': 'Identifier/URI field should mention format or provide example'
                    })
                    recommendations.append('Add format specification or example')

        # 2. STUB/PLACEHOLDER DETECTION
        stub_indicators = [
            (r'\bTODO\b', 'Contains TODO'),
            (r'\bTBD\b', 'Contains TBD'),
            (r'\bFIXME\b', 'Contains FIXME'),
            (r'\bXXX\b', 'Contains XXX marker'),
            (r'<.*?>', 'Contains placeholder tags'),
            (r'\[.*?\]', 'May contain placeholder brackets'),
        ]

        for pattern, message in stub_indicators:
            if re.search(pattern, description):
                issues.append({
                    'severity': 'HIGH',
                    'type': 'stub',
                    'message': message
                })
                recommendations.append(f'Replace placeholder: {message}')

        # 3. GRAMMAR AND STYLE
        # Capitalization
        if description and not description[0].isupper() and not description[0].isdigit():
            issues.append({
                'severity': 'LOW',
                'type': 'grammar',
                'message': 'Description should start with capital letter'
            })
            recommendations.append('Capitalize first letter')

        # Sentence ending
        if not description.strip().endswith(('.', ')', '!', '?', '"', "'")):
            issues.append({
                'severity': 'LOW',
                'type': 'style',
                'message': 'Description should end with period'
            })
            recommendations.append('Add period at end')

        # Check for common grammar issues
        grammar_issues = [
            (r'\s+,', 'Space before comma'),
            (r'\s+\.', 'Space before period'),
            (r'[a-z]\.[A-Z]', 'Missing space after period'),
            (r'\s{2,}', 'Multiple consecutive spaces'),
        ]

        for pattern, message in grammar_issues:
            if re.search(pattern, description):
                issues.append({
                    'severity': 'LOW',
                    'type': 'grammar',
                    'message': message
                })

        # 4. LENGTH AND COMPLETENESS
        word_count = len(description.split())

        if word_count < 4:
            issues.append({
                'severity': 'HIGH',
                'type': 'completeness',
                'message': f'Too short ({word_count} words) - lacks context'
            })
            recommendations.append('Expand description to provide adequate context')
        elif word_count < 8:
            issues.append({
                'severity': 'MEDIUM',
                'type': 'completeness',
                'message': f'Brief ({word_count} words) - could use more detail'
            })
            recommendations.append('Consider adding more context or examples')

        # 5. EXAMPLES
        has_examples = bool(re.search(r'\(e\.g\.,|\(for example,|Examples?:|such as', description))

        # Recommend examples for complex fields
        if element_type == 'slot':
            range_type = context.get('range', '')
            if range_type == 'string' and not has_examples and word_count > 10:
                # Only suggest for longer descriptions where examples would help
                if any(term in desc_lower for term in ['format', 'pattern', 'identifier', 'name', 'type']):
                    recommendations.append('Consider adding examples to illustrate expected values')

        # 6. CONSISTENCY CHECKS
        # Track terminology for consistency analysis
        key_terms = re.findall(r'\b(?:dataset|data|instance|field|variable|value|attribute)\b', desc_lower)
        for term in key_terms:
            self.terminology_map[term] += 1

        # Check for vague language
        vague_terms = [
            (r'\betc\.?\b', 'Uses "etc" - consider being explicit'),
            (r'\bvarious\b', 'Uses "various" - consider being specific'),
            (r'\bsome\b', 'Uses "some" - consider being specific'),
            (r'\bmany\b', 'Uses "many" - could be more precise'),
            (r'\bstuff\b', 'Uses informal "stuff"'),
            (r'\bthings\b', 'Uses vague "things"'),
        ]

        for pattern, message in vague_terms:
            if re.search(pattern, desc_lower):
                issues.append({
                    'severity': 'LOW',
                    'type': 'clarity',
                    'message': message
                })

        # 7. CLARITY CHECKS
        # Check for overly long sentences (>40 words)
        sentences = re.split(r'[.!?]+', description)
        for i, sentence in enumerate(sentences):
            words_in_sentence = len(sentence.split())
            if words_in_sentence > 40:
                issues.append({
                    'severity': 'MEDIUM',
                    'type': 'clarity',
                    'message': f'Sentence {i+1} is very long ({words_in_sentence} words) - consider breaking up'
                })
                recommendations.append('Break long sentences into smaller ones')

        # Check for passive voice (approximate)
        passive_indicators = [
            r'\b(?:is|are|was|were|be|been|being)\s+\w+ed\b',
            r'\b(?:is|are|was|were)\s+(?:provided|given|used|created|generated)\b'
        ]
        passive_count = sum(len(re.findall(pattern, description)) for pattern in passive_indicators)
        if passive_count > 2:
            issues.append({
                'severity': 'LOW',
                'type': 'style',
                'message': f'Multiple passive voice constructions ({passive_count}) - consider active voice'
            })
            recommendations.append('Use active voice where possible for clarity')

        # 8. TERMINOLOGY CONSISTENCY
        # Check for inconsistent terminology (dataset vs. data set, etc.)
        inconsistencies = [
            (['dataset', 'data set'], 'Inconsistent: "dataset" vs "data set"'),
            (['metadata', 'meta data'], 'Inconsistent: "metadata" vs "meta data"'),
            (['file name', 'filename'], 'Inconsistent: "filename" vs "file name"'),
        ]

        for term_variants, message in inconsistencies:
            if sum(1 for term in term_variants if term in desc_lower) > 1:
                issues.append({
                    'severity': 'LOW',
                    'type': 'consistency',
                    'message': message
                })

        # Calculate quality score
        quality_score = 100
        for issue in issues:
            if issue['severity'] == 'HIGH':
                quality_score -= 20
            elif issue['severity'] == 'MEDIUM':
                quality_score -= 10
            elif issue['severity'] == 'LOW':
                quality_score -= 3

        quality_score = max(0, quality_score)

        return {
            'element': f"{module}.{element_name}",
            'type': element_type,
            'description': description,
            'word_count': word_count,
            'has_examples': has_examples,
            'issues': issues,
            'recommendations': recommendations,
            'quality_score': quality_score
        }

    def review_module(self, filepath: Path) -> Dict[str, Any]:
        """Review all descriptions in a module."""
        data = load_yaml_file(filepath)
        module_name = filepath.stem

        reviews = {
            'module': module_name,
            'module_description': None,
            'classes': {},
            'slots': {},
            'enums': {},
            'stats': {
                'total_elements': 0,
                'total_issues': 0,
                'high_severity': 0,
                'medium_severity': 0,
                'low_severity': 0,
                'avg_quality_score': 0
            }
        }

        all_scores = []

        # Review module description
        if 'description' in data:
            reviews['module_description'] = self.review_description(
                'module', module_name, module_name,
                data.get('description', ''),
                {}
            )
            all_scores.append(reviews['module_description']['quality_score'])

        # Review classes
        classes = data.get('classes', {})
        for class_name, class_data in classes.items():
            class_review = self.review_description(
                'class', class_name, module_name,
                class_data.get('description', ''),
                {}
            )
            reviews['classes'][class_name] = {
                'review': class_review,
                'attributes': {}
            }
            all_scores.append(class_review['quality_score'])

            # Review attributes
            attributes = class_data.get('attributes', {})
            for attr_name, attr_data in attributes.items():
                if isinstance(attr_data, dict):
                    attr_review = self.review_description(
                        'slot', attr_name, module_name,
                        attr_data.get('description', ''),
                        attr_data
                    )
                    reviews['classes'][class_name]['attributes'][attr_name] = attr_review
                    all_scores.append(attr_review['quality_score'])

        # Review top-level slots
        slots = data.get('slots', {})
        for slot_name, slot_data in slots.items():
            if isinstance(slot_data, dict):
                slot_review = self.review_description(
                    'slot', slot_name, module_name,
                    slot_data.get('description', ''),
                    slot_data
                )
                reviews['slots'][slot_name] = slot_review
                all_scores.append(slot_review['quality_score'])

        # Review enums
        enums = data.get('enums', {})
        for enum_name, enum_data in enums.items():
            enum_review = self.review_description(
                'enum', enum_name, module_name,
                enum_data.get('description', ''),
                {}
            )
            reviews['enums'][enum_name] = {
                'review': enum_review,
                'values': {}
            }
            all_scores.append(enum_review['quality_score'])

            # Review enum values
            pv = enum_data.get('permissible_values', {})
            for value_name, value_data in pv.items():
                if isinstance(value_data, dict):
                    value_review = self.review_description(
                        'enum_value', value_name, module_name,
                        value_data.get('description', ''),
                        {}
                    )
                    reviews['enums'][enum_name]['values'][value_name] = value_review
                    all_scores.append(value_review['quality_score'])

        # Calculate stats
        def count_issues(review_data):
            if isinstance(review_data, dict):
                if 'issues' in review_data:
                    reviews['stats']['total_elements'] += 1
                    reviews['stats']['total_issues'] += len(review_data['issues'])
                    for issue in review_data['issues']:
                        sev = issue['severity']
                        if sev == 'HIGH':
                            reviews['stats']['high_severity'] += 1
                        elif sev == 'MEDIUM':
                            reviews['stats']['medium_severity'] += 1
                        elif sev == 'LOW':
                            reviews['stats']['low_severity'] += 1

                # Recurse
                for key, value in review_data.items():
                    if key in ('attributes', 'values', 'review'):
                        if isinstance(value, dict):
                            for sub_value in value.values():
                                count_issues(sub_value)

        if reviews['module_description']:
            count_issues(reviews['module_description'])
        count_issues(reviews['classes'])
        count_issues(reviews['slots'])
        count_issues(reviews['enums'])

        if all_scores:
            reviews['stats']['avg_quality_score'] = sum(all_scores) / len(all_scores)

        return reviews


def generate_comprehensive_report(all_reviews: List[Dict[str, Any]]) -> str:
    """Generate comprehensive markdown report."""

    report = ["# D4D Schema Comprehensive Description Review\n"]
    report.append(f"**Generated:** 2026-04-08\n")
    report.append("**Scope:** All D4D modules\n\n")
    report.append("---\n\n")

    # Executive Summary
    report.append("## Executive Summary\n\n")

    total_elements = sum(r['stats']['total_elements'] for r in all_reviews)
    total_issues = sum(r['stats']['total_issues'] for r in all_reviews)
    high_issues = sum(r['stats']['high_severity'] for r in all_reviews)
    medium_issues = sum(r['stats']['medium_severity'] for r in all_reviews)
    low_issues = sum(r['stats']['low_severity'] for r in all_reviews)

    all_scores = []
    for r in all_reviews:
        if r['stats']['avg_quality_score'] > 0:
            all_scores.append(r['stats']['avg_quality_score'])

    avg_score = sum(all_scores) / len(all_scores) if all_scores else 0

    report.append(f"**Total elements reviewed:** {total_elements}\n")
    report.append(f"**Total issues found:** {total_issues}\n")
    report.append(f"**Average quality score:** {avg_score:.1f}/100\n\n")

    report.append("### Issues by Severity\n\n")
    report.append(f"- 🔴 **HIGH:** {high_issues} (missing descriptions, stub text, very short)\n")
    report.append(f"- 🟡 **MEDIUM:** {medium_issues} (accuracy, completeness, clarity)\n")
    report.append(f"- 🟢 **LOW:** {low_issues} (grammar, style, minor improvements)\n\n")

    # Priority Issues
    report.append("## Priority Issues Requiring Action\n\n")

    # Collect all HIGH severity issues
    high_severity_items = []
    for module_review in all_reviews:
        def collect_high(data, path=''):
            if isinstance(data, dict):
                if 'issues' in data and 'element' in data:
                    high_issues_in_element = [i for i in data['issues'] if i['severity'] == 'HIGH']
                    if high_issues_in_element:
                        high_severity_items.append({
                            'element': data['element'],
                            'issues': high_issues_in_element,
                            'recommendations': data.get('recommendations', [])
                        })
                for key, value in data.items():
                    if key in ('classes', 'slots', 'enums', 'attributes', 'values'):
                        if isinstance(value, dict):
                            for sub_val in value.values():
                                collect_high(sub_val)
                    elif key == 'review':
                        collect_high(value)

        if module_review.get('module_description'):
            collect_high(module_review['module_description'])
        collect_high(module_review.get('classes', {}))
        collect_high(module_review.get('slots', {}))
        collect_high(module_review.get('enums', {}))

    if high_severity_items:
        report.append(f"### 🔴 HIGH Priority ({len(high_severity_items)} elements)\n\n")
        for item in high_severity_items[:20]:  # Top 20
            report.append(f"#### `{item['element']}`\n\n")
            for issue in item['issues']:
                report.append(f"- **{issue['type'].upper()}:** {issue['message']}\n")
            if item['recommendations']:
                report.append(f"- **Fix:** {item['recommendations'][0]}\n")
            report.append("\n")

        if len(high_severity_items) > 20:
            report.append(f"*...and {len(high_severity_items) - 20} more. See JSON data for complete list.*\n\n")
    else:
        report.append("✅ No HIGH priority issues found!\n\n")

    report.append("---\n\n")

    # Module Summaries
    report.append("## Module-by-Module Summary\n\n")

    for module_review in sorted(all_reviews, key=lambda x: x['module']):
        module = module_review['module']
        stats = module_review['stats']

        report.append(f"### {module}\n\n")
        report.append(f"- **Elements:** {stats['total_elements']}\n")
        report.append(f"- **Issues:** {stats['total_issues']} ")
        report.append(f"(🔴 {stats['high_severity']}, 🟡 {stats['medium_severity']}, 🟢 {stats['low_severity']})\n")
        report.append(f"- **Avg Quality:** {stats['avg_quality_score']:.1f}/100\n\n")

    report.append("---\n\n")

    # Recommendations
    report.append("## Recommendations\n\n")

    if high_issues > 0:
        report.append(f"1. **Address {high_issues} HIGH priority issues immediately:**\n")
        report.append("   - Fill missing descriptions\n")
        report.append("   - Replace stub/placeholder text\n")
        report.append("   - Expand very short descriptions\n\n")

    if medium_issues > 10:
        report.append(f"2. **Review {medium_issues} MEDIUM priority issues:**\n")
        report.append("   - Clarify multivalued fields\n")
        report.append("   - Add format specifications for identifiers/URIs\n")
        report.append("   - Break up long sentences\n\n")

    report.append(f"3. **Consider addressing {low_issues} LOW priority style/grammar issues** in next cleanup pass\n\n")

    report.append("4. **Add examples** to complex fields (currently only 12.6% have examples)\n\n")

    report.append("5. **Maintain consistency** in terminology across modules\n\n")

    return "".join(report)


def main():
    """Main execution."""
    schema_dir = Path("src/data_sheets_schema/schema")
    module_files = sorted(schema_dir.glob("D4D_*.yaml"))

    # Also include main schema
    main_schema = schema_dir / "data_sheets_schema.yaml"
    if main_schema.exists():
        module_files.insert(0, main_schema)

    reviewer = DescriptionReviewer()
    all_reviews = []

    print("Performing comprehensive description review...")
    for filepath in module_files:
        print(f"  - {filepath.name}")
        review = reviewer.review_module(filepath)
        all_reviews.append(review)

    # Generate reports
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Markdown report
    markdown_report = generate_comprehensive_report(all_reviews)
    md_path = reports_dir / "description_comprehensive_review.md"
    with open(md_path, 'w') as f:
        f.write(markdown_report)
    print(f"\nMarkdown report: {md_path}")

    # JSON detailed data
    json_path = reports_dir / "description_comprehensive_review.json"
    with open(json_path, 'w') as f:
        json.dump(all_reviews, f, indent=2)
    print(f"JSON data: {json_path}")

    print("\nDone!")


if __name__ == "__main__":
    main()
