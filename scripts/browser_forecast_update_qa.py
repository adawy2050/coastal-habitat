"""Check issued forecast controls, continuous observations and regional sources."""
from pathlib import Path
import asyncio,json
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto('http://127.0.0.1:8765/?lang=en&lat=38.25&lon=141.60&product=oisst');await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
        assert await page.locator('#photoBasin option[value="eastasia"]').count()==1
        f=await page.evaluate('AtlasUI.forecast("oisst",AtlasUI.snapshot().state.pixel)');assert f['external'] is not None and f['trainingLastYear']==2025 and f['nTest']==10
        dates=await page.evaluate('AtlasDetails.load(AtlasUI.snapshot().state.pixel,"oisst").then(d=>({daily:d.daily.dates.at(-1),monthly:d.monthly.dates.at(-1),year:d.currentYear}))');assert dates=={'daily':'2026-10-20','monthly':'2026-10-15','year':2026},dates
        await page.locator('#openPointAnalysis').click();await page.wait_for_function("document.querySelectorAll('#observed2026Metrics tbody tr').length===6",timeout=30000);await page.get_by_role('button',name='Climate indices',exact=True).click();await page.wait_for_function("document.querySelector('#issuedIndexPlot').data?.length>20",timeout=30000)
        await page.locator('#issuedIndexForecasts').scroll_into_view_if_needed();await page.screenshot(path=str(ROOT/'qa/issued-climate-forecasts.png'))
        await page.get_by_role('button',name='Outlook',exact=True).click();await page.locator('#issuedCellPlot').scroll_into_view_if_needed();await page.wait_for_function("document.querySelector('#issuedCellPlot').data?.length===4")
        await page.screenshot(path=str(ROOT/'qa/issued-cell-outlook.png'))
        await page.locator('#outlookInputs').select_option('observed');await page.wait_for_timeout(400);f=await page.evaluate('AtlasUI.forecast("oisst",AtlasUI.snapshot().state.pixel)');assert f['external'] is None and f['trainingLastYear']==2024
        await page.locator('#outlookInputs').select_option('external');await page.wait_for_timeout(400);f=await page.evaluate('AtlasUI.forecast("oisst",AtlasUI.snapshot().state.pixel)');assert f['external'] is not None
        await page.keyboard.press('Escape')
        regional={}
        for basin in ['redsea','gulf','eastasia']:
            await page.locator('#basin').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("change"));}',basin);await page.wait_for_timeout(300)
            rows=await page.locator('#paperList h3').all_text_contents();news=await page.locator('#newsList h3').all_text_contents();assert rows and news
            if basin=='redsea':assert all('Red Sea' in s for s in rows)
            if basin=='gulf':assert all('Gulf' in s for s in rows)
            if basin=='eastasia':assert not any('Red Sea' in s or 'Persian Gulf' in s for s in rows)
            regional[basin]={'papersVisible':len(rows),'newsVisible':len(news)}
        assert not errors,errors
        (ROOT/'qa/forecast_update_browser.json').write_text(json.dumps({'passed':True,'continuousDailyThrough':dates['daily'],'issuedForecastPointControls':True,'regionalSources':regional,'browserErrors':errors},indent=2))
        await browser.close();print('PASS: issued forecasts, model switching, continuous 2026 series, and regional papers/news in all three areas.')

if __name__=='__main__':asyncio.run(main())
