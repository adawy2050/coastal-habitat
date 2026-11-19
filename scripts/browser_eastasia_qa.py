"""Exercise geographic entry, languages, dense histories and an East Asia PDF."""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parents[1]
async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto('http://127.0.0.1:8765/?lang=en&choose=1');await page.wait_for_function("document.documentElement.dataset.ready==='true'",timeout=90000)
        assert await page.locator('#areaEntry').is_visible()
        await page.locator('#areaChoices button').filter(has_text='East Asia & western Pacific').click();assert await page.locator('#basin').input_value()=='eastasia'
        assert await page.evaluate("AtlasUI.snapshot().meta.pixels===210680")
        await page.locator('#chooseArea').click();await page.locator('#rectangleForm summary').click()
        for name,value in [('south','24'),('west','126'),('north','31'),('east','133')]:await page.locator(f'#rectangleForm input[name={name}]').fill(value)
        await page.locator('#rectangleForm button').click();await page.wait_for_timeout(1000)
        assert await page.evaluate("JSON.stringify(AtlasUI.snapshot().state.selection)==='[126,24,133,31]'")
        assert await page.evaluate("AtlasUI.snapshot().pixels.filter(AtlasUI.visible).length>100")
        assert await page.evaluate("AtlasUI.visible(AtlasUI.snapshot().point)")
        locales=['en','ar','zh-Hans','zh-Hant','ja','ko','fil','id','ms','vi','ru','fa'];checks=[]
        for width in [1440,390]:
            await page.set_viewport_size({'width':width,'height':1000})
            for code in locales:
                await page.locator('#languageSelect').select_option(code);await page.wait_for_timeout(200)
                assert await page.locator('html').get_attribute('lang')==code
                dimensions=await page.evaluate("({map:document.querySelector('#map').getBoundingClientRect().width,body:document.documentElement.scrollWidth,viewport:innerWidth})")
                assert abs(dimensions['map']-width)<=1,dimensions
                assert dimensions['body']<=width+1,(code,dimensions)
                checks.append({'language':code,'width':width,'fullWidthMap':True,'noOverflow':True})
        await page.set_viewport_size({'width':1440,'height':1000});await page.locator('#languageSelect').select_option('en');await page.evaluate("AtlasUI.selectBounds(null)")
        await page.locator('#basin').select_option('eastasia');await page.wait_for_timeout(1000)
        await page.evaluate("AtlasUI.selectPixel(AtlasUI.snapshot().pixels.findIndex(p=>p[3]>=5&&(p[2]&8)),true)");await page.wait_for_function("document.querySelector('#footprintNote').textContent.includes('occurrence')")
        await page.locator('#historyDetails').scroll_into_view_if_needed();await page.wait_for_function("document.querySelector('#monthCalendar svg rect')!==null");assert await page.locator('#pixelPhoto img').first.evaluate('(e)=>e.complete&&e.naturalWidth>0')
        assert await page.locator('.habitat-outlook-figure').count()==4
        assert await page.locator('.region-line-toggle').count()>40
        assert await page.evaluate("document.querySelector('#historyPlot').data.some(t=>t.yaxis==='y2')")
        async with page.expect_download() as event:await page.locator('#saveCalendarSvg').click()
        calendar=await event.value;await calendar.save_as(ROOT/'qa/monthly_heatwave_calendar.svg')
        assert '<svg' in (ROOT/'qa/monthly_heatwave_calendar.svg').read_text(encoding='utf8')
        await page.locator('#metric').select_option('outlook_probability');await page.wait_for_timeout(600)
        assert await page.evaluate("AtlasUI.snapshot().state.mapMode==='probability'")
        await page.locator('#languageSelect').select_option('ar');await page.locator('#themeToggle').click();await page.wait_for_timeout(500)
        async with page.expect_download(timeout=90000) as event:await page.locator('#createReport').click()
        download=await event.value;await download.save_as(ROOT/'qa/eastasia-point-report.pdf')
        await page.screenshot(path=str(ROOT/'qa/eastasia-arabic-map.png'),full_page=False)
        assert not errors,errors
        (ROOT/'qa/eastasia_browser_results.json').write_text(json.dumps({'passed':True,'checks':checks,'browserErrors':errors,'report':'eastasia-point-report.pdf'},indent=2))
        await browser.close();print('PASS: 24 language/viewport combinations, rectangle filter, East Asia kelp point, histories, photos, forecast curves and Arabic/dark PDF download.')
if __name__=='__main__':asyncio.run(main())
