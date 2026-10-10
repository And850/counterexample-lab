"""Explicit live end-to-end check, never part of the ordinary test suite."""
import json
from pathlib import Path
import time
from dotenv import load_dotenv
from app.contracts import ProblemInput, SamplePair
from app.search import search


def main():
    load_dotenv()
    problem=ProblemInput(statement='Input exactly two whitespace separated integers a,b, -100 <= a,b <= 100. Output their sum as one integer.',samples=[SamplePair(stdin='2 3',stdout='5')])
    source='#include <bits/stdc++.h>\nint main(){long long a,b;std::cin>>a>>b;std::cout<<std::abs(a+b);}'
    result=search(problem,source,deadline=time.monotonic()+180,root=Path('.runs'),max_cases=512,on_progress=lambda stage,counts,elapsed:print(f'{elapsed:.1f}s {stage}',flush=True))
    path=Path('.runs/live-smoke-result.json');path.write_text(result.model_dump_json(indent=2));path.chmod(0o600)
    print(json.dumps({'outcome':result.outcome,'message':result.message,'elapsed':result.elapsed,'input':result.evidence.stdin if result.evidence else None}))
    return 0 if result.outcome=='corroborated_counterexample' else 1


if __name__=='__main__':raise SystemExit(main())
