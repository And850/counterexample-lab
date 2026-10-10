'use strict';
const $ = id => document.getElementById(id);
let activeId = null, timer = null, finalResult = null, importedWarnings = [];
function fail(message) { $('error').textContent = message; }
async function api(path, options) {
  const response = await fetch(path, options);
  let data; try { data = await response.json(); } catch { throw new Error('Invalid server response.'); }
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Input validation failed. Review the statement, source and complete samples.');
  return data;
}
function addSample(input='', output='') {
  const row = document.createElement('div'); row.className='sample';
  for (const [name,value] of [['Input',input],['Output',output]]) {
    const label=document.createElement('label'); label.textContent=name;
    const field=document.createElement('textarea'); field.value=value; field.required=true; field.maxLength=name==='Input'?100000:65536;
    field.setAttribute('aria-label','Sample '+name.toLowerCase()); label.append(field); row.append(label);
  }
  const button=document.createElement('button'); button.type='button'; button.textContent='Remove sample';
  button.onclick=()=>row.remove(); row.append(button); $('samples').append(row);
}
async function health() {
  try { const h=await api('/api/health'); $('health').textContent=`Docker: ${h.runner.ready?'ready':'unavailable'} · ${h.provider.name}: ${h.provider.reachable?'reachable':'unavailable'}${h.provider.model?' ('+h.provider.model+')':''}. Generation is checked during each run.`; }
  catch(e) { $('health').textContent=e.message; }
}
$('refresh').onclick=health;
$('add-sample').onclick=()=>addSample();
$('html-file').onchange=async event=>{
  const file=event.target.files[0]; if(!file)return;
  if(file.size>5*1024*1024){fail('HTML exceeds the 5 MiB limit.');return;}
  const form=new FormData();form.append('file',file);fail('');
  try { const problem=await api('/api/import',{method:'POST',body:form});
    $('title').value=problem.title; $('statement').value=problem.statement; $('samples').replaceChildren();
    for(const s of problem.samples)addSample(s.stdin,s.stdout);
    if(!problem.samples.length)addSample(); importedWarnings=problem.warnings; $('warnings').textContent=problem.warnings.join('\n');
  }catch(e){fail(e.message);}event.target.value='';
};
$('cpp-file').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  if(file.size>262144){fail('Source exceeds the 256 KiB limit.');return;}
  $('source').value=await file.text();event.target.value='';
};
function busy(value){$('start').disabled=value;$('cancel').disabled=!value;}
function render(snapshot) {
  $('progress-panel').hidden=false;$('stage').textContent=snapshot.stage;$('elapsed').textContent=Math.round(snapshot.elapsed)+' s';
  $('counts').textContent=Object.entries(snapshot.counts).map(([name,n])=>`${name}: ${n}`).join(' · ');
  if(!snapshot.terminal)return;
  clearTimeout(timer);activeId=null;busy(false);finalResult=snapshot.result;
  const result=snapshot.result;$('result').hidden=false;
  $('outcome').textContent=result.outcome.replaceAll('_',' ');$('message').textContent=result.message;$('method').textContent=result.method||'No testing module prepared.';
  $('explanation-panel').hidden=!result.explanation;$('explanation').textContent=result.explanation;
  $('evidence').hidden=!result.evidence;
  if(result.evidence){const e=result.evidence;
    $('stdin').textContent=e.stdin;$('expected').textContent=e.expected;$('actual').textContent=e.actual.stdout||`[${e.actual.status}, exit ${e.actual.exit_code??'unknown'}]`;
    $('checks').textContent=`Sample checks: ${e.samples_checked?'passed':'incomplete'} · Both input validators: ${e.validators_agree?'agree':'not established'} · Reference outputs: ${e.references_agree?'agree':'not established'} · Seed: ${result.seed}`;
    $('primary-code').textContent=e.primary_code;$('confirmation-code').textContent=e.confirmation_code||'No checked independent reference.';
    $('hashes').textContent=`SHA-256\nCandidate: ${e.candidate_hash}\nPrimary: ${e.primary_hash}\nConfirmation: ${e.confirmation_hash}`;
  }
}
async function poll() {
  if(!activeId)return;
  try {render(await api('/api/runs/'+activeId));if(activeId)timer=setTimeout(poll,1000);}
  catch(e){fail(e.message);if(activeId)timer=setTimeout(poll,2000);}
}
$('run-form').onsubmit=async event=>{
  event.preventDefault();fail('');const rows=[...$('samples').querySelectorAll('.sample')];
  const samples=rows.map(row=>{const fields=row.querySelectorAll('textarea');return{stdin:fields[0].value,stdout:fields[1].value};});
  if(!samples.length){fail('Add at least one complete sample.');return;}
  const payload={problem:{title:$('title').value,statement:$('statement').value,samples,warnings:importedWarnings},source:$('source').value,seed:Number($('seed').value)};
  busy(true);$('result').hidden=true;
  try {const snapshot=await api('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});activeId=snapshot.id;render(snapshot);poll();}
  catch(e){busy(false);fail(e.message);}
};
$('cancel').onclick=async()=>{if(!activeId)return;try{await api('/api/runs/'+activeId+'/cancel',{method:'POST'});$('stage').textContent='Cancellation requested…';$('cancel').disabled=true;}catch(e){fail(e.message);}};
$('download').onclick=()=>{if(!finalResult)return;const url=URL.createObjectURL(new Blob([JSON.stringify(finalResult,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='counterexample-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
addSample();health();
