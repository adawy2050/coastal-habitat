"""Point-wise display verification for the forecast-combination comparison."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')

async def main():
    results=[];errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1600,'height':1100},reduced_motion='reduce')
        page.on('pageerror',lambda e:errors.append(str(e)))
        for product in ['oisst','mur']:
            for lat,lon in [(26.73,33.94),(24.45,54.35),(9.89,118.04)]:
                await page.goto(f'{BASE}?lang=en&lat={lat}&lon={lon}&product={product}&v=20261101-combinations-r1')
                await page.wait_for_function("document.querySelectorAll('#combinationRows tr').length===12",timeout=90000)
                await page.wait_for_function("document.querySelectorAll('#allForecastIndex option').length===9",timeout=30000)
                d=await page.evaluate('AtlasUI.snapshot().state');f=await page.evaluate('AtlasOutlookCombinations.loadPoint(AtlasUI.snapshot().state.product,AtlasUI.snapshot().state.pixel)')
                assert f['summary']['product']==product and len(f['summary']['candidates'])==12
                assert f['summary']['nTest']==(10 if product=='oisst' else 3)
                assert len(await page.locator('#combinationRows').inner_text())>100
                assert await page.evaluate("document.querySelector('#combinationPlot').data.length===5")
                results.append({'product':product,'latitude':lat,'longitude':lon,'probability':f['values']['policy_probability'],'skill':f['values']['policy_skill']})
                if product=='oisst' and lon==118.04:
                    await page.locator('#openPointAnalysis').click()
                    await page.locator('#outlookCombinations').evaluate('(e)=>e.scrollIntoView({block:"start"})')
                    await page.screenshot(path=str(ROOT/'qa/outlook-combinations.png'))
                    for key in ['Nino34','DMI','EMI','ATL3','SIOD','SASD','NNI','CNI','DNI']:
                        await page.locator('#allForecastIndex').select_option(key)
                        await page.wait_for_function("document.querySelector('#allForecastPlot').layout.yaxis.title.text.startsWith(document.querySelector('#allForecastIndex').selectedOptions[0].textContent)")
                    await page.locator('#allForecastIndices').scroll_into_view_if_needed()
                    await page.screenshot(path=str(ROOT/'qa/nine-forecast-indices.png'))
                    await page.locator('#outlookCombinations').evaluate('(e)=>e.scrollIntoView({block:"start"})')
                    async with page.expect_download() as download:
                        await page.locator('#combinationCsv').click()
                    await (await download.value).save_as(str(ROOT/'qa/point-outlook-combinations.csv'))
        assert len({r['probability'] for r in results})>=4
        await page.goto(f'{BASE}?lang=ar&lat=9.89&lon=118.04&product=oisst&v=20261101-combinations-r1')
        await page.set_viewport_size({'width':390,'height':844})
        await page.wait_for_function("document.querySelectorAll('#combinationRows tr').length===12",timeout=90000)
        await page.locator('#openPointAnalysis').click();await page.locator('#outlookCombinations').evaluate('(e)=>e.scrollIntoView({block:"start"})')
        assert 'مقارنة' in await page.locator('#combinationTitle').inner_text()
        await page.screenshot(path=str(ROOT/'qa/outlook-combinations-ar.png'))
        assert not errors,errors
        (ROOT/'qa/outlook_combinations_browser.json').write_text(json.dumps({'passed':True,'points':results,'nineIndices':True,'browserErrors':errors},indent=2))
        await browser.close();print('PASS: 6 native-product/coast comparisons, 9 issued index curves, point CSV, Arabic mobile, no browser errors.')

if __name__=='__main__':asyncio.run(main())
