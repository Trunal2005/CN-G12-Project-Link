"""Non-destructive audit runner: explicit output directory; frozen media/model."""
import argparse,asyncio,json,time,hashlib,statistics,csv
from pathlib import Path
import httpx
from playwright.async_api import async_playwright

def save(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf-8')

async def finish(client,sid,status='finished'):
    for _ in range(100):
        r=await client.post(f'/api/sessions/{sid}/finish',json={'status':status})
        if r.status_code!=409:r.raise_for_status();return r.json()
        await asyncio.sleep(.05)
    raise RuntimeError('Transfers did not drain')

async def transport(base,out):
    path=out/'transport';path.mkdir(exist_ok=False);report={}
    async with httpx.AsyncClient(base_url=base,trust_env=False,timeout=60) as c:
        calibration=[]
        for concurrency in [1,2]:
            sid=(await c.post('/api/sessions',json={'profile':'stable','scale':.5,'purpose':'calibration'})).json()['id'];lat=[];done=False
            async def body():
                size=0
                for _ in range(2):
                    r=await c.get(f'/media/{sid}/chunk-3-00001.m4s');r.raise_for_status();size+=len(r.content)
                return size
            async def controls():
                while not done:
                    t=time.perf_counter();r=await c.get('/api/health');r.raise_for_status();lat.append(time.perf_counter()-t);await asyncio.sleep(.1)
            ctl=asyncio.create_task(controls());t=time.perf_counter();sizes=await asyncio.gather(*(body() for _ in range(concurrency)));elapsed=time.perf_counter()-t;done=True;await ctl
            final=await finish(c,sid);raw=(await c.get(f'/api/sessions/{sid}/export')).json();save(path/f'{sid}.json',raw)
            result={'id':sid,'concurrency':concurrency,'bytes':sum(sizes),'seconds':elapsed,'configured_bps':1750000,'measured_bps':sum(sizes)*8/elapsed,'error_fraction':sum(sizes)*8/elapsed/1750000-1,'health_max_s':max(lat),'health_requests':len(lat)};calibration.append(result);print(result,flush=True)
            assert abs(result['error_fraction'])<.15 and max(lat)<.5
        report['calibration']=calibration
        # A single video response starts before the 12 s drop and continues after it.
        sid=(await c.post('/api/sessions',json={'profile':'step','purpose':'calibration'})).json()['id'];anchor=time.perf_counter();await c.get(f'/media/{sid}/init-0.mp4');await asyncio.sleep(max(0,11.5-(time.perf_counter()-anchor)))
        arrivals=[];t=time.perf_counter()
        async with c.stream('GET',f'/media/{sid}/chunk-3-00001.m4s') as r:
            r.raise_for_status()
            async for chunk in r.aiter_bytes():arrivals.append([time.perf_counter()-anchor,len(chunk)])
        elapsed=time.perf_counter()-t;await finish(c,sid);save(path/f'{sid}.json',(await c.get(f'/api/sessions/{sid}/export')).json())
        low=sum(n for t,n in arrivals if 13<=t<18)*8/5
        report['inflight_transition']={'id':sid,'request_start_profile_s':arrivals[0][0],'duration_s':elapsed,'low_window_s':[13,18],'low_measured_bps':low,'arrivals':arrivals}
        assert arrivals[0][0]<12 and arrivals[-1][0]>18 and 350000<low<600000
        # Audio-sized, video and repeated range bodies share one budget.
        sid=(await c.post('/api/sessions',json={'profile':'stable','scale':.5,'purpose':'calibration'})).json()['id']
        async def request(asset,headers=None):
            t=time.perf_counter();r=await c.get(f'/media/{sid}/{asset}',headers=headers);r.raise_for_status();return {'asset':asset,'status':r.status_code,'bytes':len(r.content),'seconds':time.perf_counter()-t,'range':r.headers.get('content-range')}
        t=time.perf_counter();mixed=await asyncio.gather(request('chunk-3-00001.m4s'),request('chunk-4-00001.m4s'),request('chunk-3-00001.m4s',{'Range':'bytes=0-65535'}),request('chunk-3-00001.m4s',{'Range':'bytes=0-65535'}));elapsed=time.perf_counter()-t
        await finish(c,sid);raw=(await c.get(f'/api/sessions/{sid}/export')).json();save(path/f'{sid}.json',raw)
        assert sum(d['bytes'] for d in raw['delivery'])==sum(x['bytes'] for x in mixed)
        assert all(x['status']==206 and x['bytes']==65536 for x in mixed[2:])
        report['mixed']={'id':sid,'seconds':elapsed,'bps':sum(x['bytes'] for x in mixed)*8/elapsed,'requests':mixed};assert abs(report['mixed']['bps']/1750000-1)<.15
        sid=(await c.post('/api/sessions',json={'profile':'stable','scale':.2,'purpose':'calibration'})).json()['id']
        received=0
        async with c.stream('GET',f'/media/{sid}/chunk-3-00001.m4s') as r:
            async for chunk in r.aiter_bytes():
                received+=len(chunk)
                if received>=32768:break
        await asyncio.sleep(.1);t=time.perf_counter();small=await c.get(f'/media/{sid}/init-0.mp4');small.raise_for_status();recovery=time.perf_counter()-t
        final=await finish(c,sid);raw=(await c.get(f'/api/sessions/{sid}/export')).json();save(path/f'{sid}.json',raw)
        assert any(d['status']=='aborted' for d in raw['delivery']) and recovery<.5
        report['cancellation']={'id':sid,'received_before_abort':received,'subsequent_init_s':recovery,'summary':final['summary']}
    save(path/'report.json',report)

async def browser_run(browser,base,out,config,seconds=40,full=False):
    ctx=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce');external=[];errors=[];bad=[]
    async def route(r):
        if r.request.url.startswith(base+'/'):await r.continue_()
        else:external.append(r.request.url);await r.abort()
    await ctx.route('**/*',route);page=await ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:bad.append([r.url,r.status]) if r.status>=400 else None)
    try:
        await page.goto(base);await page.wait_for_function('window.stallguard')
        if full:await page.evaluate('''()=>{const v=document.querySelector('video');v.addEventListener('ended',()=>{window.endProof={time:v.currentTime,duration:v.duration,frames:v.getVideoPlaybackQuality().totalVideoFrames};},{once:true});}''')
        sid=await page.evaluate('(c)=>window.stallguard.start(c)',config)
        if full:
            await page.wait_for_function('window.endProof && window.stallguard.snapshot.state==="finished"',timeout=180000)
            proof=await page.evaluate('window.endProof');assert proof['time']>=119 and proof['frames']>=2500
        else:
            await page.wait_for_timeout(seconds*1000);proof=await page.evaluate('({time:document.querySelector("video").currentTime,frames:document.querySelector("video").getVideoPlaybackQuality().totalVideoFrames})');await page.evaluate('window.stallguard.stop("finished")')
        raw=await (await ctx.request.get(base+f'/api/sessions/{sid}/export')).json();save(out/f'{sid}.json',raw)
        assert proof['time']>1 and proof['frames']>0 and not errors and not external and not bad
        assert raw['meta']['status']=='finished'
        configs=[e for e in raw['events'] if e['kind']=='configuration'];assert len(configs)==1
        settings=configs[0]['settings'];assert settings['buffer']['fastSwitchEnabled'] is False
        if config['policy']=='default':assert settings['abr']['rules']['throughputRule']['active'] and settings['abr']['rules']['bolaRule']['active'] and not any(e['kind']=='decision' for e in raw['events'])
        else:
            assert not any(r['active'] for r in settings['abr']['rules'].values())
            decisions=[e for e in raw['events'] if e['kind']=='decision'];assert len({e['decision_id'] for e in decisions})==len(decisions)
            if config['policy']=='ml':assert any(e.get('predictor')=='random forest' for e in decisions)
        row={'id':sid,**config,'proof':proof,'ending_rule':'natural ended with 180 s safety timeout' if full else f'{seconds} s wall clock after start returns','summary':raw['meta']['summary'],'identities':{k:raw['meta'].get(k) for k in ['asset_fingerprint','source_identity','controller_version','model_checksum','common_settings_identity']},'external_attempts':external,'page_errors':errors,'bad_responses':bad}
        print(json.dumps({'id':sid,'policy':config['policy'],'profile':config['profile'],'time':proof['time'],'stalls':row['summary']['stall_count'],'switches':row['summary']['quality_switches'],'requests':row['summary']['video_request_count']}),flush=True);return row
    finally:await ctx.close()

async def playback(base,out,mode,repetitions,seconds):
    path=out/mode;path.mkdir(exist_ok=False);results=[]
    if mode=='candidate':matrix=[('historical','stable',500)]
    elif mode=='full':matrix=[('ml','stable',900)]
    else:matrix=[(policy,profile,500+r) for r in range(repetitions) for profile in ['stable','step','fluctuate'] for policy in ['historical','ml','default']]
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        try:
            for policy,profile,seed in matrix:
                config={'policy':policy,'profile':profile,'seed':seed,'purpose':'test' if mode=='matrix' else 'smoke','benchmark':True,'duration_limit_s':seconds if mode!='full' else None}
                results.append(await browser_run(browser,base,path,config,seconds,mode=='full'));save(path/'runs.json',results)
        finally:await browser.close()
    if mode=='matrix':
        identities=[r['identities'] for r in results];assert all(i==identities[0] for i in identities)
        keys=['id','policy','profile','seed']+[k for k,v in results[0]['summary'].items() if not isinstance(v,(list,dict))]
        with (path/'runs.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
            for r in results:w.writerow({**{k:r[k] for k in keys if k in r},**{k:r['summary'][k] for k in keys if k in r['summary']}})

async def main(a):
    out=Path(a.out).resolve();out.mkdir(exist_ok=True,parents=True)
    if a.mode=='transport':await transport(a.base_url,out)
    else:await playback(a.base_url,out,a.mode,a.repetitions,a.seconds)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['transport','candidate','matrix','full']);p.add_argument('--out',required=True);p.add_argument('--base-url',default='http://127.0.0.1:8002');p.add_argument('--repetitions',type=int,default=3);p.add_argument('--seconds',type=int,default=40);asyncio.run(main(p.parse_args()))
