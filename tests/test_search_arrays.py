from app.contracts import ConfirmationBundle, GeneratedBundle, ProblemInput, SamplePair
from tests.test_search import FixtureProvider
import threading,time

ARRAY_CODE='''import random

def parse(s):
 a=list(map(int,s.split()));return a[1:] if a and a[0]==len(a)-1 else []
def render(c):return str(len(c))+'\\n'+' '.join(map(str,c))
def valid(c):return isinstance(c,list) and 1<=len(c)<=8 and all(type(x)==int and -9<=x<=9 for x in c)
def solve(s):
 a=parse(s);return str(max(sum(a[i:j]) for i in range(len(a)) for j in range(i+1,len(a)+1)))
def generate(seed,index,mode):
 if mode=='exhaustive':return [-2,-1] if index==0 else None
 r=random.Random(seed+index);return [r.randint(-9,9) for _ in range(r.randint(1,8))]
def shrink(c):return [c[:i]+c[i+1:] for i in range(len(c))]+[[0 if j==i else x for j,x in enumerate(c)] for i in range(len(c))]
'''
CONFIRM='''def valid_input(s):
 try:
  x=list(map(int,s.split()));return len(x)>1 and x[0]==len(x)-1 and 1<=x[0]<=8 and all(-9<=a<=9 for a in x[1:])
 except ValueError:return False
def solve(s):
 a=list(map(int,s.split()))[1:];best=None
 for i in range(len(a)):
  acc=0
  for j in range(i,len(a)):
   acc+=a[j];best=acc if best is None else max(best,acc)
 return str(best)
'''


class ArrayProvider(FixtureProvider):
 def generate_primary(self,problem,deadline):
  self.calls+=1
  return GeneratedBundle(code=ARRAY_CODE,method='Enumerate every nonempty interval',small_input_limits='n<=8')
 def generate_confirmation(self,problem,deadline):
  self.calls+=1
  return ConfirmationBundle(code=CONFIRM,method='Independent interval enumeration')


def test_greedy_empty_interval_bug_preserves_coupled_lengths(tmp_path):
 from app.search import search
 source='#include <bits/stdc++.h>\nint main(){int n,x;std::cin>>n;long long s=0,b=0;while(n--){std::cin>>x;s=std::max(0LL,s+x);b=std::max(b,s);}std::cout<<b;}'
 p=ProblemInput(statement='1<=n<=8, -9<=a[i]<=9. Largest sum of a nonempty contiguous interval.',samples=[SamplePair(stdin='3\n1 -2 3',stdout='3')])
 result=search(p,source,provider=ArrayProvider(),root=tmp_path,deadline=time.monotonic()+30,cancel=threading.Event(),max_cases=5)
 assert result.outcome=='corroborated_counterexample',result.message
 tokens=list(map(int,result.evidence.stdin.split()))
 assert tokens[0]==len(tokens)-1 and tokens[0]>=1
 assert result.evidence.actual.stdout=='0' and int(result.evidence.expected)<0
