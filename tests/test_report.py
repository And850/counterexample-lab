import json
from pathlib import Path
from benchmarks.report import main


def record(problem,attempt):
 return {'problem':problem,'candidate':'wrong','attempt':attempt,'outcome':'corroborated_counterexample','input_valid':True,'ground_truth_checked':True,'ground_truth_agrees':True,'actual_disagrees':True,'elapsed':10,'counts':{'tested':1}}


def test_partial_rounds_cannot_pass_gate_by_combining_lucky_cases(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);Path('benchmarks').mkdir()
 Path('benchmarks/cases.json').write_text(json.dumps([{'id':str(i)} for i in range(5)]))
 Path('benchmarks/results.json').write_text(json.dumps([record(str(i),i+1) for i in range(3)]))
 main()
 report=Path('benchmarks/report.md').read_text()
 assert '**3/5**' in report and '**not met**' in report


def test_wrong_reference_or_invalid_input_is_not_coverage(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);Path('benchmarks').mkdir()
 Path('benchmarks/cases.json').write_text(json.dumps([{'id':str(i)} for i in range(5)]))
 records=[record(str(i),1) for i in range(5)]
 records[0]['input_valid']=False;records[1]['ground_truth_agrees']=False;records[2]['actual_disagrees']=False
 records += [{**record(str(i),1),'candidate':'correct','outcome':'inconclusive'} for i in range(5)]
 Path('benchmarks/results.json').write_text(json.dumps(records));main()
 assert '**not met**' in Path('benchmarks/report.md').read_text()


def test_complete_round_can_meet_gate_but_false_correct_finding_revokes_it(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);Path('benchmarks').mkdir()
 Path('benchmarks/cases.json').write_text(json.dumps([{'id':str(i)} for i in range(5)]))
 records=[record(str(i),1) for i in range(5)]
 records[3]['outcome']=records[4]['outcome']='inconclusive'
 records += [{**record(str(i),1),'candidate':'correct','outcome':'inconclusive'} for i in range(5)]
 Path('benchmarks/results.json').write_text(json.dumps(records));main()
 assert '**met on these fixed problems**' in Path('benchmarks/report.md').read_text()
 records[-1]['outcome']='corroborated_counterexample'
 Path('benchmarks/results.json').write_text(json.dumps(records));main()
 assert '**not met**' in Path('benchmarks/report.md').read_text()


def test_interrupted_attempt_discloses_elapsed_lower_bound(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);Path('benchmarks').mkdir()
 Path('benchmarks/cases.json').write_text(json.dumps([{'id':str(i)} for i in range(5)]))
 interrupted={**record('0',1),'outcome':'evaluation_interrupted','elapsed_is_lower_bound':True}
 Path('benchmarks/results.json').write_text(json.dumps([interrupted]));main()
 report=Path('benchmarks/report.md').read_text()
 assert '>=10.00' in report and 'last logged progress' in report and '**not met**' in report


def test_interrupted_correct_control_prevents_complete_round_acceptance(tmp_path,monkeypatch):
 monkeypatch.chdir(tmp_path);Path('benchmarks').mkdir()
 Path('benchmarks/cases.json').write_text(json.dumps([{'id':str(i)} for i in range(5)]))
 records=[record(str(i),1) for i in range(5)]
 records[3]['outcome']=records[4]['outcome']='inconclusive'
 records += [{**record(str(i),1),'candidate':'correct','outcome':'inconclusive'} for i in range(5)]
 records[-1].update(outcome='evaluation_interrupted',elapsed_is_lower_bound=True)
 Path('benchmarks/results.json').write_text(json.dumps(records));main()
 assert '**not met**' in Path('benchmarks/report.md').read_text()
