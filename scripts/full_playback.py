"""Natural end-to-end 120 s decode proof; kept separate from bounded evaluation."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
    errors=[];external=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        context=await browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        async def route(r):
            if r.request.url.startswith('http://127.0.0.1:8000'):await r.continue_()
            else:external.append(r.request.url);await r.abort()
        await context.route('**/*',route)
        page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto('http://127.0.0.1:8000');await page.wait_for_function('window.stallguard')
        await page.evaluate('''()=>{const v=document.querySelector('video');v.addEventListener('ended',()=>{window.endProof={time:v.currentTime,duration:v.duration,decoded_frames:v.getVideoPlaybackQuality().totalVideoFrames};},{once:true});}''')
        sid=await page.evaluate('window.stallguard.start({policy:"ml",profile:"stable",seed:999,purpose:"smoke",benchmark:true})')
        # Poll in bounded intervals so a failure has an explicit timeout.
        for i in range(18):
            await page.wait_for_timeout(10000)
            state=await page.evaluate('({proof:window.endProof,state:window.stallguard.snapshot.state,time:document.querySelector("video").currentTime})')
            print(json.dumps(state),flush=True)
            if state.get('proof'):break
        await page.wait_for_function('window.stallguard.snapshot.state==="finished"',timeout=10000)
        proof=await page.evaluate('window.endProof');assert proof and proof['time']>=119 and proof['decoded_frames']>2500
        data=await (await context.request.get(f'http://127.0.0.1:8000/api/sessions/{sid}/export')).json()
        assert data['meta']['status']=='finished' and data['meta']['summary']['browser_errors']==0
        assert not errors and not external
        result={'sid':sid,'policy':'ml','profile':'stable','purpose':'full-clip smoke, separate from final matrix','proof':proof,'page_errors':errors,'external_attempts':external,'summary':data['meta']['summary']}
        (ROOT/'data/results/full-playback.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
        await browser.close()
if __name__=='__main__':asyncio.run(main())
