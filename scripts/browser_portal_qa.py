"""Check bilingual controls, independent 2026 climate dates and the seasonal link."""
from pathlib import Path
import csv
import io
import json
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
qa=root/'qa';qa.mkdir(exist_ok=True)
feed=json.loads((root/'dist/data/climate_latest.json').read_text())
current_year=feed['asOf'][:4]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[];http=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:http.append([r.status,r.url]) if r.status>=400 else None)
    page.goto('http://127.0.0.1:8765/?lat=26.73&lon=33.94&variable=outlook_probability',wait_until='networkidle')
    page.wait_for_function("document.documentElement.dataset.ready==='true' && document.querySelector('#pointProbability').textContent!=='—'",timeout=60000)
    probability=page.locator('#pointProbability').inner_text()
    assert page.locator('#climateTo').input_value()==current_year
    assert page.locator('.latest-index-card').count()==7
    assert 'Invalid Date' not in page.locator('#latestIndexCards').inner_text()
    assert page.locator('#climateStep').is_enabled()
    page.locator('#climateThisYear').click()
    assert page.locator('#climateFrom').input_value()==current_year
    assert page.locator('#climateTo').input_value()==current_year
    page.locator('#climateScale').select_option('raw')
    page.wait_for_function("document.querySelector('#climatePlot').data[0].x.every(d=>String(d).startsWith('2026'))")
    expected=[v for i,v in enumerate(feed['monthly']['values']['Nino34']) if feed['monthly']['dates'][i].startswith(current_year) and v is not None]
    plotted=page.evaluate("document.querySelector('#climatePlot').data[0].y.filter(v=>v!==null)")
    assert len(plotted)==len(expected) and max(abs(a-b) for a,b in zip(plotted,expected))<1e-9
    page.locator('#climateStep').select_option('annual')
    page.wait_for_function("document.querySelector('#climateCaption').textContent.includes('year to date')")
    with page.expect_download() as item:page.locator('#downloadClimate').click()
    item.value.save_as(str(qa/'climate_2026_annual.csv'))
    rows=list(csv.DictReader(io.StringIO((qa/'climate_2026_annual.csv').read_text(encoding='utf-8-sig'))))
    assert len(rows)==1 and int(rows[0]['Nino34_months'])==len(expected)
    assert abs(float(rows[0]['Nino34'])-sum(expected)/len(expected))<1e-8
    assert 'Dec 2026' in page.locator('#climateNextTitle').inner_text()
    assert probability in page.locator('#climateNextTitle').inner_text()
    page.locator('[data-language=ar]').click()
    page.wait_for_function("document.documentElement.lang==='ar' && document.querySelector('h1').textContent.includes('الموجات')")
    assert 'سبتمبر' in page.locator('#freshness').inner_text()
    assert page.evaluate('document.documentElement.dir')=='rtl'
    assert page.locator('#pointProbability').inner_text()==probability
    assert 'ديسمبر' in page.locator('#climateNextTitle').inner_text()
    page.locator('#product').select_option('oisst',force=True)
    page.wait_for_function("document.querySelector('#pointValidationYears').textContent.includes('13') && document.querySelector('#pointValidationYears').textContent.includes('تحقق')")
    page.locator('#metric').select_option('mhw_mean_intensity')
    page.wait_for_function("document.querySelector('#mapTitle').textContent.includes('متوسط الشدة')")
    page.locator('#methodsOpen').click()
    assert page.locator('.methods-ar').is_visible() and not page.locator('.methods-en').is_visible()
    page.locator('#methodsClose').click()
    page.locator('#climateThisYear').click()
    page.locator('.intro').screenshot(path=str(qa/'portal_ar_intro.png'))
    page.locator('#climate').screenshot(path=str(qa/'portal_ar_climate.png'))
    page.locator('#habitats').scroll_into_view_if_needed()
    page.wait_for_function("[...document.querySelectorAll('.habitat-gallery img')].every(i=>i.complete && i.naturalWidth>0)")
    page.locator('#habitats').screenshot(path=str(qa/'portal_ar_habitats.png'))
    audit=page.evaluate("""() => {const result=[];const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);while(w.nextNode()){const n=w.currentNode;if(n.parentElement.closest('script,style,.methods-en,.methods-ar,[data-no-i18n]'))continue;const t=n.nodeValue.trim();if(/[a-z]{4}/i.test(t)&&n.parentElement.getClientRects().length)result.push(t);}return [...new Set(result)];}""")
    (qa/'arabic_text_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.screenshot(path=str(qa/'portal_ar_mobile.png'),full_page=True)
    page.reload(wait_until='networkidle')
    assert page.evaluate('document.documentElement.lang')=='ar'
    page.locator('[data-language=en]').click()
    page.wait_for_function("document.querySelector('h1').textContent==='Marine heatwaves in coastal habitats'")
    assert page.evaluate('document.documentElement.dir')=='ltr'
    assert 'Prediction probability' in page.locator('#metric option[value=outlook_probability]').inner_text()
    assert not errors,errors
    assert not http,http
    browser.close()
(qa/'portal_results.json').write_text(json.dumps({'passed':True,'year':current_year,'annualMonths':len(expected),'pageErrors':errors,'httpErrors':http},indent=2))
print('PASS: Arabic/English persistence and layout; latest cards, 2026 monthly/partial annual climate, seasonal link and original photos.')
