import json
from pathlib import Path
from benchmarks.evaluate import truth


def test_independent_definitions_match_all_fixed_samples():
 for case in json.loads(Path('benchmarks/cases.json').read_text()):
  for sample in case['problem']['samples']:
   assert truth(case['id'],sample['stdin'])==list(map(int,sample['stdout'].split()))


def test_independent_validators_cover_dimensions_and_aggregate_constraints():
 from benchmarks.evaluate import valid
 for case in json.loads(Path('benchmarks/cases.json').read_text()):
  for sample in case['problem']['samples']:assert valid(case['id'],sample['stdin'])
 assert not valid('nonempty-interval','2 -1')
 assert not valid('knapsack','2 3 1 2')
 assert not valid('distinct','2 0 99')
 assert not valid('sum','0 1000')
 assert not valid('cyclic-snowmen','2 1 1 2 3')
 assert not valid('cyclic-snowmen','1 1 1 2 4')
