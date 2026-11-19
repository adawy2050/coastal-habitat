"""Check current-year maps/curves and photo loading in each study area."""
import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('ATLAS_QA_URL','http://127.0.0.1:8765/')

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        page=await browser.new_page(viewport={'width':1440,'height':1050},accept_downloads=True)
        errors=[];missing=[];checks=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('response',lambda r:missing.append(r.url) if r.status>=400 and r.url.startswith(BASE) else None)
        for basin,lat,lon in [('redsea',26.73,33.94),('gulf',25.87,55.99),('eastasia',38.25,141.60)]:
            await page.goto(f'{BASE}?lang=en&basin={basin}&lat={lat}&lon={lon}&product=mur&v=20261023-october-r2')
            await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
            assert await page.locator('#year').input_value()=='2026'
            for product in ['mur','oisst']:
                await page.locator('#product').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("change"));}',product)
                await page.wait_for_function('(p)=>AtlasUI.snapshot().state.product===p&&document.querySelector("#loading").hidden',arg=product,timeout=60000)
                data=await page.evaluate('p=>AtlasObserved2026.forPoint(AtlasUI.snapshot().state.pixel,p)',product)
                assert data['product']==product and data['index']['dateEnd']=='2026-10-20'
                for metric,expected in zip(data['index']['metricOrder'],data['metrics']):
                    await page.locator('#metric').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("change"));}',metric)
                    await page.wait_for_function("""({metric,value})=>{const s=AtlasUI.snapshot(),plot=document.querySelector('#historyPlot'),line=plot.data?.find(t=>t.meta==='observed_to_date');return s.state.metric===metric&&document.querySelector('#loading').hidden&&line?.customdata?.at(-1)==='2026-10-20'&&(value===null?line.y.at(-1)===null:Math.abs(line.y.at(-1)-value)<1e-5);}""",arg={'metric':metric,'value':expected},timeout=60000)
                    mapped=await page.evaluate('async ({product,metric})=>{const a=await AtlasUI.mapValues(product,metric);return a[AtlasUI.snapshot().point[product==="mur"?4:5]];}',{'product':product,'metric':metric})
                    assert mapped==expected,(basin,product,metric,mapped,expected)
                    checks.append([basin,product,metric])
                await page.locator('#metric').evaluate('e=>{e.value="mhw_days";e.dispatchEvent(new Event("change"));}')
                await page.wait_for_function("document.querySelector('#modelPlot').data?.some(t=>t.meta==='observed_to_date'&&t.customdata.at(-1)==='2026-10-20')",timeout=60000)
            await page.evaluate('()=>{const s=AtlasUI.snapshot(),ll=L.latLng(s.point[1],s.point[0]);AtlasUI.map.setView(ll,10);}')
            await page.wait_for_timeout(400)
            await page.evaluate('()=>{const s=AtlasUI.snapshot(),ll=L.latLng(s.point[1],s.point[0]);AtlasUI.map.fire("mousemove",{latlng:ll,containerPoint:AtlasUI.map.latLngToContainerPoint(ll)});}')
            await page.wait_for_function("document.querySelector('.cell-hover')",timeout=15000)
            assert await page.locator('.cell-hover img').count()==0
            await page.evaluate('()=>{AtlasUI.map.fire("mouseout");}')
            await page.locator('#openPointAnalysis').click()
            await page.wait_for_function("document.querySelector('#pointHistoryOutlookPlot').data?.length===4",timeout=30000)
            assert await page.locator('#pointAnalysis').evaluate('e=>e.getBoundingClientRect().width>=innerWidth*.95')
            assert await page.locator('#pointHistoryOutlookPlot').evaluate("e=>e.data[0].x.at(-1)==='2026-10-20'&&e.data[3].x.at(-1)==='2027-02-28'")
            await page.wait_for_function("[...document.querySelectorAll('#pixelPhoto img')].some(i=>i.complete&&i.naturalWidth>0)",timeout=30000)
            await page.get_by_role('button',name='Daily and monthly',exact=True).click()
            await page.wait_for_function("document.querySelector('#detailPlot').data?.some(t=>t.x.at(-1)==='2026-10-20')",timeout=30000)
            await page.get_by_role('button',name='Heatwave history',exact=True).click()
            await page.wait_for_function("document.querySelector('#monthCalendar svg')?.textContent.includes('2026')",timeout=30000)
            if basin=='redsea':
                await page.locator('#historyPlot').scroll_into_view_if_needed()
                await page.screenshot(path=str(ROOT/'qa/october-history.png'))
                async with page.expect_download() as event:await page.locator('#downloadHistory').click()
                await (await event.value).save_as(ROOT/'qa/october-history.csv')
                await page.get_by_role('button',name='Overview',exact=True).click()
                async with page.expect_download(timeout=90000) as event:await page.locator('#createReport').click()
                await (await event.value).save_as(ROOT/'qa/october-report.pdf')
            await page.keyboard.press('Escape')
        await page.wait_for_function('AtlasPhotos.photos.length===470')
        photo_errors=await page.evaluate('''async()=>{const errors=[],photos=AtlasPhotos.photos;for(let k=0;k<photos.length;k+=12)await Promise.all(photos.slice(k,k+12).map(p=>new Promise(resolve=>{const image=new Image(),timeout=setTimeout(()=>{errors.push(p.id+':timeout');resolve();},20000);image.onload=()=>{clearTimeout(timeout);if(!image.naturalWidth)errors.push(p.id);resolve();};image.onerror=()=>{clearTimeout(timeout);errors.push(p.id);resolve();};image.src=AtlasPhotos.previewUrl(p,480);})));return errors;}''')
        assert not photo_errors,photo_errors
        await page.route('https://upload.wikimedia.org/**',lambda route:route.abort())
        await page.evaluate('AtlasPhotos.open(AtlasPhotos.photos.findIndex(p=>p.originalHosted===false))')
        await page.wait_for_function("document.querySelector('#photoOriginal').naturalWidth>=1400&&document.querySelector('#photoLoadNote').textContent.includes('source link')",timeout=30000)
        await page.screenshot(path=str(ROOT/'qa/photo-original-fallback.png'))
        await page.locator('#photoClose').click()
        assert not errors,errors
        assert not missing,missing
        (ROOT/'qa/october-browser-results.json').write_text(json.dumps({'base':BASE,'passed':True,'mapAndCurveChecks':checks,'decodedPhotoPreviews':470,'hoverPhotosRemoved':True,'pointPhotosRetained':True,'originalFailureFallback':True,'browserErrors':errors,'missingAssets':missing},indent=2))
        await browser.close()
        print('PASS: 36 map/curve checks, October history/report, 470 photo previews, hover without photos, point photos and original fallback.')

if __name__=='__main__':asyncio.run(main())
