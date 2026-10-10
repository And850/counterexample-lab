import threading
import time

from fastapi.testclient import TestClient
from app.contracts import CounterexampleResult
from app.main import app

PAYLOAD={'problem':{'statement':'Sum two integers','samples':[{'stdin':'2 3','stdout':'5'}]},'source':'int main(){}','seed':1}


def client():
    return TestClient(app, base_url='http://localhost')


def test_same_origin_and_local_host():
    c=client()
    assert c.post('/api/runs',json=PAYLOAD,headers={'Origin':'https://evil.example'}).status_code==403
    assert c.get('/api/health',headers={'Host':'evil.example'}).status_code==400


def test_import_and_validation():
    c=client()
    data=open('tests/fixtures/statement.html','rb').read()
    response=c.post('/api/import',files={'file':('problem.html',data,'text/html')})
    assert response.status_code==200
    assert len(response.json()['samples'])==1
    assert c.post('/api/runs',json={**PAYLOAD,'problem':{'statement':'sum','samples':[]}}).status_code==422
    assert c.get('/api/runs/unknown').status_code==404


def test_job_lifecycle_and_single_concurrency(monkeypatch,tmp_path):
    import app.main as main
    ready=threading.Event()
    def fake_search(*args,**kwargs):
        ready.set()
        while not kwargs['cancel'].is_set():time.sleep(.01)
        return CounterexampleResult(outcome='cancelled',message='Cancelled')
    monkeypatch.setattr(main,'search',fake_search)
    monkeypatch.setattr(main,'readiness',lambda:{'ready':True})
    monkeypatch.setattr(main,'provider_readiness',lambda:{'configured':True,'reachable':True})
    monkeypatch.setattr(main,'RUNS_ROOT',tmp_path)
    c=client()
    first=c.post('/api/runs',json=PAYLOAD)
    assert first.status_code==202,first.text
    id=first.json()['id'];assert ready.wait(2)
    try:
        time.sleep(.05)
        assert c.get('/api/runs/'+id).json()['elapsed']>.02
        assert c.post('/api/runs',json=PAYLOAD).status_code==409
    finally:
        assert c.post('/api/runs/'+id+'/cancel').status_code==200
        for _ in range(100):
            snapshot=c.get('/api/runs/'+id).json()
            if snapshot['terminal']:break
            time.sleep(.02)
    assert snapshot['result']['outcome']=='cancelled'
    assert snapshot['elapsed']==snapshot['result']['elapsed']


def test_readiness_failure_rejects_job(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main,'readiness',lambda:{'ready':False,'message':'Unavailable'})
    assert client().post('/api/runs',json=PAYLOAD).status_code==503


def test_noninteger_sample_output_is_rejected_before_run():
    body={**PAYLOAD,'problem':{'statement':'Unsupported float output','samples':[{'stdin':'2 3','stdout':'5.0'}]}}
    assert client().post('/api/runs',json=body).status_code==422
