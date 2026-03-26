#!/usr/bin/env python3
"""
Unit tests for evaluate_d4d.py

Tests D4D evaluation framework functionality.
"""

import unittest
import tempfile
import shutil
import yaml
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.evaluation.evaluate_d4d import (
        D4DEvaluator,
        SubElementScore,
        ElementScore,
        QuestionScore,
        D4DEvaluation
    )
except ImportError as e:
    print(f"Warning: Could not import evaluate_d4d: {e}", file=sys.stderr)
    D4DEvaluator = None
    SubElementScore = None
    ElementScore = None
    QuestionScore = None
    D4DEvaluation = None


class TestD4DEvaluation(unittest.TestCase):
    """Test D4D evaluation framework functionality."""

    def setUp(self):
        """Set up test fixtures - create temporary directories with test files."""
        if D4DEvaluator is None:
            self.skipTest("evaluate_d4d module not available")

        self.test_dir = tempfile.mkdtemp()
        self.test_path = Path(self.test_dir)

        # Create minimal rubric10 test file
        self.rubric10_data = {
            'rubric10': {
                'elements': [
                    {
                        'id': 1,
                        'name': 'Discovery',
                        'description': 'Dataset discovery and findability',
                        'sub_elements': [
                            {
                                'name': 'Title',
                                'field': 'title'
                            },
                            {
                                'name': 'Description',
                                'field': 'description'
                            }
                        ]
                    }
                ]
            }
        }

        self.rubric10_file = self.test_path / "rubric10.txt"
        with open(self.rubric10_file, 'w') as f:
            yaml.dump(self.rubric10_data, f)

        # Create minimal rubric20 test file
        self.rubric20_data = {
            'rubric20': {
                'questions': [
                    {
                        'id': 1,
                        'name': 'Dataset Title',
                        'description': 'Is the dataset title present?',
                        'category': 'Structural Completeness',
                        'score_type': 'pass_fail',
                        'max_score': 1,
                        'field': 'title'
                    },
                    {
                        'id': 2,
                        'name': 'Dataset Description',
                        'description': 'Is the description comprehensive?',
                        'category': 'Metadata Quality',
                        'score_type': 'numeric',
                        'max_score': 5,
                        'field': 'description'
                    }
                ]
            }
        }

        self.rubric20_file = self.test_path / "rubric20.txt"
        with open(self.rubric20_file, 'w') as f:
            yaml.dump(self.rubric20_data, f)

        # Create sample D4D YAML file (flat format)
        self.d4d_data_flat = {
            'title': 'Test Dataset',
            'description': 'A comprehensive test dataset description',
            'keywords': ['test', 'sample'],
            'license_and_use_terms': {
                'description': 'CC-BY-4.0'
            }
        }

        self.d4d_file_flat = self.test_path / "test_d4d_flat.yaml"
        with open(self.d4d_file_flat, 'w') as f:
            yaml.dump(self.d4d_data_flat, f)

        # Create sample D4D YAML file (DatasetCollection format)
        self.d4d_data_collection = {
            'DatasetCollection': {
                'resources': [
                    {
                        'title': 'Test Dataset Collection',
                        'description': 'A test dataset in collection format',
                        'keywords': ['test', 'collection']
                    }
                ]
            }
        }

        self.d4d_file_collection = self.test_path / "test_d4d_collection.yaml"
        with open(self.d4d_file_collection, 'w') as f:
            yaml.dump(self.d4d_data_collection, f)

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'test_dir'):
            shutil.rmtree(self.test_dir)

    def test_evaluator_initialization(self):
        """Test D4DEvaluator initialization."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        self.assertIsNotNone(evaluator)
        self.assertEqual(evaluator.rubric10_path, self.rubric10_file)
        self.assertEqual(evaluator.rubric20_path, self.rubric20_file)

    def test_load_rubric10(self):
        """Test rubric10 loading."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        rubric10 = evaluator.rubric10
        self.assertIsNotNone(rubric10)
        self.assertIn('rubric10', rubric10)
        self.assertIn('elements', rubric10['rubric10'])

    def test_load_rubric20(self):
        """Test rubric20 loading."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        rubric20 = evaluator.rubric20
        self.assertIsNotNone(rubric20)
        self.assertIn('rubric20', rubric20)
        self.assertIn('questions', rubric20['rubric20'])

    def test_load_d4d_yaml_flat(self):
        """Test loading flat D4D YAML."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        data = evaluator._load_d4d_yaml(self.d4d_file_flat)
        self.assertIsNotNone(data)
        self.assertEqual(data['title'], 'Test Dataset')
        self.assertEqual(data['description'], 'A comprehensive test dataset description')

    def test_load_d4d_yaml_collection(self):
        """Test loading DatasetCollection D4D YAML."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        data = evaluator._load_d4d_yaml(self.d4d_file_collection)
        self.assertIsNotNone(data)
        self.assertEqual(data['title'], 'Test Dataset Collection')
        self.assertEqual(data['description'], 'A test dataset in collection format')

    def test_extract_field_value_simple(self):
        """Test extracting simple field value."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        value = evaluator._extract_field_value(self.d4d_data_flat, 'title')
        self.assertEqual(value, 'Test Dataset')

    def test_extract_field_value_nested(self):
        """Test extracting nested field value."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        value = evaluator._extract_field_value(
            self.d4d_data_flat,
            'license_and_use_terms.description'
        )
        self.assertEqual(value, 'CC-BY-4.0')

    def test_extract_field_value_nonexistent(self):
        """Test extracting nonexistent field value."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        value = evaluator._extract_field_value(self.d4d_data_flat, 'nonexistent_field')
        self.assertIsNone(value)

    def test_is_field_present_string(self):
        """Test field presence check for string field."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        is_present, found_values = evaluator._is_field_present(
            self.d4d_data_flat,
            ['title']
        )

        self.assertTrue(is_present)
        self.assertGreater(len(found_values), 0)
        self.assertIn('title', found_values[0])

    def test_is_field_present_list(self):
        """Test field presence check for list field."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        is_present, found_values = evaluator._is_field_present(
            self.d4d_data_flat,
            ['keywords']
        )

        self.assertTrue(is_present)
        self.assertGreater(len(found_values), 0)

    def test_is_field_present_dict(self):
        """Test field presence check for dict field."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        is_present, found_values = evaluator._is_field_present(
            self.d4d_data_flat,
            ['license_and_use_terms']
        )

        self.assertTrue(is_present)
        self.assertGreater(len(found_values), 0)

    def test_is_field_present_empty_string(self):
        """Test field presence check for empty string."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        data = {'title': '', 'description': 'Valid'}
        is_present, found_values = evaluator._is_field_present(data, ['title'])

        self.assertFalse(is_present)

    def test_is_field_present_missing(self):
        """Test field presence check for missing field."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        is_present, found_values = evaluator._is_field_present(
            self.d4d_data_flat,
            ['nonexistent_field']
        )

        self.assertFalse(is_present)
        self.assertEqual(len(found_values), 0)

    def test_score_rubric10_element(self):
        """Test scoring a rubric10 element."""
        evaluator = D4DEvaluator(
            str(self.rubric10_file),
            str(self.rubric20_file)
        )

        element = self.rubric10_data['rubric10']['elements'][0]
        score = evaluator._score_rubric10_element(self.d4d_data_flat, element)

        self.assertIsInstance(score, ElementScore)
        self.assertEqual(score.element_id, 1)
        self.assertEqual(score.name, 'Discovery')
        self.assertEqual(len(score.sub_element_scores), 2)
        # Both title and description are present
        self.assertEqual(score.total_score, 2.0)

    def test_sub_element_score_dataclass(self):
        """Test SubElementScore dataclass."""
        score = SubElementScore(
            name='Test Element',
            field_paths=['test.field'],
            score=1,
            found_values=['test.field: test value']
        )

        self.assertEqual(score.name, 'Test Element')
        self.assertEqual(score.score, 1)
        self.assertEqual(len(score.found_values), 1)

    def test_element_score_dataclass(self):
        """Test ElementScore dataclass."""
        sub_scores = [
            SubElementScore('Sub1', ['field1'], 1, ['value1']),
            SubElementScore('Sub2', ['field2'], 0, [])
        ]

        score = ElementScore(
            element_id=1,
            name='Test Element',
            description='Test description',
            sub_element_scores=sub_scores,
            total_score=1.0,
            max_score=2
        )

        self.assertEqual(score.element_id, 1)
        self.assertEqual(score.total_score, 1.0)
        self.assertEqual(len(score.sub_element_scores), 2)

    def test_question_score_dataclass(self):
        """Test QuestionScore dataclass."""
        score = QuestionScore(
            question_id=1,
            name='Test Question',
            description='Test description',
            category='Test Category',
            score_type='numeric',
            score=3.0,
            max_score=5,
            score_label='Moderate',
            found_values=['value1']
        )

        self.assertEqual(score.question_id, 1)
        self.assertEqual(score.score, 3.0)
        self.assertEqual(score.max_score, 5)

    def test_d4d_evaluation_dataclass(self):
        """Test D4DEvaluation dataclass."""
        evaluation = D4DEvaluation(
            project='TEST',
            method='test',
            file_path='/test/path.yaml',
            timestamp='2024-01-01',
            rubric10_scores=[],
            rubric20_scores=[],
            rubric10_total=25.0,
            rubric10_max=50,
            rubric10_percentage=50.0,
            rubric20_total=42.0,
            rubric20_max=84,
            rubric20_percentage=50.0
        )

        self.assertEqual(evaluation.project, 'TEST')
        self.assertEqual(evaluation.method, 'test')
        self.assertEqual(evaluation.rubric10_total, 25.0)
        self.assertEqual(evaluation.rubric20_total, 42.0)


if __name__ == '__main__':
    unittest.main()
