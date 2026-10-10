// Offline DOM checks: no browser process, network, or submitted code execution.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('../../.runs/dom-check/node_modules/jsdom');
const dom=new JSDOM(fs.readFileSync('app/static/index.html','utf8'),{url:'https://lab.invalid',runScripts:'outside-only'});
const w=dom.window,d=w.document;
const terminal=(outcome,evidence=null)=>({id:'run-1',stage:'finished',elapsed:2,terminal:true,counts:{generated:2,valid:2,tested:2,invalid:0,timed_out:0},result:{outcome,message:'Executed finding',evidence,method:'Fixture method',explanation:'',seed:850}});
let current=terminal('inconclusive'),postError=null,imported=false,cancelled=false;
let callbacks=[];w.setTimeout=fn=>{callbacks.push(fn);return callbacks.length};w.clearTimeout=()=>{};
w.fetch=async(path,options={})=>{
 let data;
 if(path==='/api/health')data={runner:{ready:true},provider:{name:'fixture',reachable:true,model:'OFFLINE FIXTURE'}};
 else if(path==='/api/import'){imported=true;data={title:'<script>bad</script>',statement:'Parsed statement',samples:[{stdin:'2 3',stdout:'5'}],warnings:['Review extracted constraints']};}
 else if(path==='/api/runs'){if(postError)return{ok:false,json:async()=>({detail:postError})};data={id:'run-1',stage:'queued',elapsed:0,terminal:false,counts:{}};}
 else if(path.endsWith('/cancel')){cancelled=true;data={cancellation_requested:true};current=terminal('cancelled');}
 else data=current;
 return{ok:true,json:async()=>data};
};
w.eval(fs.readFileSync('app/static/app.js','utf8'));
const flush=async()=>{for(let i=0;i<3;i++)await new Promise(setImmediate);};
const submit=()=>d.getElementById('run-form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
(async()=>{
 await flush();assert.match(d.getElementById('health').textContent,/Docker: ready/);
 d.getElementById('add-sample').click();assert.equal(d.querySelectorAll('.sample').length,2);
 d.querySelector('.sample button').click();assert.equal(d.querySelectorAll('.sample').length,1);
 const fields=d.querySelectorAll('.sample textarea');fields[0].value='2 3';fields[1].value='5';
 d.getElementById('statement').value='Sum';d.getElementById('source').value='int main(){}';
 submit();await flush();assert.equal(d.getElementById('outcome').textContent,'inconclusive');assert.equal(d.getElementById('start').disabled,false);
 postError='Model quota reached';submit();await flush();assert.equal(d.getElementById('error').textContent,postError);assert.equal(d.getElementById('statement').value,'Sum');postError=null;
 const html=new w.File(['ignored'], 'saved.html',{type:'text/html'});Object.defineProperty(d.getElementById('html-file'),'files',{value:[html],configurable:true});d.getElementById('html-file').dispatchEvent(new w.Event('change'));await flush();assert(imported);assert.equal(d.getElementById('title').value,'<script>bad</script>');assert.equal(d.querySelectorAll('script').length,1);
 Object.defineProperty(d.getElementById('cpp-file'),'files',{value:[{size:12,text:async()=> 'int main(){return 7;}'}],configurable:true});d.getElementById('cpp-file').dispatchEvent(new w.Event('change'));await flush();assert.match(d.getElementById('source').value,/return 7/);
 const evidence={stdin:'<img src=x onerror=bad()>',expected:'5',actual:{stdout:'6',status:'ok'},samples_checked:true,validators_agree:true,references_agree:true,primary_code:'def solve(s): return "5"',confirmation_code:'def solve(s): return "5"',candidate_hash:'a',primary_hash:'b',confirmation_hash:'c'};
 current=terminal('corroborated_counterexample',evidence);submit();await flush();assert.equal(d.getElementById('stdin').textContent,evidence.stdin);assert.equal(d.querySelectorAll('img').length,0);
 for(const outcome of ['preparation_failure','unconfirmed_disagreement','provider_failure']){current=terminal(outcome);submit();await flush();assert.equal(d.getElementById('outcome').textContent,outcome.replaceAll('_',' '));assert.match(d.getElementById('source').value,/return 7/);}
 current={id:'run-1',stage:'searching',terminal:false,elapsed:2,counts:{generated:1}};submit();await flush();assert.equal(d.getElementById('cancel').disabled,false);d.getElementById('cancel').click();await flush();assert(cancelled);await callbacks.pop()();await flush();assert.equal(d.getElementById('outcome').textContent,'cancelled');
 assert(d.querySelector('meta[name=viewport]'));assert(/max-width:760px/.test(fs.readFileSync('app/static/style.css','utf8')));
 console.log('Offline DOM journeys passed: paste, uploads, sample edits, evidence escaping, failure retention, cancellation. Visual layout and real browser are not verified.');
 dom.window.close();
})().catch(error=>{console.error(error);process.exitCode=1;dom.window.close();});
