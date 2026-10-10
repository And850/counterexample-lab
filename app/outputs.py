import re
import sys

sys.set_int_max_str_digits(0)


def integer_tokens(output: str) -> tuple[int, ...]:
    tokens = output.split()
    if not tokens or any(re.fullmatch(r'[+-]?[0-9]+', token) is None for token in tokens):
        raise ValueError('Expected nonempty signed integer output tokens')
    return tuple(int(token) for token in tokens)
