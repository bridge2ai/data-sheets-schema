"""F15: topic words do not infer study groups."""
from data_sheets_schema.rendering.human_readable_renderer import HumanReadableRenderer


def test_topics_do_not_select_a_study_specific_group():
    renderer = HumanReadableRenderer.__new__(HumanReadableRenderer)
    for value in ('diabetes', 'insulin', 'oral', 'lifestyle', 'ocean sensor'):
        assert renderer._infer_category_names([['row', value]]) == ['Category 1']
