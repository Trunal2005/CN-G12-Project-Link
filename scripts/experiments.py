"""Sequential fresh Chrome contexts; no concurrent playback runs."""
import argparse
import asyncio
import json
import sys
import datetime
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

COLLECT=[
 ('train','historical','stable',101,.65),('train','default','step',102,.8),
 ('train','historical','fluctuate',103,.7),('train','default','stable',104,1.4),
 ('train','historical','step',105,1.2),('train','default','fluctuate',106,1.2),
 ('validation','historical','step',201,1.05),('validation','default','fluctuate',202,.9),
]

async def run(mode,seconds,repetitions,output_arg=None):
    output=Path(output_arg).resolve() if output_arg else ROOT/'data/results'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output.mkdir(parents=True,exist_ok=False);print('New evidence directory:',output,flush=True)
    matrix=COLLECT if mode=='collect' else [('test',p,f,300+repeat,1) for repeat in range(repetitions) for f in ['stable','step','fluctuate','unfamiliar'] for p in ['historical','ml','default']]
    rows=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        for purpose,policy,profile,seed,scale in matrix:
            context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
            externals=[];errors=[]
            async def route(r):
                if r.request.url.startswith('http://127.0.0.1:8000'): await r.continue_()
                else:externals.append(r.request.url);await r.abort()
            await context.route('**/*',route)
            page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            config=dict(purpose=purpose,policy=policy,profile=profile,seed=seed,scale=scale,benchmark=True,duration_limit_s=seconds)
            try:
                await page.goto('http://127.0.0.1:8000');await page.wait_for_function('window.stallguard')
                sid=await page.evaluate('(c)=>window.stallguard.start(c)',config)
                # Fixed wall-clock ending rule from session-start return, includes startup/stalls.
                await page.wait_for_timeout(seconds*1000)
                observed=await page.evaluate('({time:document.querySelector("video").currentTime,frames:document.querySelector("video").getVideoPlaybackQuality().totalVideoFrames})')
                final=await page.evaluate('window.stallguard.stop("finished")')
                export=await (await context.request.get(f'http://127.0.0.1:8000/api/sessions/{sid}/export')).json()
                (output/f'{sid}.json').write_text(json.dumps(export,indent=2))
                row={**config,'id':sid,'ending_rule':f'{seconds} s wall clock after start','observed':observed,'external_attempts':externals,'page_errors':errors,'summary':final['summary']}
                assert observed['time']>1 and observed['frames']>0,'No decoded playback'
                assert not errors and not externals
                rows.append(row)
                print(json.dumps({'completed':len(rows),'of':len(matrix),**config,'id':sid,'time':observed['time'],'stalls':final['summary']['stall_count']}),flush=True)
            except Exception as e:
                rows.append({**config,'error':str(e)});print(str(e),flush=True)
                raise
            finally:
                (output/f'{mode}-runs.json').write_text(json.dumps(rows,indent=2))
                await context.close()
        await browser.close()
    if mode=='evaluate':
        import csv
        keys=['id','policy','profile','seed','scale']+list(rows[0]['summary'])
        with (output/'evaluation.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
            for r in rows:writer.writerow({**{k:r[k] for k in keys if k in r},**r['summary']})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['collect','evaluate']);p.add_argument('--seconds',type=int,default=40);p.add_argument('--repetitions',type=int,default=1);p.add_argument('--out');a=p.parse_args();asyncio.run(run(a.mode,a.seconds,a.repetitions,a.out))
