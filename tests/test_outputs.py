import pytest


def test_integer_outputs_ignore_only_whitespace_and_support_large_values():
    from app.outputs import integer_tokens

    assert integer_tokens(' +5\n-7  0 ') == (5, -7, 0)
    assert integer_tokens('9' * 5000)[0] > 10**4999


@pytest.mark.parametrize('output', ['1.0', '1 extra', '', '١'])
def test_malformed_output_is_not_an_integer_answer(output):
    from app.outputs import integer_tokens

    with pytest.raises(ValueError):
        integer_tokens(output)
