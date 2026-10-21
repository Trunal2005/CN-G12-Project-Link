"""Fresh-checkout Chrome playback, UI stop/save and downloaded export check."""
import argparse
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright


async def main(base, out):
    out.mkdir(parents=True, exist_ok=False)
    errors, external, bad = [], [], []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel='chrome', headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        async def route(r):
            if r.request.url.startswith(base + '/'):
                await r.continue_()
            else:
                external.append(r.request.url)
                await r.abort()
        await context.route('**/*', route)
        page = await context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('response', lambda r: bad.append(r.status) if r.status >= 400 else None)
        try:
            await page.goto(base)
            await page.wait_for_function('window.stallguard')
            health = await (await context.request.get(base + '/api/health')).json()
            assert health['media_ready'] and health['model_ready']
            await page.get_by_label('Adaptation policy').select_option('ml')
            await page.get_by_role('button', name='Start new session').click()
            await page.wait_for_function('document.querySelector("video").currentTime > 3', timeout=30000)
            await page.wait_for_function('window.stallguard.events.some(e=>e.kind==="decision" && e.predictor==="random forest")', timeout=40000)
            proof = await page.evaluate('({time:document.querySelector("video").currentTime,frames:document.querySelector("video").getVideoPlaybackQuality().totalVideoFrames,sid:window.stallguard.sid})')
            await page.get_by_role('button', name='Stop & save').click()
            await page.wait_for_function('window.stallguard.snapshot.state === "cancelled"')
            async with page.expect_download() as pending:
                await page.get_by_role('button', name='Export JSON', exact=False).click()
            download = await pending.value
            await download.save_as(out / 'session.json')
            export = json.loads((out / 'session.json').read_text())
            assert export['meta']['id'] == proof['sid'] and export['meta']['status'] == 'cancelled'
            assert export['events'] and export['delivery']
            assert any(e.get('predictor') == 'random forest' for e in export['events'])
            assert proof['frames'] > 0
            await page.screenshot(path=str(out / 'desktop.png'), full_page=True)
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.screenshot(path=str(out / 'mobile.png'), full_page=True)
            overflow = await page.evaluate('document.documentElement.scrollWidth > innerWidth')
            assert not overflow and not errors and not external and not bad
            report = {'health': health, 'playback': proof, 'saved_status': export['meta']['status'],
                      'forest_decisions': sum(e.get('predictor') == 'random forest' for e in export['events']),
                      'export_parsed': True, 'page_errors': errors, 'external_attempts': external,
                      'bad_http_statuses': bad, 'mobile_overflow': overflow}
            (out / 'report.json').write_text(json.dumps(report, indent=2))
            print(json.dumps(report, indent=2))
        finally:
            await browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.base_url.rstrip('/'), args.out))
