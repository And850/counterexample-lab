"""Summarize every live attempt without converting failed preparation into coverage."""
import json
from pathlib import Path


def main():
 records=json.loads(Path('benchmarks/results.json').read_text())
 cases=json.loads(Path('benchmarks/cases.json').read_text())
 attempts=sorted({r.get('attempt',1) for r in records})
 lines=['# Live evaluation','',f'{len(records)} recorded runs across {len(cases)} fixed problems. Seed: 850. See `models.json` for loaded model/configuration and `prompt-versions.json` for prompt text. Every failed preparation or service request is retained.','']
 covered=set();false_correct=[];qualifying_rounds=[]
 for attempt in attempts:
  group=[r for r in records if r.get('attempt',1)==attempt]
  successes=[r for r in group if r['candidate']=='wrong' and r['outcome']=='corroborated_counterexample' and r.get('input_valid') and r['ground_truth_agrees'] and r.get('actual_disagrees') and r['elapsed']<=180 and not r.get('elapsed_is_lower_bound')]
  covered.update(r['problem'] for r in successes)
  expected={(c['id'],kind) for c in cases for kind in ('wrong','correct')}
  completed=all(r['outcome']!='evaluation_interrupted' and not r.get('elapsed_is_lower_bound') for r in group)
  if completed and len(group)==len(expected) and {(r['problem'],r['candidate']) for r in group}==expected and len({r['problem'] for r in successes})>=3:
   qualifying_rounds.append(attempt)
  false_correct.extend(r for r in group if r['candidate']=='correct' and r['outcome']=='corroborated_counterexample')
  lines.extend([f'## Attempt round {attempt}','',f'{len(group)}/10 runs recorded. {len(successes)}/5 wrong controls produced independently reviewed, valid corroborated evidence within 180 seconds.','', '| Problem | Candidate | Outcome | Seconds | Tested | Ground truth checked |','|---|---|---|---:|---:|---|'])
  for r in group:
   check='agrees' if r.get('ground_truth_checked') and r['ground_truth_agrees'] and r.get('input_valid') else 'not checked' if not r.get('ground_truth_checked') else 'failed'
   lines.append(f"| {r['problem']} | {r['candidate']} | {r['outcome']} | {'>=' if r.get('elapsed_is_lower_bound') else ''}{r['elapsed']:.2f} | {r['counts']['tested']} | {check} |")
  lines.append('')
  if any(r.get('elapsed_is_lower_bound') for r in group):lines.extend(['Interrupted-attempt time is the last logged progress, a lower bound (>=), not a completed run duration.',''])
 gate=bool(qualifying_rounds) and not false_correct
 lines.extend(['## Acceptance assessment','',f'Observed coverage across the recorded rounds: **{len(covered)}/5** wrong-control problems. False corroborated findings on correct controls: **{len(false_correct)}**. Minimum target (3/5 in a complete ten-run round, and zero false findings): **'+('met on these fixed problems' if gate else 'not met')+'**; this is not a guarantee of general performance.','', 'Repeated rounds use fresh model generations and are reported separately. Coverage across rounds is not a first-attempt success rate. Preparation failures and inconclusive searches are not evidence of correctness. Several controls may fail preparation; the table makes that visible.','', 'Independent benchmark validators check dimensions, value ranges and original aggregate limits. Independently authored definitions compare expected outputs with ground truth; cyclic-array enumeration is bounded to n<=10 and sum n<=100 so evaluation cannot run an unbounded host workload. The raw result messages in `results.json` retain failure reasons.',''])
 Path('benchmarks/report.md').write_text('\n'.join(lines))
 print('Reported',len(records),'runs; coverage',len(covered),'/5; gate',gate)


if __name__=='__main__':main()
