"""Regression: chart zoom must not remove 2026 from other point views."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')

async def main():
    results=[];errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(viewport={'width':1920,'height':1080})
        page.on('pageerror',lambda e:errors.append(str(e)))
        for lat,lon in [(33.50,135.82),(26.73,33.94),(25.87,55.99)]:
            for product in ['mur','oisst']:
                await page.goto(f'{BASE}?lang=en&lat={lat}&lon={lon}&product={product}&v=20261023-october-r2')
                await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
                await page.locator('#openPointAnalysis').click()
                await page.get_by_role('button',name='Heatwave history',exact=True).click()
                await page.wait_for_function("document.querySelector('#historyPlot').data?.some(t=>t.customdata?.at(-1)==='2026-10-20')",timeout=30000)
                # This exact zoom previously changed To=2025 and deleted 2026 everywhere.
                for plot in ['historyPlot','modelPlot']:
                    await page.evaluate('id=>Plotly.relayout(id,{"xaxis.range[0]":2003.05,"xaxis.range[1]":2025.9})',plot)
                    await page.wait_for_timeout(150)
                    assert await page.locator('#toYear').input_value()=='2026'
                    assert await page.evaluate("document.querySelector('#historyPlot').data.some(t=>t.customdata?.at(-1)==='2026-10-20')")
                await page.get_by_role('button',name='Daily and monthly',exact=True).click()
                await page.wait_for_function("document.querySelector('#detailPlot').data?.every(t=>t.x.at(-1)==='2026-10-20')",timeout=30000)
                # Choosing an older end date remains possible; Show latest restores it.
                await page.locator('#toYear').evaluate('e=>{e.value="2025";e.dispatchEvent(new Event("change"));}')
                await page.wait_for_function("document.querySelector('#detailPlot').data?.[0].x.at(-1)==='2025-12-31'",timeout=30000)
                assert 'shown through 2025-12-31' in await page.locator('#detailNote').inner_text()
                await page.get_by_role('button',name='Heatwave history',exact=True).click()
                await page.locator('#showLatestRecords').click()
                await page.wait_for_function("document.querySelector('#historyPlot').data?.some(t=>t.customdata?.at(-1)==='2026-10-20')",timeout=30000)
                data=await page.evaluate('''async product=>{const s=AtlasUI.snapshot(),d=await AtlasDetails.load(s.state.pixel,product);let gaps=0;for(let i=1;i<d.daily.dates.length;i++)if(Date.parse(d.daily.dates[i])-Date.parse(d.daily.dates[i-1])!==86400000)gaps++;return {point:s.point.slice(0,2),product,to:s.state.to,gaps,missing:d.daily.values.filter(v=>v===null).length,end:d.daily.dates.at(-1)};}''',product)
                assert data['gaps']==0 and data['missing']==0 and data['to']==2026,data
                results.append(data)
                if lat==33.50 and product=='mur':
                    await page.locator('#themeToggle').evaluate('e=>e.click()')
                    await page.get_by_role('button',name='Daily and monthly',exact=True).click()
                    await page.wait_for_timeout(300)
                    await page.screenshot(path=str(ROOT/'qa/continuous-october-kuroshio.png'))
        assert not errors,errors
        (ROOT/'qa/range-regression.json').write_text(json.dumps({'base':BASE,'passed':True,'zoomPreservesYearFilter':True,'allVisibleDetailLinesEnd':'2026-10-20','points':results,'browserErrors':errors},indent=2))
        await browser.close()
    print('PASS: zoom keeps 2026; Show latest restores it; daily/monthly lines reach 20 October with no gaps at six product/point combinations.')

if __name__=='__main__':asyncio.run(main())
