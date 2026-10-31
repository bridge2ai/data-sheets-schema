"""Independent request-binding regression for A14/#5162, 2026-10-28.

The released public omission API must bind the response to its saved request.
These tests use its real captured schema, request, parser, and checker offline.
"""
import pytest

from data_sheets_schema import shared_generation as sg
from tests.test_audit_omissions import inputs, prepared, answer, raw  # noqa: F401


@pytest.mark.parametrize('response_identity', ['actual_request', 'different_projection'])
def test_public_omission_response_matches_exact_saved_request(prepared, response_identity):
    request = prepared.request()
    response = answer(prepared, candidate=False)
    if response_identity == 'different_projection':
        # No shared-generation selector was used: this is a different payload
        # from the one the public API prepared and its caller saved.
        projected = {**request['payload'], 'schema': sg.trim_omission_schema(request['payload']['schema'])}
        response['request_sha256'] = sg.sha(sg.canonical(projected))
        assert response['request_sha256'] != request['request_sha256']
    report = prepared.check(raw(response), saved_request=request)
    if response_identity == 'actual_request':
        assert report['protocol_complete']
    else:
        assert not report['protocol_complete'], 'checker accepted a response naming an unsent schema projection'
        assert any(row['code'] == 'request_identity' for row in report['problems'])
