"""Exercise the layered map, point window, current-year data and PDF export."""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto('http://127.0.0.1:8765/?lang=en&lat=38.25&lon=141.60');await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
        assert await page.locator('#basemap').input_value()=='blend'
        assert not await page.locator('input[name=habitat][value="2"]').is_checked()
        assert await page.evaluate('AtlasUI.snapshot().state.habitats===13')
        await page.evaluate('AtlasUI.map.setView([AtlasUI.snapshot().point[1],AtlasUI.snapshot().point[0]],10)');await page.wait_for_timeout(3500)
        await page.locator('#shorelineOpacity').evaluate("e=>{e.value=.65;e.dispatchEvent(new Event('input'));}")
        await page.locator('#satelliteOpacity').evaluate("e=>{e.value=.8;e.dispatchEvent(new Event('input'));}")
        assert await page.evaluate('AtlasMapLayers.state.shoreline===.65&&AtlasMapLayers.state.satellite===.8')
        await page.screenshot(path=str(ROOT/'qa/shoreline-blended.png'))
        point=await page.evaluate("(()=>{const p=AtlasUI.map.latLngToContainerPoint([AtlasUI.snapshot().point[1],AtlasUI.snapshot().point[0]]);return {x:p.x,y:p.y};})()")
        await page.locator('#map').click(position=point);await page.wait_for_function("document.querySelector('#pointAnalysis').open")
        assert await page.locator('#pointAnalysis #createReport').count()==1
        await page.get_by_role('button',name='2026 to date',exact=True).click();await page.wait_for_function("document.querySelector('#observed2026Plot').data?.length===3",timeout=30000)
        observed=await page.locator('#observed2026Note').inner_text();assert any(source in observed for source in ['OISST','MUR']) and '2026' in observed,observed
        assert await page.locator('#observed2026Plot').evaluate("e=>e.data[0].x.at(-1)==='2026-10-20'")
        await page.screenshot(path=str(ROOT/'qa/observed2026-point.png'))
        await page.get_by_role('button',name='Heatwave history',exact=True).click();await page.wait_for_function("document.querySelector('#monthCalendar svg')")
        assert await page.locator('#historyPlot').evaluate("e=>e.data.some(t=>t.yaxis==='y2')")
        await page.locator('#pointWindowProduct').select_option('oisst');await page.wait_for_timeout(800);assert await page.locator('#product').input_value()=='oisst'
        await page.get_by_role('button',name='Outlook',exact=True).click();await page.wait_for_timeout(500);assert await page.locator('#outlookScope').input_value()=='pixel'
        await page.get_by_role('button',name='Overview',exact=True).click()
        async with page.expect_download(timeout=90000) as event:await page.locator('#createReport').click()
        download=await event.value;await download.save_as(ROOT/'qa/point-window-2026-report.pdf')
        await page.keyboard.press('Escape');assert not await page.locator('#pointAnalysis').evaluate('e=>e.open')
        await page.locator('#filtersOpen').click();await page.locator('#basemap').select_option('satellite');await page.locator('#filtersClose').click();assert await page.locator('#shorelineOpacity').is_disabled()
        await page.set_viewport_size({'width':390,'height':900});await page.locator('#languageSelect').select_option('ar');await page.locator('#openPointAnalysis').click();await page.wait_for_timeout(500)
        assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        assert await page.locator('#pointAnalysis').evaluate('e=>e.getBoundingClientRect().width<=innerWidth+1')
        await page.screenshot(path=str(ROOT/'qa/point-window-mobile-ar.png'));assert not errors,errors
        result={'passed':True,'mapClickOpensWindow':True,'independentOpacity':True,'currentYearObservations':observed,'historyAndOutlook':True,'reportInsideWindow':True,'arabicMobile':True,'browserErrors':errors}
        (ROOT/'qa/point_window_results.json').write_text(json.dumps(result,indent=2),encoding='utf8');await browser.close();print('PASS: layered map, independent opacity, point window, 2026 observations, history/outlook, PDF and Arabic/mobile.')

if __name__=='__main__':asyncio.run(main())
