"""Exercise both study areas, computed dotted curves and a Gulf point report."""
from pathlib import Path
import csv
import io
import json
import fitz
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'qa';QA.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1050})
    errors=[];http=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:http.append([r.status,r.url]) if r.status>=400 else None)
    page.goto('http://127.0.0.1:8765/?lang=en&basin=gulf&lat=25.2&lon=51.6&variable=outlook_probability',wait_until='networkidle')
    page.wait_for_function("document.documentElement.dataset.ready==='true' && document.querySelector('#pointProbability').textContent!=='—'",timeout=60000)
    assert page.locator('#totalPixels').inner_text()=='15,940'
    assert page.evaluate('window.AtlasDebug.state.pixel>=49408')
    assert page.locator('#region option').count()==3
    assert 'Arabian Gulf' in page.title()
    assert page.evaluate("document.querySelector('#modelPlot').data.find(t=>t.name==='Combined model').line.dash")=='dot'
    assert page.evaluate("document.querySelector('#historyPlot').data.at(-1).line.dash")=='dot'
    page.locator('#showTrend').uncheck()
    page.wait_for_function("document.querySelector('#historyPlot').data.length===1")
    page.locator('#showTrend').check()
    page.wait_for_function("document.querySelector('#historyPlot').data.length===2")
    with page.expect_download() as item:page.locator('#downloadHistory').click()
    item.value.save_as(str(QA/'gulf_history.csv'))
    rows=list(csv.DictReader(io.StringIO((QA/'gulf_history.csv').read_text(encoding='utf-8-sig'))))
    assert set(r['series'] for r in rows)=={'observed','fitted_linear_trend'}
    assert all(r['pixel'].startswith('gulf_') for r in rows)
    page.locator('#climateTrend').check()
    page.wait_for_function("document.querySelector('#climatePlot').data.some(t=>t.line.dash==='dot')")
    page.locator('#outlookScope').select_option('overall')
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===3")
    assert all('Arabian Gulf' in t for t in page.locator('.region-name').all_inner_texts())
    page.locator('#outlookScope').select_option('ecoregion')
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===5")
    page.locator('#region').select_option('4',force=True)
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===2")
    assert all('Gulf of Oman' in t for t in page.locator('.region-name').all_inner_texts())
    page.locator('#region').select_option('all',force=True)
    page.locator('#product').select_option('oisst',force=True)
    page.wait_for_function("document.querySelector('#pointValidationYears').textContent.includes('13')")
    with page.expect_download(timeout=60000) as item:page.locator('#createReport').click()
    item.value.save_as(str(QA/'gulf_point_report.pdf'))
    doc=fitz.open(QA/'gulf_point_report.pdf');text='\n'.join(p.get_text() for p in doc)
    assert 'gulf_ghrsst_' in text and 'Gulf of Oman' in text
    assert 'Red Sea & Gulf of Aden' not in text
    for j,pdf_page in enumerate(doc):pdf_page.get_pixmap(dpi=100).save(QA/f'gulf_report_p{j+1}.png')
    page.locator('[data-language=ar]').click()
    page.wait_for_function("document.querySelector('title').textContent.includes('الخليج')")
    assert page.evaluate('document.documentElement.dir')=='rtl'
    page.locator('.atlas-layout').screenshot(path=str(QA/'gulf_ar_map.png'))
    page.locator('#connections').screenshot(path=str(QA/'gulf_ar_models.png'))
    page.locator('#basin').select_option('all',force=True)
    page.locator('#outlookScope').select_option('ecoregion')
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===14")
    assert page.locator('#totalPixels').inner_text()=='65,348'
    page.locator('#outlookScope').select_option('overall')
    page.wait_for_function("document.querySelectorAll('.outlook-card').length===6")
    page.locator('#basin').select_option('redsea',force=True)
    page.wait_for_function("window.AtlasDebug.state.pixel<49408 && document.querySelectorAll('.outlook-card').length===3")
    assert page.locator('#totalPixels').inner_text()=='49,408'
    page.locator('#basin').select_option('gulf',force=True)
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.evaluate('scrollTo(0,0)');page.screenshot(path=str(QA/'gulf_mobile_header.png'))
    assert not errors,errors
    assert not http,http
    browser.close()
(QA/'gulf_browser_results.json').write_text(json.dumps({'passed':True,'pdfPages':len(doc),'pageErrors':errors,'httpErrors':http},indent=2))
print('PASS: both basins, source-cell forecasts, basin/region scopes, dotted fits, CSV series, Gulf PDF and Arabic mobile layout.')
