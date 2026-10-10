import random


def parse(stdin):
    return list(map(int, stdin.split()))


def render(case):
    return ' '.join(map(str, case)) + '\n'


def valid(case):
    return isinstance(case, list) and len(case) == 2 and all(type(x) is int and -100 <= x <= 100 for x in case)


def solve(stdin):
    return str(sum(parse(stdin)))


def generate(seed, index, mode):
    if mode == 'exhaustive':
        return [index // 5 - 2, index % 5 - 2] if index < 25 else None
    if mode == 'adversarial':
        return [[0, 0], [-100, 100], [100, 100], [-100, -100]][index % 4]
    r = random.Random(seed + index)
    return [r.randint(-100, 100), r.randint(-100, 100)]


def shrink(case):
    return [[0, case[1]], [case[0], 0], [int(case[0] / 2), int(case[1] / 2)]]
