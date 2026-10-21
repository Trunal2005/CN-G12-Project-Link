import argparse
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main(seconds,policy,profile):
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        context=await browser.new_context(viewport={'width':1440,'height':1000})
        external=[]; errors=[]; requests=[]
        async def route(r):
            if not r.request.url.startswith('http://127.0.0.1:8000'):
                external.append(r.request.url);await r.abort()
            else: await r.continue_()
        await context.route('**/*',route)
        page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
        await page.goto('http://127.0.0.1:8000');await page.wait_for_function('window.stallguard')
        await page.evaluate('(c)=>window.stallguard.start(c)',{'policy':policy,'profile':profile,'purpose':'smoke','benchmark':True})
        await page.wait_for_function('document.querySelector("video").currentTime>1',timeout=30000)
        await page.wait_for_timeout(seconds*1000)
        state=await page.evaluate('({time:document.querySelector("video").currentTime,decoded:document.querySelector("video").getVideoPlaybackQuality().totalVideoFrames,snapshot:window.stallguard.snapshot,sid:window.stallguard.sid})')
        out=ROOT/'data/results/screenshots';out.mkdir(exist_ok=True)
        await page.screenshot(path=str(out/'desktop.png'),full_page=True)
        await page.evaluate('window.stallguard.stop("finished")')
        await page.set_viewport_size({'width':390,'height':844});await page.screenshot(path=str(out/'mobile.png'),full_page=True)
        overflow=await page.evaluate('document.documentElement.scrollWidth>innerWidth')
        result={'policy':policy,'profile':profile,'requested_seconds':seconds,'time':state['time'],'decoded_frames':state['decoded'],'sid':state['sid'],'errors':errors,'external_attempts':external,'mobile_overflow':overflow,'video_reps_requested':sorted(set(u.split('/chunk-')[1].split('-')[0] for u in requests if '/chunk-' in u and '/chunk-4-' not in u)),'snapshot':state['snapshot']}
        (ROOT/'data/results'/f'browser-{policy}-{profile}.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='snapshot'},indent=2))
        await browser.close()
        assert state['time']>1 and state['decoded']>0
        assert not errors and not external and not overflow

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--seconds',type=int,default=20);a.add_argument('--policy',default='historical');a.add_argument('--profile',default='stable');args=a.parse_args();asyncio.run(main(args.seconds,args.policy,args.profile))
