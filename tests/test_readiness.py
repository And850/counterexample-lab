import pytest


def test_validates_lmstudio_json_in_normal_content():
    from app.readiness import validate_smoke

    response = {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"status":"ok","sum":5}'}}]}
    assert validate_smoke(response) == 'content'


def test_validates_known_lmstudio_reasoning_field_compatibility():
    from app.readiness import validate_smoke

    response = {'choices': [{'finish_reason': 'stop', 'message': {'content': '', 'reasoning_content': '{"status":"ok","sum":5}'}}]}
    assert validate_smoke(response) == 'reasoning_content'


@pytest.mark.parametrize('response', [
    {'choices': [{'finish_reason': 'length', 'message': {'content': '{"status":"ok","sum":5}'}}]},
    {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"status":"ok","sum":6}'}}]},
    {'choices': [{'finish_reason': 'stop', 'message': {'content': '{"status":"ok","sum":"5"}'}}]},
    {'choices': [{'finish_reason': 'stop', 'message': {'content': '', 'reasoning_content': 'I think the sum is 5'}}]},
])
def test_invalid_or_truncated_smoke_is_not_ready(response):
    from app.readiness import validate_smoke

    with pytest.raises(ValueError):
        validate_smoke(response)
