/* One large, keyboard-accessible point window keeps the map in view. */
(() => {
  const $=id=>document.getElementById(id),T=s=>AtlasLanguage.translate(s);
  AtlasLanguage.add({'2026 to date':'2026 حتى الآن','OBSERVATIONS':'الرصد','Download 2026 observations':'تنزيل رصد 2026','Heatwave metric':'متغير الموجات الحارة','Point analysis':'تحليل النقطة','Open point analysis':'افتح تحليل النقطة','Back to map':'العودة إلى الخريطة','Overview':'نظرة عامة','Heatwave history':'سجل الموجات الحارة','Daily and monthly':'اليومي والشهري','Climate links':'العلاقات المناخية','Outlook':'التوقع الموسمي','Detailed shoreline':'خط الساحل المفصل','Data update progress':'متابعة تحديث البيانات'});
  const dialog=document.createElement('dialog');dialog.id='pointAnalysis';dialog.className='point-analysis-dialog';dialog.setAttribute('aria-labelledby','pointWindowTitle');
  dialog.innerHTML='<header class="point-window-heading"><div><span class="eyebrow">Point analysis · Under testing</span><h2 id="pointWindowTitle"></h2></div><div class="point-window-controls"><label>Temperature record<select id="pointWindowProduct"></select></label><label>Heatwave metric<select id="pointWindowMetric"></select></label></div><button id="closePointAnalysis" class="button outline">Back to map</button></header><nav id="pointWindowTabs" class="point-window-tabs" aria-label="Point analysis"></nav><div id="pointWindowBody" class="point-window-body"></div>';
  document.body.append(dialog);
  const body=$('pointWindowBody'),overview=document.createElement('section');overview.id='pointOverview';overview.className='point-window-overview';
  overview.append(document.querySelector('.pixel-panel'));overview.querySelector('.pixel-panel').append(document.querySelector('section.point-outlook'));body.append(overview);
  const current=document.createElement('section');current.id='observed2026';current.className='analysis-section';current.innerHTML='<div class="section-heading"><div><span class="eyebrow">OBSERVATIONS</span><h2>2026 to date</h2><p id="observed2026Note">The 2026 habitat records are being downloaded and checked.</p></div><a class="text-button" href="./status/" target="_blank">Data update progress</a></div><div id="observed2026Plot" class="large-chart" hidden></div><p id="observed2026Source" class="detail-note"></p><div id="observed2026Metrics" class="observed-metrics-table"></div><button id="observed2026MetricsCsv" class="text-button" hidden>Download 2026 metrics CSV</button><div id="observed2026Comparison" class="large-chart" hidden></div><p id="observed2026ComparisonCaption" class="detail-note"></p><a class="text-button" href="./observed2026/habitat_ecoregion_summary_2026.csv" download>Habitat and ecoregion summary CSV</a> · <button id="observed2026Csv" class="text-button" hidden>Download 2026 observations</button>';body.append(current);
  const items=[['pointOverview','Overview'],['observed2026','2026 to date'],['history','Heatwave history'],['detail','Daily and monthly'],['connections','Climate links'],['outlook','Outlook'],['climate','Climate indices']];
  for(const [id,label] of items){const section=$(id);if(id!=='pointOverview')body.append(section);const button=document.createElement('button');button.type='button';button.textContent=label;button.onclick=()=>section.scrollIntoView({block:'start',behavior:'auto'});$('pointWindowTabs').append(button);}
  const launch=document.createElement('button');launch.id='openPointAnalysis';launch.type='button';launch.className='button primary';launch.textContent='Open point analysis';document.querySelector('.explore-tools').prepend(launch);
  const progress=document.createElement('a');progress.className='update-progress-link';progress.href='./status/';progress.textContent='Data update progress';document.querySelector('.explore-tools').append(progress);
  for(const [copyId,sourceId] of [['pointWindowProduct','product'],['pointWindowMetric','metric']]){const source=$(sourceId),copy=$(copyId);copy.append(...[...source.options].filter(o=>o.value!=='outlook_probability').map(o=>new Option(o.text,o.value)));copy.value=source.value;copy.onchange=()=>{source.value=copy.value;source.dispatchEvent(new Event('change'));};source.addEventListener('change',()=>copy.value=source.value);}
  function heading(){if(document.documentElement.dataset.ready!=='true')return;const d=AtlasUI.snapshot();$('pointWindowTitle').textContent=`${d.point[1].toFixed(2)}°N, ${d.point[0].toFixed(2)}°E · ${d.meta.regions[d.point[3]]}`;}
  function resize(){for(const plot of dialog.querySelectorAll('.js-plotly-plot'))if(plot.data&&plot.getBoundingClientRect().width>0)Plotly.Plots.resize(plot);window.dispatchEvent(new Event('resize'));}
  function open(section='pointOverview'){
    heading();if(!dialog.open)dialog.showModal();
    $('pointWindowProduct').value=$('product').value;$('pointWindowMetric').value=AtlasUI.snapshot().state.metric;
    $('outlookScope').value='pixel';$('outlookScope').dispatchEvent(new Event('change'));
    requestAnimationFrame(()=>{resize();$(section)?.scrollIntoView({block:'start',behavior:'auto'});});
  }
  launch.onclick=()=>open();$('closePointAnalysis').onclick=()=>dialog.close();dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  for(const link of document.querySelectorAll('a[href^="#"]')){const id=link.getAttribute('href').slice(1);if(items.some(item=>item[0]===id))link.addEventListener('click',e=>{e.preventDefault();open(id);});}
  window.addEventListener('atlaspointopen',()=>open());window.addEventListener('atlaspixelchange',heading);window.addEventListener('atlasready',heading);
  dialog.addEventListener('toggle',()=>{if(dialog.open)window.dispatchEvent(new Event('atlaspointwindowopen'));});
  dialog.addEventListener('close',()=>AtlasUI.map.invalidateSize());
  window.AtlasPointWindow={open,close:()=>dialog.close()};
})();
