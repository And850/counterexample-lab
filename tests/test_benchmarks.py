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


def test_evaluation_provenance_uses_selected_provider(monkeypatch):
 from benchmarks.evaluate import provenance
 monkeypatch.setenv('MODEL_PROVIDER','gemini')
 monkeypatch.setenv('GEMINI_MODEL','reviewed-gemini-model')
 monkeypatch.setenv('LMSTUDIO_MODEL','unrelated-local-model')
 assert provenance()=={'provider':'gemini','model':'reviewed-gemini-model','api':'google-genai'}
 monkeypatch.setenv('MODEL_PROVIDER','lmstudio')
 monkeypatch.setenv('LMSTUDIO_API','native')
 assert provenance()=={'provider':'lmstudio','model':'unrelated-local-model','api':'native'}


def test_ground_truth_rejects_out_of_scope_dimensions_before_enumeration():
 import pytest
 with pytest.raises(ValueError,match='constraints'):
  truth('knapsack','9 1 '+'1 1 '*9)
 with pytest.raises(ValueError,match='constraints'):
  truth('nonempty-interval','9 '+'1 '*9)
