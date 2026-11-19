/* Keep existing control IDs and scientific state while reducing first-screen load. */
(() => {
  const $=id=>document.getElementById(id);
  const drawer=document.createElement('dialog');drawer.id='filtersDialog';drawer.className='side-drawer';drawer.setAttribute('aria-labelledby','filterTitle');drawer.innerHTML='<div class="dialog-heading"><h2 id="filterTitle">More filters</h2><button id="filtersClose" aria-label="Close filters"></button></div><div class="dialog-body"><div id="secondaryControls"></div></div>';document.body.append(drawer);
  for(const id of ['region','product'])$('secondaryControls').append($(id).closest('label'));
  $('secondaryControls').append(document.querySelector('.layers-toolbar'));
  const open=document.createElement('button');open.type='button';open.id='filtersOpen';open.className='button outline';open.textContent='More filters';document.querySelector('.toolbar').append(open);open.onclick=()=>drawer.showModal();$('filtersClose').onclick=()=>drawer.close();drawer.onclick=e=>{if(e.target===drawer)drawer.close();};
  const methods=$('methodsDialog');methods.classList.add('side-drawer');methods.setAttribute('aria-label','Data and methods');
  for(const body of methods.querySelectorAll('.dialog-body')){const ar=body.classList.contains('methods-ar'),toc=document.createElement('nav');toc.className='methods-toc';toc.setAttribute('aria-label',ar?'محتويات المنهجية':'Methods contents');const children=[...body.children];let section;
    for(const child of children){if(child.tagName==='H3'){section=document.createElement('details');section.className='method-section';const summary=document.createElement('summary');summary.textContent=child.textContent;section.append(summary);child.replaceWith(section);const button=document.createElement('button');button.type='button';button.textContent=summary.textContent;button.onclick=()=>{section.open=true;section.scrollIntoView({block:'start',behavior:'auto'});};const target=section;button.onclick=()=>{target.open=true;target.scrollIntoView({block:'start',behavior:'auto'});};toc.append(button);}else if(section)section.append(child);}
    body.prepend(toc);
  }
  function help(element,term,description){if(!element||element.querySelector('.term-help'))return;const details=document.createElement('details');details.className='term-help';const button=document.createElement('summary');button.textContent='i';button.setAttribute('aria-label',term);const text=document.createElement('span');text.textContent=description;details.append(button,text);element.after(details);}
  help(document.querySelector('.intro h1'),'Marine heatwave','At least five days above the seasonally varying local 90th-percentile temperature threshold.');
  help(document.querySelector('.variation-card .small-tag'),'Shapley R²','Allocates the fitted variation among predictors while sharing credit between correlated indices.');
  help($('modelCv').parentElement,'Leave-one-year-out R²','Fits each year using the other years; negative scores mean poorer fit than the reference mean.');
  help($('pointSkill').parentElement,'Brier skill','Compares probability errors with the historical-probability baseline; positive is better.');
  help($('outlookDefinition'),'90th-percentile threshold','A temperature exceeded on about one in ten baseline days for the same time of year.');
  help($('outlookSubtitle'),'Lead time','The interval from forecast issue to the start of the predicted season.');
  help($('outlookDates'),'Backtest','Recreates past forecasts using only data available before each test season.');
  const pointBar=document.createElement('div');pointBar.id='pointProbabilityBar';pointBar.className='point-probability-bar';$('pointOutlookPeriod').after(pointBar);
  async function probability(){if(document.documentElement.dataset.ready!=='true')return;const d=AtlasUI.snapshot(),pixel=d.state.pixel,f=await AtlasUI.forecast(d.state.product,pixel);if(!f||pixel!==AtlasUI.snapshot().state.pixel)return;pointBar.replaceChildren();const track=document.createElement('div');track.className='probability-track';track.innerHTML=`<span style="width:${f.probability*100}%"></span><i style="left:${f.baseline*100}%" title="Historical baseline"></i>`;const text=document.createElement('span');text.textContent='Model probability · marker: historical baseline';pointBar.append(track,text);}
  for(const event of ['atlasready','atlaspixelchange','atlaslanguagechange'])window.addEventListener(event,probability);
})();
