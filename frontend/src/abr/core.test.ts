import {test} from 'node:test';
import assert from 'node:assert/strict';
import {Controller,features,predict,validateModel,FEATURE_NAMES} from './core';
import fs from 'node:fs';
import {playableBuffer} from '../player/measurements';
import {compatibleSessions} from '../components/compatibility';
const reps=[{id:'0',height:240,bandwidth:300000},{id:'1',height:360,bandwidth:600000},{id:'2',height:480,bandwidth:1200000},{id:'3',height:720,bandwidth:2500000}];
test('cold start, low buffer, boundary idempotence and causal hysteresis',()=>{
 const c=new Controller();assert.equal(c.decide(reps,5000000,12,0).index,0);
 assert.equal(c.decide(reps,5000000,12,1).index,0);
 for(let i=0;i<10;i++)assert.equal(c.decide(reps,5000000,12,1).index,0);
 assert.equal(c.decide(reps,5000000,12,2).index,1);
 assert.equal(c.decide(reps,5000000,1,3).index,0);
});
test('counterfactual forecast genuinely changes selection with same state',()=>{
 const low=new Controller(),high=new Controller();
 for(let i=0;i<5;i++){low.decide(reps,400000,12,i);high.decide(reps,5000000,12,i);}
 assert.equal(low.selected,0);assert.ok(high.selected>low.selected);
});
test('feature warmup and known vector',()=>{
 assert.equal(features([]),null);
 const h=Array.from({length:5},(_,i)=>({throughput:i+1,duration:2,size:100,start:0,end:1,idle:.5}));
 assert.deepEqual(features(h),[1,2,3,4,5,3,Math.sqrt(2),1,2,.5,100]);
});
test('real exported forest matches sklearn vectors including float32 boundaries',()=>{
 const path='../data/models/forest.json';
 if(!fs.existsSync(path))throw Error('Train real model before numerical consistency test');
 const model=JSON.parse(fs.readFileSync(path,'utf8'));assert.ok(validateModel(model));
 const cases=JSON.parse(fs.readFileSync('../data/models/parity.json','utf8'));
 for(const c of cases)assert.ok(Math.abs(predict(model,c.x)-c.expected)<1e-6,`${c.expected}`);
 assert.equal(validateModel({...model,feature_names:FEATURE_NAMES.slice(1)}),false);
});

test('discontinuous ranges never count future disjoint media as current buffer',()=>{
 const r={length:2,start:(i:number)=>[0,7][i],end:(i:number)=>[4,12][i]} as TimeRanges;
 assert.equal(playableBuffer(r,3),1);assert.equal(playableBuffer(r,5),0);assert.equal(playableBuffer(r,8),4);
});
test('malformed model falls back rather than throwing or fractional tree indexing',()=>{
 assert.equal(validateModel({schema:'forest-v1',feature_names:FEATURE_NAMES,trees:{length:1}} as any),false);
 const m={schema:'forest-v1',feature_names:FEATURE_NAMES,trees:[{left:[1.2,-1],right:[1,-1],feature:[0,-2],threshold:[1,0],value:[0,1]}]};assert.equal(validateModel(m as any),false);
});
test('fair comparisons need full bundle/source/settings identity and real ML use',()=>{
 const meta={status:'finished',policy:'ml',asset_fingerprint:'whole-bundle',source_identity:'code',common_settings_identity:'common',summary:{interacted:false,observed_s:40,forest_prediction_count:8}};
 assert.ok(compatibleSessions([{meta},{meta:{...meta}}]));assert.equal(compatibleSessions([{meta},{meta:{...meta,asset_fingerprint:'different'}}]),false);
 assert.equal(compatibleSessions([{meta:{...meta,summary:{...meta.summary,forest_prediction_count:0}}}]),false);
});
