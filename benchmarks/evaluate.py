"""Real model evaluation: deliberately separate from deterministic regression tests."""
import json
import argparse
import hashlib
import os
from pathlib import Path
import time
from dotenv import load_dotenv
from app.contracts import ProblemInput
from app.search import search
from app.provider import PRIMARY, CONFIRM


def truth(id,stdin):
 a=list(map(int,stdin.split()))
 if id=='sum':return [sum(a)]
 if id=='distinct':return [len(set(a[1:]))]
 if id=='nonempty-interval':
  v=a[1:];return [max(sum(v[i:j]) for i in range(len(v)) for j in range(i+1,len(v)+1))]
 if id=='knapsack':
  n,W=a[:2];items=list(zip(a[2::2],a[3::2]));return [max(sum(items[i][1] for i in range(n) if m>>i&1) for m in range(1<<n) if sum(items[i][0] for i in range(n) if m>>i&1)<=W)]
 if id=='cyclic-snowmen':
  pos=1;out=[];checked_size=0
  for _ in range(a[0]):
   n=a[pos];checked_size+=n
   if n>10 or checked_size>100:raise ValueError("Ground-truth check exceeds reviewed tiny bounds")
   pos+=1;v=a[pos:pos+n];b=a[pos+n:pos+2*n];c=a[pos+2*n:pos+3*n];pos+=3*n
   out.append(sum(all(v[(i+r)%n]<b[(j+r)%n]<c[(k+r)%n] for r in range(n)) for i in range(n) for j in range(n) for k in range(n)))
  return out
 raise ValueError('Unknown benchmark')


def valid(id, stdin):
 try:
  a=list(map(int,stdin.split()))
  if id=='sum':return len(a)==2 and all(-100<=x<=100 for x in a)
  if id in ('distinct','nonempty-interval'):
   low,high=(0,5) if id=='distinct' else (-9,9)
   return bool(a) and 1<=a[0]<=8 and len(a)==a[0]+1 and all(low<=x<=high for x in a[1:])
  if id=='knapsack':return len(a)>=2 and 1<=a[0]<=8 and 1<=a[1]<=20 and len(a)==2+2*a[0] and all(1<=x<=10 for x in a[2::2]) and all(1<=x<=20 for x in a[3::2])
  if id=='cyclic-snowmen':
   if not a or not 1<=a[0]<=5000:return False
   pos=1;total=0
   for _ in range(a[0]):
    n=a[pos];pos+=1;total+=n
    if not 1<=n<=5000 or len(a)<pos+3*n or not all(1<=x<=3*n for x in a[pos:pos+3*n]):return False
    pos+=3*n
   return pos==len(a) and total<=5000
  return False
 except (ValueError,IndexError,TypeError):return False


def main():
 parser=argparse.ArgumentParser();parser.add_argument('--attempt',type=int,default=1);args=parser.parse_args()
 load_dotenv();root=Path('.runs/evaluation');root.mkdir(parents=True,exist_ok=True)
 path=Path('benchmarks/results.json')
 records=json.loads(path.read_text()) if path.exists() else []
 version=hashlib.sha256((PRIMARY+CONFIRM).encode()).hexdigest()
 for case in json.loads(Path('benchmarks/cases.json').read_text()):
  for kind in ('wrong','correct'):
   print(case['id'],kind,'attempt',args.attempt,flush=True)
   result=search(ProblemInput.model_validate(case['problem']),case[kind],seed=850,deadline=time.monotonic()+180,root=root,on_progress=lambda stage,counts,elapsed:print(round(elapsed,1),stage,flush=True))
   (root/(case['id']+'-'+kind+'-attempt'+str(args.attempt)+'.json')).write_text(result.model_dump_json(indent=2))
   verified=False;input_valid=False;actual_disagrees=None
   if result.evidence:
    input_valid=valid(case['id'],result.evidence.stdin)
    try:
     expected=truth(case['id'],result.evidence.stdin)
     verified=list(map(int,result.evidence.expected.split()))==expected
     try:actual_disagrees=list(map(int,result.evidence.actual.stdout.split()))!=expected
     except ValueError:actual_disagrees=True
    except (ValueError,IndexError,TypeError):pass
   record={'problem':case['id'],'candidate':kind,'attempt':args.attempt,'prompt_version':version,'provider':os.getenv('MODEL_PROVIDER','lmstudio'),'model':os.getenv('LMSTUDIO_MODEL','counterexample-local'),'outcome':result.outcome,'elapsed':round(result.elapsed,2),'counts':result.counts.model_dump(),'ground_truth_checked':result.evidence is not None,'ground_truth_agrees':verified,'input_valid':input_valid,'actual_disagrees':actual_disagrees,'message':result.message}
   records.append(record);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(records,indent=2));temporary.replace(path);print(record,flush=True)
 return records


if __name__=='__main__':main()
