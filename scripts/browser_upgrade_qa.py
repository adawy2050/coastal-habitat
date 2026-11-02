"""Release checks for EN/AR, both themes and three widths under project URL."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1];QA=ROOT/'qa';QA.mkdir(exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    for lang in ['en','ar']:
        for theme in ['light','dark']:
            for width in [360,768,1440]:
                context=browser.new_context(viewport={'width':width,'height':950},reduced_motion='reduce')
                page=context.new_page();errors=[];http=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('response',lambda r:http.append([r.status,r.url]) if r.status>=400 else None)
                page.add_init_script(f"localStorage.setItem('atlas-theme','{theme}')")
                page.goto(f'http://127.0.0.1:8765/coastal-habitat/?lang={lang}&basin=gulf&lat=25.3&lon=55.3',wait_until='networkidle')
                page.wait_for_function("document.documentElement.dataset.ready==='true' && document.querySelector('#detailPlot').data?.length===3")
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                assert page.evaluate('document.documentElement.dataset.motion')=='off'
                assert page.evaluate('document.documentElement.dataset.theme')==theme
                assert page.evaluate('document.documentElement.dir')==('rtl' if lang=='ar' else 'ltr')
                assert page.locator('.paper-row').count()==10
                assert page.locator('.news-item').count()==3
                assert page.evaluate("document.querySelector('#modelPlot').data.some(t=>t.meta==='annual_scenario'&&t.x.includes(2027))")
                assert page.evaluate("document.querySelector('#outlookTimeline').data.at(-1).x[1].startsWith('2027')")
                page.locator('#filtersOpen').click();assert page.locator('#product').is_visible();page.locator('#basemap').select_option('coastline');page.locator('#filtersClose').click()
                page.keyboard.press('Tab');page.locator('#themeToggle').focus();assert page.locator('#themeToggle').evaluate("e=>e.matches(':focus-visible')")
                page.screenshot(path=str(QA/f'release_{lang}_{theme}_{width}.png'))
                if width==1440:page.locator('#connections').screenshot(path=str(QA/f'release_connections_{lang}_{theme}.png'))
                assert not errors,errors
                assert not http,http
                results.append({'language':lang,'theme':theme,'width':width,'passed':True});print('PASS',lang,theme,width,flush=True)
                context.close()
    # Like-for-like full-domain rendering time: same viewport, bounds and filters.
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto('http://127.0.0.1:8765/coastal-habitat/?lang=en&basin=all',wait_until='networkidle')
    page.wait_for_function("document.documentElement.dataset.ready==='true'")
    measure=page.evaluate('''async()=>{const times=[];AtlasUI.redraw();for(let i=0;i<30;i++){await new Promise(requestAnimationFrame);const t=performance.now();AtlasDebug.state.year=2003+i%23;AtlasUI.redraw();times.push(performance.now()-t);}return {mean:times.reduce((a,b)=>a+b)/times.length,p95:[...times].sort((a,b)=>a-b)[28],samples:times};}''')
    (QA/'canvas_full_view.json').write_text(json.dumps(measure,indent=2))
    browser.close()
(QA/'upgrade_browser_results.json').write_text(json.dumps({'passed':True,'layouts':results,'fullViewDrawMs':measure},indent=2))
print('PASS: all 12 language/theme/width combinations, project paths, reduced motion, rich curves and keyboard focus.')
