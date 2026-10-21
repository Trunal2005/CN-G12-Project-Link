import * as dashjs from 'dashjs';
import {Controller,ewma,features,predict,validateModel,type Forest,type Observation} from '../abr/core';
import {playableBuffer} from './measurements';
export type Event=Record<string,any>&{kind:string,t:number};
export async function api(path:string,body?:unknown){const r=await fetch('/api'+path,body===undefined?{cache:'no-store'}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});if(!r.ok)throw Error(`${r.status}: ${await r.text()}`);return r.json();}
export type Snapshot={buffer:number,time:number,throughput:number|null,forecast:number|null,rendered:string,requested:string,stalls:number,state:string,predictor:string,reason:string,points:any[],transfers:any[],decisions:Event[]};
export const empty:Snapshot={buffer:0,time:0,throughput:null,forecast:null,rendered:'—',requested:'—',stalls:0,state:'Ready',predictor:'Warmup',reason:'Start a fresh session to observe decisions.',points:[],transfers:[],decisions:[]};
export class Lab{
 player:any;sid='';t0=performance.now();history:Observation[]=[];queue:Event[]=[];events:Event[]=[];model:Forest|null=null;
 control=new Controller();timer:any;observer:PerformanceObserver|null=null;snapshot:Snapshot={...empty,points:[],transfers:[],decisions:[]};
 stopped=false;finishing=false;cleanup:(()=>void)[]=[];pending:Promise<void>|null=null;finishPromise:Promise<any>|null=null;
 waiting=false;started=false;deliberate=false;seeks=false;epoch=0;sequence=0;ruleCalls=0;inventory=new Map<string,any>();requestCounter=0;requestedInitialized=false;
 constructor(public video:HTMLVideoElement,public update:(s:Snapshot)=>void){}
 now(){return (performance.now()-this.t0)/1000;}
 buffer(){return playableBuffer(this.video.buffered,this.video.currentTime);}
 emit(kind:string,data:Record<string,any>={}){const e={kind,t:this.now(),seq:this.sequence++,epoch:this.epoch,...data};this.queue.push(e);this.events.push(e);if(this.events.length>10000)this.events.splice(0,1000);return e;}
 flush():Promise<void>{
  if(this.pending)return this.pending;
  this.pending=(async()=>{while(this.queue.length){const rows=this.queue.slice(0,500);await api(`/sessions/${this.sid}/telemetry`,{events:rows});this.queue.splice(0,rows.length);}})().finally(()=>{this.pending=null;});return this.pending;
 }
 sample(){
  const buffer=this.buffer(),time=this.video.currentTime;
  this.emit('sample',{buffer,value:time,decoded_frames:this.video.getVideoPlaybackQuality?.().totalVideoFrames??0,rule_calls:this.ruleCalls});
  this.snapshot={...this.snapshot,buffer,time,points:[...this.snapshot.points.slice(-119),{t:this.now(),buffer,quality:this.snapshot.rendered,requested:this.snapshot.requested,stalled:this.waiting}]};
 }
 resources(entries:PerformanceEntry[]){
  for(const raw of entries){
   const r=raw as PerformanceResourceTiming,asset=r.name.split('/').at(-1)!,known=this.inventory.get(asset);
   if(!r.name.includes(`/media/${this.sid}/`)||!known||known.representation==='4')continue;
   const end=(r.responseEnd-this.t0)/1000,start=(r.startTime-this.t0)/1000,duration=r.duration/1000;
   if(duration<=0||r.encodedBodySize!==known.bytes||r.transferSize===0||(r.responseStatus!==undefined&&r.responseStatus!==200)){
    this.emit('excluded',{t:end,asset,reason:'Incomplete/cached/non-200 video body or size mismatch',size:r.encodedBodySize,start,duration:Math.max(0,duration)});continue;
   }
   const previous=this.history.at(-1);
   if(previous&&start<previous.end){this.emit('excluded',{t:end,asset,reason:'Overlapping video request excluded from causal history'});continue;}
   const boundary=this.history.length,decision=this.events.filter(e=>e.kind==='decision'&&e.epoch===this.epoch&&e.boundary===boundary&&e.t<=start&&e.representation===known.representation).at(-1);
   const o={throughput:8*r.encodedBodySize/duration,size:r.encodedBodySize,duration,start,end,idle:previous?Math.max(0,start-previous.end):0};
   this.emit('segment',{t:end,start,first_byte:(r.responseStart-this.t0)/1000,throughput:o.throughput,duration,size:o.size,asset,stream_type:'video',representation:known.representation,request_id:`${asset}:${start}`,media_start:known.start,media_duration:known.duration,boundary,decision_id:decision?.decision_id,model_checksum:decision?.model_checksum,timing_source:'ResourceTiming encodedBodySize / full request duration'});
   this.snapshot.transfers=[...this.snapshot.transfers.slice(-119),{t:end,throughput:o.throughput,forecast:decision?.value??null}];this.history.push(o);this.snapshot.throughput=o.throughput;
  }
  performance.clearResourceTimings();
 }
 async start(config:any){
  this.t0=performance.now();this.sid=(await api('/sessions',config)).id;localStorage.setItem('stallguard-last',this.sid);
  const inventory=await api('/assets');for(const s of inventory.segments)this.inventory.set(s.asset,s);
  try{const m=await api('/models/current');if(validateModel(m))this.model=m;}catch{}
  this.snapshot.predictor=config.policy==='default'?'dash.js default':config.policy==='ml'&&!this.model?'historical fallback':'warmup EWMA';
  const player=this.player=dashjs.MediaPlayer().create();
  player.updateSettings({debug:{logLevel:0},streaming:{buffer:{bufferTimeDefault:12,bufferTimeAtTopQuality:12,bufferTimeAtTopQualityLongForm:12,fastSwitchEnabled:false},cacheInitSegments:false}} as any);
  if(config.policy!=='default'){
   const rules=Object.fromEntries(['throughputRule','bolaRule','insufficientBufferRule','switchHistoryRule','droppedFramesRule','abandonRequestsRule','l2ARule','loLPRule'].map(k=>[k,{active:false}]));const lab=this;
   function StallGuardRule(this:any){const sw=(window as any).dashjs.FactoryMaker.getClassFactoryByName('SwitchRequest'),ruleContext=this.context;return{getClassName:()=> 'StallGuardRule',reset:()=>{},getSwitchRequest(context:any){
    const result=sw(ruleContext).create();if(context.getMediaType()!=='video')return result;lab.ruleCalls++;
    const reps=player.getRepresentationsByType('video').sort((a:any,b:any)=>a.bandwidth-b.bandwidth);if(!reps.length)return result;
    const boundary=lab.history.length;
    if(lab.control.boundary!==boundary){
     const x=features(lab.history),begin=performance.now(),source=config.policy==='ml'&&lab.model&&x?'random forest':config.policy==='ml'&&!lab.model?'historical fallback':x?'EWMA':'warmup EWMA';
     const forecast=source==='random forest'?predict(lab.model!,x!):ewma(lab.history),inference_ms=performance.now()-begin,choice=lab.control.decide(reps,forecast,lab.buffer(),boundary);
     const event=lab.emit('decision',{boundary,decision_id:`${lab.epoch}:${boundary}`,value:forecast,buffer:lab.buffer(),representation:String(reps[choice.index].id),predictor:source,reason:choice.reason,features:x??undefined,inference_ms,model_checksum:source==='random forest'?(lab.model as any).checksum:undefined,controller_version:'shared-buffer-v2-append-only'});
     lab.snapshot={...lab.snapshot,forecast,predictor:source,reason:choice.reason,decisions:[...lab.snapshot.decisions.slice(-24),event]};
    }
    result.representation=reps[lab.control.selected];result.priority=1;result.rule='StallGuardRule';result.reason={name:'StallGuardRule',boundary,epoch:lab.epoch};return result;
   }};}
   player.addABRCustomRule('qualitySwitchRules','StallGuardRule',((context:any)=>({create:()=>StallGuardRule.call({context})})) as any);
   player.updateSettings({streaming:{abr:{rules,initialBitrate:{video:300}}}} as any);
  }
  performance.clearResourceTimings();performance.setResourceTimingBufferSize(1000);this.observer=new PerformanceObserver(list=>this.resources(list.getEntries()));this.observer.observe({type:'resource'});
  const ev=dashjs.MediaPlayer.events;
  player.on(ev.FRAGMENT_LOADING_STARTED,(e:any)=>{const r=e.request;if(!r?.url)return;this.emit('request',{asset:r.url.split('/').at(-1),request_id:`r${this.requestCounter++}`,stream_type:r.mediaType,request_type:r.type,representation:r.representation?String(r.representation.id):undefined,retry_attempts:r.retryAttempts??0,media_start:Number.isFinite(r.startTime)?r.startTime:undefined});if(!this.requestedInitialized&&r.mediaType==='video'&&r.type==='MediaSegment'&&r.representation){this.requestedInitialized=true;this.emit('requested',{representation:String(r.representation.id),value:r.representation.bandwidth,media_time:this.video.currentTime,reason:'initial request assignment'});this.snapshot.requested=`${r.representation.height}p`;}});
  for(const [name,kind] of [[ev.QUALITY_CHANGE_REQUESTED,'requested'],[ev.QUALITY_CHANGE_RENDERED,'rendered']] as const)player.on(name,(e:any)=>{if(e.mediaType!=='video')return;const r=e.newRepresentation;this.emit(kind,{representation:String(r.id),value:r.bandwidth,media_time:this.video.currentTime});this.snapshot[kind]=`${r.height}p`;});
  player.on(ev.ERROR,(e:any)=>{this.emit('error',{reason:String(JSON.stringify(e.error)??'Player error').slice(0,490),media_time:this.video.currentTime});this.snapshot.state='Playback error';this.update({...this.snapshot});});
  for(const name of ['playing','waiting','pause','seeking','seeked','ended','error']){
   const fn=()=>{
    const buffer=this.buffer();
    if(name==='waiting'&&this.started&&!this.deliberate&&!this.seeks&&!this.waiting&&buffer<.25){this.waiting=true;this.snapshot.stalls++;this.snapshot.state='Stalled';}
    if(name==='playing'){this.started=true;this.waiting=false;this.deliberate=false;this.seeks=false;this.snapshot.state='Playing';}
    if(name==='pause'&&!this.video.ended){this.deliberate=true;this.waiting=false;this.snapshot.state='Paused';this.emit('interaction',{reason:'user pause; profile clock continues'});}
    if(name==='seeking'){this.seeks=true;this.waiting=false;this.control=new Controller();this.history=[];this.epoch++;this.emit('interaction',{reason:'seek resets history and decision epoch'});}
    this.emit(name,{buffer,media_time:this.video.currentTime});if(name==='ended')void this.stop('finished').catch(e=>{this.snapshot.state=String(e);this.update({...this.snapshot});});
   };this.video.addEventListener(name,fn);this.cleanup.push(()=>this.video.removeEventListener(name,fn));
  }
  const pagehide=()=>{if(this.stopped||this.finishing)return;this.sample();this.emit('close',{reason:'page left; partial run',media_time:this.video.currentTime});const body=new Blob([JSON.stringify({events:this.queue.slice(0,500)})],{type:'application/json'});navigator.sendBeacon(`/api/sessions/${this.sid}/abandon`,body);};
  window.addEventListener('pagehide',pagehide);this.cleanup.push(()=>window.removeEventListener('pagehide',pagehide));
  this.emit('intent');this.snapshot.state='Starting';this.update({...this.snapshot});player.initialize(this.video,`/media/${this.sid}/stream.mpd`,true);
  const settings=player.getSettings() as any;this.emit('configuration',{settings:JSON.parse(JSON.stringify({abr:settings.streaming.abr,buffer:settings.streaming.buffer,cacheInitSegments:settings.streaming.cacheInitSegments})),model_checksum:(this.model as any)?.checksum,controller_version:'shared-buffer-v2-append-only'});
  this.timer=setInterval(()=>{this.sample();this.update({...this.snapshot});void this.flush().catch(e=>{this.snapshot.state=String(e);this.update({...this.snapshot});});},1000);return this.sid;
 }
 stop(status='cancelled'):Promise<any>{
  if(this.finishPromise)return this.finishPromise;
  this.finishing=true;
  this.finishPromise=(async()=>{
   clearInterval(this.timer);if(this.observer){this.resources(this.observer.takeRecords());this.observer.disconnect();}
   this.sample();this.emit('close',{reason:`session ${status}`,media_time:this.video.currentTime});this.cleanup.forEach(f=>f());this.cleanup=[];this.player?.reset();
   await this.flush();let result;
   for(let i=0;i<50;i++){try{result=await api(`/sessions/${this.sid}/finish`,{status});break;}catch(e){if(i===49||!String(e).includes('409'))throw e;await new Promise(r=>setTimeout(r,100));}}
   this.stopped=true;this.finishing=false;this.snapshot.state=status;this.update({...this.snapshot});return result;
  })().catch(e=>{this.finishing=false;this.finishPromise=null;throw e;});return this.finishPromise;
 }
}
