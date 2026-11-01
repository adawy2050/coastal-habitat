/* Red Sea Habitat Heatwave Atlas. All scientific arrays are fetched locally. */
(() => {
  'use strict';
  const RELEASE='20261101-combinations-r2';
  const $ = id => document.getElementById(id), S = window.AtlasStats;
  const labels = {Nino34: 'Niño-3.4', IOD: 'IOD', NAO: 'NAO', AO: 'AO', EAWR: 'EAWR', NAtl_SSTA: 'N. Atlantic SST', PDO: 'PDO',localSst:'Annual SST (OISST)'};
  const modeColors = {Nino34:'#9b5844', IOD:'#3b7772', NAO:'#7b6b85', AO:'#4e708f', EAWR:'#958044', NAtl_SSTA:'#9b6f7b', PDO:'#73855c',localSst:'#6b7661'};
  const metricInfo = {
    mhw_days: {name:'Heatwave days', unit:'days', axis:'Heatwave days / year', max:200, digits:0},
    mhw_frequency: {name:'Event frequency', unit:'events', axis:'Events / year', max:12, digits:1},
    mhw_mean_duration: {name:'Mean event duration', unit:'days', axis:'Mean duration (days)', max:40, digits:1},
    mhw_mean_intensity: {name:'Mean intensity', unit:'°C', axis:'Mean intensity (°C relative to threshold)', max:1.5, digits:2},
    mhw_max_intensity: {name:'Maximum intensity', unit:'°C', axis:'Maximum intensity (°C relative to threshold)', max:3, digits:2},
    mhw_cumulative_intensity: {name:'Cumulative intensity', unit:'°C days', axis:'Cumulative intensity (°C days)', max:160, digits:1}
  };
  const state = {product:'mur', metric:'mhw_days',mapMode:'history', year:2026, basin:'all',region:'all', habitats:13, selection:null,historySecondary:'mhw_frequency', pixel:0, pins:[], arrays:new Map(),showTrend:true,climateTrend:false,
    from:2003, to:2025, lag:0, benchmark:'trend', index:'Nino34', detrend:true, selectedModes:new Set(['Nino34','IOD','NAtl_SSTA','AO']),
    step:'monthly', scale:'standard', climateSource:'latest',climateFrom:null,climateTo:null,outlookRecord:'GHRSST MUR',outlookScope:'ecoregion',pixelOpacity:.7,showPixels:true,timer:null,generation:0};
  let meta, pixels, climate, map, pixelLayer, selectedMarker, sourceMarker, sourceLine, climateZ, mapLand,landLayer,satelliteLayer,coverageMeta,liveClimate,outlook,externalModels;
  let outlookInputs='external';
  function externalInfo(product,ignoreChoice=false){const info=externalModels?.products[product];return (ignoreChoice||outlookInputs==='external')&&info&&info.nativeCells===meta?.products[product]?.cells.length&&externalModels.referenceAsOf===outlook?.asOf&&externalModels.seasonStart===outlook?.pixelOutlooks[product]?.seasonStart&&externalModels.forecastIssueMonth===outlook.pixelOutlooks[product].issueDate.slice(0,7)?info:null;}
  const coverageLayers={};
  let modelData = null, currentHistory = [], climateExport = [], historyTicket=0, modelTicket=0;
  const pinColors = ['#3f7f82','#997ba0','#9b954d','#5f809d','#c68f57'];
  const config = {responsive:true, displaylogo:false, scrollZoom:false, modeBarButtonsToRemove:['lasso2d','select2d','autoScale2d'],
    toImageButtonOptions:{format:'svg', filename:'redsea_habitat_mhw', height:550, width:1100, scale:1}};
  const baseLayout = {paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)', font:{family:'system-ui, sans-serif',size:10,color:'#657775'},
    margin:{l:58,r:20,t:30,b:46}, hovermode:'x unified', hoverlabel:{font:{size:10},bgcolor:'#fff',bordercolor:'#ddd'},
    xaxis:{gridcolor:'#f0f1eb',linecolor:'#dfe3d9',zeroline:false,tickformat:'d',fixedrange:false},
    yaxis:{gridcolor:'#edf0e7',zeroline:false,title:{font:{size:10}},fixedrange:false},
    legend:{orientation:'h',x:0,y:1.15,font:{size:10}}, showlegend:true};
  function layout(extra={}) { return {...baseLayout,...extra,xaxis:{...baseLayout.xaxis,...extra.xaxis},yaxis:{...baseLayout.yaxis,...extra.yaxis}}; }
  function renderPlot(id,traces,chartLayout,options=config){
    const localize=(value,key)=>{if(typeof value==='string')return ['name','text','title'].includes(key)&&window.AtlasLanguage?.current!=='en'?window.AtlasLanguage.translate(value):value;if(Array.isArray(value))return value.map(v=>localize(v,key));if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).map(([k,v])=>[k,localize(v,k)]));return value;};
    return Plotly.react(id,localize(traces,''),localize(chartLayout,''),options);
  }
  function note(message) { $('toast').textContent=message; $('toast').hidden=false; clearTimeout(note.timer); note.timer=setTimeout(()=>{$('toast').hidden=true;},4000); }
  function loading(message) { $('loadingText').textContent=message; $('loading').hidden=false; }
  async function json(path) { const r=await fetch(`${path}?v=${RELEASE}`); if(!r.ok)throw Error(`${path}: HTTP ${r.status}`); return r.json(); }
  async function array(product, metric) {
    const key=`${product}_${metric}`;
    if(!state.arrays.has(key)) state.arrays.set(key, fetch(`./data/${key}.f32?v=${RELEASE}`).then(r=>{if(!r.ok)throw Error(`Unable to load ${key}`);return r.arrayBuffer();}).then(buffer=>{
      const a=new Float32Array(buffer), p=meta.products[product];
      if(a.length!==p.years.length*p.cells.length)throw Error(`Unexpected data dimensions: ${key}`);return a;
    }).catch(e=>{state.arrays.delete(key);throw e;}));
    return state.arrays.get(key);
  }
  async function mapValues(product,metric,year=state.year){if(year===2026)return AtlasObserved2026.mapValues(product,metric);const a=await array(product,metric),p=meta.products[product],k=p.years.indexOf(year);if(k<0)throw Error('Map year unavailable.');return a.subarray(k*p.cells.length,(k+1)*p.cells.length);}
  async function forecastArray(product,name){const extra=externalInfo(product),file=extra?.files[name],key=(file?'issued_':'')+`${product}_outlook_${name}`;if(!state.arrays.has(key))state.arrays.set(key,fetch((file?'./forecasts/'+file:`./data/${product}_outlook_${name}.f32`)+`?v=${RELEASE}`).then(r=>{if(!r.ok)throw Error(`Unable to load point forecast ${name}`);return r.arrayBuffer();}).then(b=>new Float32Array(b)));return state.arrays.get(key);}
  async function pointForecast(product,pixel){
    const original=outlook.pixelOutlooks[product];if(!original)return null;const extra=externalInfo(product),info=extra?{...original,...extra}:original;const index=sourceIndex(pixel,product),names=['probability','baseline','threshold','skill','skill_all','brier','baseline_brier','n_high','alpha'];
    const arrays=await Promise.all(names.map(name=>forecastArray(product,name))),values=Object.fromEntries(names.map((name,i)=>[name,arrays[i][index]]));
    const external=extra?Object.fromEntries(await Promise.all(['reference_probability','candidate_probability','selected_weight','gain','candidate_gain','latest_season_days'].map(async name=>[name,(await forecastArray(product,name))[index]]))):null;
    return {...info,...values,external,index,product,pixel,available:true,scope:'pixel',habitat:'Selected habitat pixel',region:`${coordinate(pixel)} · ${meta.regions[pixels[pixel][3]]}`,
      historicalProbability:values.baseline,highExposureThresholdDays:values.threshold,trainingSeasons:info.trainingYears.length,
      trainingFirstYear:info.trainingYears[0],trainingLastYear:info.trainingYears.at(-1),backtest:{scores:{baseline_available:{nTest:info.nTest,nHigh:values.n_high,skill:values.skill,brierScore:values.brier,baselineBrierScore:values.baseline_brier},all_retrospective:{nTest:info.nTestRetrospective,skill:values.skill_all}}}};
  }
  function mapInfo(){return state.mapMode==='probability'?{name:'Prediction probability',unit:'%',axis:'High-exposure probability (%)',max:100,digits:1}:metricInfo[state.metric];}
  function percent(value){return value<.01?'<1%':`${Math.round(value*100)}%`;}
  function sourceIndex(pixel, product=state.product) {return pixels[pixel][product==='mur'?4:5];}
  function series(pixel, a, product=state.product) {
    const p=meta.products[product], n=p.cells.length, index=sourceIndex(pixel,product);
    return p.years.map((_,i)=>{const v=a[i*n+index];return Number.isFinite(v)?v:null;});
  }
  function number(v,digits=1) {return S.finite(v)?v.toLocaleString('en',{minimumFractionDigits:digits,maximumFractionDigits:digits}):'—';}
  function signed(v,digits=1) {return S.finite(v)?`${v>=0?'+':''}${number(v,digits)}`:'—';}
  function coordinate(i) {const p=pixels[i];return `${p[1].toFixed(2)}°N, ${p[0].toFixed(2)}°E`;}
  function pointBasin(point){return meta.basins.find(b=>b.regions.includes(point[3]));}
  function pixelId(i) {return `${pointBasin(pixels[i]).id==='redsea'?'':pointBasin(pixels[i]).id+'_'}ghrsst_${String(pixels[i][8]).padStart(5,'0')}_${String(pixels[i][9]).padStart(5,'0')}`;}
  function visible(p) {return (!state.selection||(p[0]>=state.selection[0]&&p[0]<=state.selection[2]&&p[1]>=state.selection[1]&&p[1]<=state.selection[3]))&&(p[2]&state.habitats)!==0&&(state.region==='all'||p[3]===Number(state.region))&&(state.basin==='all'||pointBasin(p).id===state.basin);}
  function regionControls(){const options=[new Option('All ecoregions','all')];meta.regions.forEach((name,index)=>{if(state.basin==='all'||meta.basins.find(b=>b.id===state.basin).regions.includes(index))options.push(new Option(name,index));});$('region').replaceChildren(...options);$('region').value=state.region;$('totalPixels').textContent=(state.basin==='all'?meta.pixels:meta.basins.find(b=>b.id===state.basin).pixels).toLocaleString('en-GB');}
  function fitStudy(){map.fitBounds(state.selection?[[state.selection[1],state.selection[0]],[state.selection[3],state.selection[2]]]:(state.basin==='all'?meta.bounds:meta.basins.find(b=>b.id===state.basin).bounds),{padding:[55,45]});}
  function color(v, max) {
    if(!S.finite(v))return '#6b8583';
    const stops=[[0,34,78],[0,46,106],[26,56,111],[50,67,109],[67,78,108],[83,90,109],[97,101,111],[111,112,115],[125,124,120],[140,136,120],[155,148,118],[171,160,114],[188,174,108],[205,187,99],[222,201,88],[240,216,70],[254,232,56]];
    const z=Math.max(0,Math.min(.99999,v/max))*(stops.length-1), i=Math.floor(z), t=z-i;
    return `rgb(${stops[i].map((c,k)=>Math.round(c+(stops[i+1][k]-c)*t)).join(',')})`;
  }
  function inYears(year) {return year>=state.from&&year<=state.to;}
  function monthLabel(value){return new Date(`${value.slice(0,7)}-01T00:00:00Z`).toLocaleDateString('en-GB',{month:'short',year:'numeric',timeZone:'UTC'});}
  function download(name, content, mime='text/csv;charset=utf-8') {
    const url=URL.createObjectURL(new Blob([content],{type:mime})), a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);
  }
  function csv(rows) {if(!rows.length)return '';const keys=[...new Set(rows.flatMap(row=>Object.keys(row)))],escape=v=>{const s=v===null||v===undefined?'':String(v);return /[",\n]/.test(s)?`"${s.replaceAll('"','""')}"`:s;};return [keys,...rows.map(r=>keys.map(k=>r[k]))].map(row=>row.map(escape).join(',')).join('\r\n');}
  function showMethods() {$('methodsDialog').showModal();}

  function makeMap(land) {
    mapLand=land;
    map=L.map('map',{zoomControl:false,attributionControl:true,minZoom:3,maxZoom:16,preferCanvas:true});fitStudy();
    map.attributionControl.setPrefix('');map.attributionControl.addAttribution('<a href="https://www.unep-wcmc.org/" target="_blank">UNEP-WCMC: coral 2021, seagrass 2021, mangroves 2010</a>');
    L.control.zoom({position:'topright'}).addTo(map);
    map.createPane('coastBase');map.getPane('coastBase').style.zIndex=230;
    landLayer=L.geoJSON(land,{pane:'coastBase',interactive:false,style:{color:'#8994a3',weight:.55,fillColor:'#d4dae1',fillOpacity:1}});
    satelliteLayer=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,detectRetina:true,crossOrigin:true,attribution:'Imagery © Esri, Vantor, Earthstar Geographics, GIS User Community'});
    satelliteLayer.addTo(map);
    map.createPane('habitatCoverage');map.getPane('habitatCoverage').style.zIndex=390;map.getPane('habitatCoverage').style.pointerEvents='none';
    const empty='data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs=';
    for(const habitat of meta.habitats){const keys=new Set(coverageMeta.tiles[habitat]||[]);const Coverage=L.TileLayer.extend({getTileUrl(coords){const key=`${coords.z}/${coords.x}/${coords.y}`;return keys.has(key)?new URL(`./coverage/${habitat}/${key}.png?v=${RELEASE}`,document.baseURI).href:empty;}});coverageLayers[habitat]=new Coverage('',{pane:'habitatCoverage',minZoom:4,maxNativeZoom:12,maxZoom:16,opacity:.95,crossOrigin:true,errorTileUrl:empty});if(document.querySelector(`input[name="coverage"][value="${habitat}"]`)?.checked!==false)coverageLayers[habitat].addTo(map);}
    for(const [name,lat,lon,kind] of [['EGYPT',27.7,30.3,'country'],['SAUDI ARABIA',25.7,43.5,'country'],['SUDAN',20.8,33.5,'country'],['ERITREA',15.7,37.4,'country'],['YEMEN',15.8,47,'country'],['SOMALIA',9.6,47.5,'country'],['Red Sea',22.7,38.9,'sea'],['Gulf of Aden',12.5,47.8,'sea']]) {
      L.tooltip({permanent:true,direction:'center',className:`country-label ${kind==='sea'?'sea-label':''}`,interactive:false}).setLatLng([lat,lon]).setContent(name).addTo(map);
    }
    for(const [name,lat,lon,kind] of [['Arabian Gulf',27.4,51.5,'sea'],['Gulf of Oman',24.3,58.4,'sea'],['IRAN',29.4,55.2,'country'],['OMAN',22.7,56.5,'country'],['UAE',24.3,54.4,'country'],['KUWAIT',29.6,47.3,'country']])L.tooltip({permanent:true,direction:'center',className:`country-label ${kind==='sea'?'sea-label':''}`,interactive:false}).setLatLng([lat,lon]).setContent(name).addTo(map);
    const HabitatLayer=L.Layer.extend({
      onAdd(mapRef){this._map=mapRef;this.canvas=L.DomUtil.create('canvas','habitat-canvas');this.canvas.style.position='absolute';this.canvas.style.pointerEvents='none';mapRef.getPane('overlayPane').appendChild(this.canvas);mapRef.on('moveend zoomend resize',this.draw,this);this.draw();},
      onRemove(mapRef){mapRef.off('moveend zoomend resize',this.draw,this);this.canvas.remove();},
      draw(){if(!this.a)return;const size=this._map.getSize(),dpr=window.devicePixelRatio||1,canvas=this.canvas;
        canvas.width=size.x*dpr;canvas.height=size.y*dpr;canvas.style.width=`${size.x}px`;canvas.style.height=`${size.y}px`;
        L.DomUtil.setPosition(canvas,this._map.containerPointToLayerPoint([0,0]));
        const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.globalAlpha=state.showPixels?state.pixelOpacity:0;const p=meta.products[state.product],n=p.cells.length,yi=p.years.indexOf(state.year),info=mapInfo(),bounds=this._map.getBounds().pad(.03);
        const step=Math.max(1.7,Math.abs(this._map.latLngToContainerPoint([20,40.01]).x-this._map.latLngToContainerPoint([20,40]).x));
        let count=0;
        const centre=this._map.getCenter(),key=[centre.lat,centre.lng,this._map.getZoom(),size.x,size.y,state.basin,state.region,state.habitats,state.product].join('|');
        if(this.positionKey!==key){this.positionKey=key;this.positions=[];this.filteredCount=0;for(let i=0;i<pixels.length;i++){const point=pixels[i];if(!visible(point))continue;this.filteredCount++;if(!bounds.contains([point[1],point[0]]))continue;const q=this._map.latLngToContainerPoint([point[1],point[0]]);this.positions.push([i,q.x,q.y,sourceIndex(i)]);}}
        count=this.filteredCount;
        for(const [i,x,y,source] of this.positions){const v=state.mapMode==='probability'?this.probabilityArray[source]*100:state.year===2026?this.currentArray?.[source]:this.a[yi*n+source];ctx.fillStyle=color(v,info.max);ctx.fillRect(x-step/2,y-step/2,step,step);}

        $('visibleCount').textContent=state.showPixels?`${count.toLocaleString()} habitat cells · click to explore`:'Inventory coverage · heatwave pixels hidden';
      }
    });
    pixelLayer=new HabitatLayer().addTo(map);
    selectedMarker=L.circleMarker([0,0],{radius:7,className:'selected-habitat-marker',color:'#315f69',weight:2.3,fillColor:'#e5f2ec',fillOpacity:.4,interactive:false}).addTo(map);
    sourceMarker=L.circleMarker([0,0],{radius:3,color:'#b4d2c2',weight:1,fillOpacity:.6,interactive:false}).addTo(map);
    sourceLine=L.polyline([],{color:'#afd4c2',weight:1,dashArray:'3,4',interactive:false}).addTo(map);
    map.on('click',e=>{
      let best=-1,distance=14*14;
      for(let i=0;i<pixels.length;i++){const p=pixels[i];if(!visible(p))continue;const q=map.latLngToContainerPoint([p[1],p[0]]),d=(q.x-e.containerPoint.x)**2+(q.y-e.containerPoint.y)**2;if(d<distance){distance=d;best=i;}}
      if(best>=0){selectPixel(best);window.dispatchEvent(new Event('atlaspointopen'));}else note('Zoom towards the coloured coastline, then select a habitat cell.');
    });
  }

  function setYearControls(reset=true) {
    const p=meta.products[state.product];if(reset){state.from=p.years[0];state.to=2026;}
    for(const id of ['fromYear','toYear']){$(id).replaceChildren(...[...p.years,2026].map(y=>new Option(y===2026?'2026 · to 20 Oct':y,y)));}
    $('fromYear').value=state.from;$('toYear').value=state.to;
    $('year').min=p.years[0];$('year').max=2026;$('yearStart').textContent=p.years[0];
    state.year=Math.max(p.years[0],Math.min(2026,state.year));$('year').value=state.year;
  }
  async function renderMap() {
    const product=state.product,metric=state.metric,token=++state.generation;
    loading('Loading habitat-pixel histories…');
    try {const [a,p,current]=await Promise.all([array(product,metric),state.mapMode==='probability'?forecastArray(product,'probability'):Promise.resolve(null),state.mapMode==='history'&&state.year===2026?mapValues(product,metric):Promise.resolve(null)]);if(token!==state.generation)return;if(state.mapMode==='history'&&state.year===2026&&!current){await renderMap();return;}pixelLayer.a=a;pixelLayer.currentArray=current;pixelLayer.probabilityArray=p;pixelLayer.draw();$('loading').hidden=true;updateMapText();await renderPixel();}
    catch(e){$('loadingText').textContent=`${e.message}. Reload to try again.`;console.error(e);}
  }
  function updateMapText() {
    const probability=state.mapMode==='probability',forecast=outlook.pixelOutlooks[state.product];
    $('mapTitle').replaceChildren(document.createTextNode(`${mapInfo().name} `),Object.assign(document.createElement('span'),{id:'mapYear',textContent:probability?`${forecast.season} ${forecast.seasonStart.slice(0,4)}`:state.year===2026?'2026 · to 20 Oct':state.year}));
    $('yearLabel').textContent=probability?`${forecast.season} ${forecast.seasonStart.slice(0,4)}`:state.year===2026?'2026 · to 20 Oct':state.year;const p=meta.products[state.product],info=mapInfo();
    for(const id of ['year','play'])$(id).hidden=probability;
    $('yearStart').textContent=probability?`${monthLabel(forecast.seasonStart.slice(0,7))}–${monthLabel(forecast.seasonEnd.slice(0,7))}`:p.years[0];
    document.querySelector('.timeline-caption').textContent=probability?'INDIVIDUAL PIXEL MODELS':'YEAR BY YEAR';document.querySelector('.year-climate').hidden=probability;
    $('mapNote').textContent=probability?`${p.name} source cells · ${forecast.leadMonths}-month lead · updated ${outlook.asOf}`:`${p.name} · ${p.resolution} SST · baseline ${p.baseline}${state.year===2026?' · 1 Jan–20 Oct 2026; event counts and durations describe within-year segments':''}`;
    $('legendTitle').textContent=info.axis;$('legendMax').textContent=`${info.max}+`;updatePixelValue();
    $('climateYearLabel').textContent=state.year===2026?'2026 index means · available months':`Climate in ${state.year}`;document.querySelector('.year-climate-heading span').textContent=state.year===2026?'Observed means · latest available months':'Annual indices · σ from 1982–2025';
    $('yearClimateValues').replaceChildren(...climate.modes.map(m=>{const e=document.createElement('div'),dot=document.createElement('i'),name=document.createElement('span'),value=document.createElement('strong');dot.style.background=modeColors[m];name.textContent=labels[m];const available=liveClimate.monthly.values[m].filter((v,i)=>liveClimate.monthly.dates[i].startsWith('2026-')&&S.finite(v));value.textContent=state.year===2026?(available.length?number(S.mean(available),2):'—'):`${signed(climateZ[m][state.year-1982],1)}σ`;e.append(dot,name,value);return e;}));
  }
  function updatePixelValue() {
    if(!pixelLayer?.a)return;const p=meta.products[state.product],a=pixelLayer.a,v=state.year===2026?pixelLayer.currentArray?.[sourceIndex(state.pixel)]:a[p.years.indexOf(state.year)*p.cells.length+sourceIndex(state.pixel)];
    if(state.mapMode==='probability'&&pixelLayer.probabilityArray){$('pixelValue').textContent=number(pixelLayer.probabilityArray[sourceIndex(state.pixel)]*100,1);$('pixelUnit').textContent=`% high-exposure probability · ${outlook.pixelOutlooks[state.product].season}`;return;}
    $('pixelValue').textContent=number(v,metricInfo[state.metric].digits);
    $('pixelUnit').textContent=`${metricInfo[state.metric].unit} ${state.year===2026?'· 1 Jan–20 Oct 2026':`in ${state.year}`}`;
  }
  function selectPixel(index, pan=false) {
    state.pixel=index;const p=pixels[index];if(pan)map.setView([p[1],p[0]],Math.max(map.getZoom(),8));
    renderPixel().catch(e=>{console.error(e);note('Unable to update the selected cell.');});
    const u=new URL(location.href);u.searchParams.set('lat',p[1].toFixed(2));u.searchParams.set('lon',p[0].toFixed(2));u.searchParams.set('product',state.product);u.searchParams.set('basin',state.basin);u.searchParams.set('variable',state.mapMode==='probability'?'outlook_probability':state.metric);history.replaceState(null,'',u);
  }
  async function renderPixel() {
    const index=state.pixel,product=state.product,metric=state.metric,a=await array(product,metric);
    if(index!==state.pixel||product!==state.product||metric!==state.metric)return;
    const p=pixels[index],native=meta.products[product],source=native.cells[sourceIndex(index)],values=series(index,a),ok=values.filter(S.finite),info=metricInfo[metric];
    selectedMarker.setLatLng([p[1],p[0]]);sourceMarker.setLatLng([source[1],source[0]]);sourceLine.setLatLngs([[p[1],p[0]],[source[1],source[0]]]);
    $('pixelTitle').textContent=coordinate(index);$('pixelRegion').textContent=meta.regions[p[3]];
    $('pixelHabitats').replaceChildren(...meta.habitats.filter((_,i)=>p[2]&(1<<i)).map(h=>{const e=document.createElement('span');e.className=`habitat-badge ${h}`;e.textContent=h==='kelp_macroalgae'?'Kelp & seaweeds':h;return e;}));
    updatePixelValue();const statLabels=document.querySelectorAll('.mini-stats>div>span');
    if(state.mapMode==='history'){['Record mean','Change / decade','Highest year'].forEach((text,j)=>statLabels[j].textContent=text);$('recordMean').textContent=ok.length?number(S.mean(ok),info.digits):'—';
    $('pixelTrend').textContent=signed(S.trend(native.years,values),info.digits===0?1:info.digits);
    const peak=ok.length?Math.max(...ok):null,idx=values.indexOf(peak);$('peakYear').textContent=idx>=0?native.years[idx]:'—';}
    else ['Historical probability','Brier skill','Test seasons'].forEach((text,j)=>statLabels[j].textContent=text);
    $('sourceCell').textContent=`${source[1].toFixed(product==='mur'?2:3)}°N, ${source[0].toFixed(product==='mur'?2:3)}°E · ${native.name}`;
    $('attachmentNote').textContent=`${number(p[product==='mur'?6:7],2)} km from habitat centre. ${product==='oisst'?'A shared 0.25° SST cell.':'Nearest valid 0.01° marine cell.'}`;
    Plotly.react('sparkline',[{x:native.years,y:values,type:'scatter',mode:'lines',line:{color:'#1768ac',width:1.5},fill:'tozeroy',fillcolor:'#d9e8f580',hovertemplate:'%{x}: %{y:.2f}<extra></extra>'}],{margin:{l:0,r:0,t:5,b:0},paper_bgcolor:'transparent',plot_bgcolor:'transparent',showlegend:false,xaxis:{visible:false},yaxis:{visible:false},font:{size:9}},{displayModeBar:false,responsive:true});
    window.dispatchEvent(new CustomEvent('atlaspixelchange',{detail:{basin:pointBasin(p).id,habitats:p[2],latitude:p[1],longitude:p[0],pixel:index}}));await Promise.all([renderHistory(),renderModel(),renderPointOutlook()]);if(state.outlookScope==='pixel')renderOutlook();
  }
  async function renderHistory() {
    const ticket=++historyTicket;const product=state.product,metric=state.metric,a=await array(product,metric);if(product!==state.product||metric!==state.metric)return;
    const p=meta.products[product],indices=[state.pixel,...state.pins.filter(i=>i!==state.pixel)];currentHistory=[];
    const traces=indices.map((index,j)=>{const values=series(index,a),years=p.years.filter(inYears),v=values.filter((_,k)=>inYears(p.years[k]));
      years.forEach((year,k)=>currentHistory.push({pixel:pixelId(index),latitude:pixels[index][1],longitude:pixels[index][0],product:p.name,year,metric,value:v[k],series:'observed'}));
      return {x:years,y:v,type:'scatter',mode:'lines+markers',name:coordinate(index),line:{color:j===0?'#1768ac':pinColors[(j-1)%pinColors.length],width:j===0?2.5:1.6},marker:{size:4},connectgaps:false,hovertemplate:`%{y:.2f} ${metricInfo[metric].unit}<extra>${coordinate(index)}</extra>`};
    });
    if(state.showTrend){const selected=traces[0],valid=selected.y.map((v,i)=>S.finite(v)?i:-1).filter(i=>i>=0);if(valid.length>=3){const years=valid.map(i=>selected.x[i]),fit=S.fit(valid.map(i=>selected.y[i]),[years]);traces.push({x:years,y:fit.pred,type:'scatter',mode:'lines',name:'Selected cell · fitted trend',line:{color:'#253444',width:2,dash:'dot'},hovertemplate:'%{y:.2f}<extra>Fitted linear trend</extra>'});years.forEach((year,k)=>currentHistory.push({pixel:pixelId(state.pixel),latitude:pixels[state.pixel][1],longitude:pixels[state.pixel][0],product:p.name,year,metric,value:fit.pred[k],series:'fitted_linear_trend'}));}}
    const second=state.historySecondary;
    if(second&&second!==metric){const key=second==='localSst'?'oisst':product,secondary=await array(key,second==='localSst'?'sst':second);if(product!==state.product||metric!==state.metric)return;const yy=meta.products[key].years,vv=series(state.pixel,secondary,key),keep=yy.map((y,i)=>inYears(y)?i:-1).filter(i=>i>=0),name=second==='localSst'?'Annual SST (OISST)':metricInfo[second].name;traces.push({x:keep.map(i=>yy[i]),y:keep.map(i=>vv[i]),name,type:'scatter',mode:'lines',yaxis:'y2',line:{color:'#7a6253',width:1.4,dash:'dash'},hovertemplate:'%{y:.2f}<extra>'+name+'</extra>'});keep.forEach(i=>currentHistory.push({pixel:pixelId(state.pixel),latitude:pixels[state.pixel][1],longitude:pixels[state.pixel][0],product:meta.products[key].name,year:yy[i],metric:second,value:vv[i],series:'observed_secondary_axis'}));}
    let currentEnd;
    if(state.to>=2026&&window.AtlasObserved2026){const records=await Promise.all(indices.map(index=>AtlasObserved2026.forPoint(index,product)));if(ticket!==historyTicket)return;records.forEach((record,j)=>{if(record?.product!==product)return;const trace=AtlasObserved2026.runningTrace(record,metric,{name:coordinate(indices[j])+' · 2026 to date',line:{color:j===0?'#98614d':pinColors[(j-1)%pinColors.length],width:1.8,dash:'dot'}});traces.push(trace);currentEnd=record.index.dateEnd;trace.y.forEach((value,k)=>currentHistory.push({pixel:pixelId(indices[j]),latitude:pixels[indices[j]][1],longitude:pixels[indices[j]][0],product:p.name,year:2026,metric,value,series:'observed_running_to_date',date:record.index.dates[k]}));});if(second&&second!==metric){const sourceProduct=second==='localSst'?'oisst':product,record=second==='localSst'?await AtlasObserved2026.forPoint(state.pixel,'oisst'):records[0];if(ticket!==historyTicket)return;if(record?.product===sourceProduct)traces.push(AtlasObserved2026.runningTrace(record,second,{name:(second==='localSst'?'Mean SST':metricInfo[second].name)+' · 2026 to date',yaxis:'y2',line:{color:'#7a6253',width:1.4,dash:'dot'}}));}}
    if(ticket!==historyTicket)return;
    renderPlot('historyPlot',traces,layout({margin:{l:65,r:70,t:45,b:48},yaxis:{title:metricInfo[metric].axis},yaxis2:{title:second&&second!==metric?(second==='localSst'?'SST (°C)':metricInfo[second].axis):'',overlaying:'y',side:'right',showgrid:false,zeroline:false,rangemode:second==='localSst'?'normal':'tozero',visible:!!second&&second!==metric},xaxis:{dtick:Math.max(1,Math.round((state.to-state.from)/9))},shapes:[{type:'line',xref:'x',x0:state.year,x1:state.year,yref:'paper',y0:0,y1:1,line:{color:'#a6b3a0',width:1,dash:'dot'}}]}),config);
    $('historyRangeStatus').textContent=currentEnd?'Observed through '+currentEnd:'Showing '+state.from+'–'+state.to+'; observations through 20 Oct 2026 are available.';
    $('historyCaption').textContent=`${p.name} · ${state.from}–${Math.min(state.to,2025)} annual values${currentEnd?' · dotted 2026: running values through '+currentEnd:''} · baseline ${p.baseline} · ${metricInfo[metric].unit}`;
    $('pins').replaceChildren(...state.pins.map((index,j)=>{const e=document.createElement('span');e.className='pin';const dot=document.createElement('i');dot.className='pin-dot';dot.style.background=pinColors[j%pinColors.length];const b=document.createElement('button');b.textContent='×';b.setAttribute('aria-label',`Remove ${coordinate(index)}`);b.onclick=()=>{state.pins=state.pins.filter(i=>i!==index);renderHistory();};e.append(dot,document.createTextNode(coordinate(index)),b);return e;}));
  }
  async function renderModel() {
    const ticket=++modelTicket;const product=state.product,metric=state.metric,pixel=state.pixel;
    const [a,sst]=await Promise.all([array(product,metric),array('oisst','sst')]);
    if(product!==state.product||metric!==state.metric||pixel!==state.pixel)return;
    const years=meta.products[product].years, values=series(pixel,a), sstSeries=series(pixel,sst,'oisst'),annual=climate.annual;
    const rows=years.map((year,i)=>{const climateIndex=annual.years.indexOf(year-state.lag),sstIndex=meta.products.oisst.years.indexOf(year);
      return {year, observed:values[i], reference:state.benchmark==='trend'?year:sstSeries[sstIndex],
        indices:climate.modes.map(m=>climateIndex>=0?annual.values[m][climateIndex]:null),sst:sstSeries[sstIndex]};
    }).filter(r=>inYears(r.year)&&[r.observed,r.reference,...r.indices].every(S.finite));
    if(rows.length<12){modelData=null;$('modelSample').textContent=`${rows.length} complete years · choose ≥12`;for(const id of ['modelR2','modelCv'])$(id).textContent='—';$('varianceBar').replaceChildren();$('shares').textContent='Select a longer period for the eight-predictor model.';const modelRendering=renderPlot('modelPlot',[],layout({annotations:[{text:'Choose at least 12 complete years.',xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false}]}),config);renderPaired(years,values,sstSeries);return;}
    const ys=rows.map(r=>r.year),y=rows.map(r=>r.observed),columns=[rows.map(r=>r.reference),...climate.modes.map((_,j)=>rows.map(r=>r.indices[j]))];
    const model=S.shapley(y,columns),base=S.fit(y,[columns[0]]),reference=state.benchmark==='trend'?'Long-term trend':'Annual SST (OISST)';
    modelData={rows,model,base,names:[reference,...climate.modes.map(m=>labels[m])],product,metric,pixel};
    $('modelSample').textContent=`${rows.length} complete years · ${ys[0]}–${ys.at(-1)}`;
    $('modelR2').textContent=number(model.r2,2);$('modelCv').textContent=number(model.cvR2,2);
    const observedCurrent=state.to>=2026&&window.AtlasObserved2026?await AtlasObserved2026.forPoint(pixel,product):null;if(ticket!==modelTicket)return;
    const modelRendering=renderPlot('modelPlot',[
      {x:ys,y,type:'scatter',mode:'lines+markers',name:'Observed',line:{color:'#1768ac',width:2},marker:{size:4}},
      {x:ys,y:base.pred,type:'scatter',mode:'lines',name:reference,line:{color:'#8e9e8c',width:1.5,dash:'dot'}},
      {x:ys,y:model.pred,type:'scatter',mode:'lines',name:'Combined model',line:{color:'#253444',width:2,dash:'dot'}},
      ...(observedCurrent?.product===product?[AtlasObserved2026.runningTrace(observedCurrent,metric)]:[])
    ],layout({margin:{l:52,r:12,t:37,b:37},legend:{...baseLayout.legend,y:1.17,font:{size:9}},yaxis:{title:metricInfo[metric].unit},xaxis:{dtick:Math.max(1,Math.round((state.to-state.from)/7))}}),config);
    modelRendering.then(()=>window.dispatchEvent(new Event('atlasmodelrender')));
    const colors=['#8591a0',...climate.modes.map(m=>modeColors[m])],bar=[];
    model.shares.forEach((v,j)=>{const e=document.createElement('span');e.style.width=`${v*100}%`;e.style.background=colors[j];e.title=`${modelData.names[j]}: ${number(v*100,1)}%`;bar.push(e);});$('varianceBar').replaceChildren(...bar);
    $('shares').replaceChildren(...model.shares.map((share,j)=>{const e=document.createElement('div');e.className='share-row';const dot=document.createElement('i');dot.style.background=colors[j];const name=document.createElement('span');name.textContent=modelData.names[j];const value=document.createElement('strong');value.textContent=`${number(share*100,1)}%`;value.title=`Coefficient per predictor SD: ${signed(model.beta[j],3)} ${metricInfo[metric].unit}`;e.append(dot,name,value);return e;}));
    const residual=document.createElement('div');residual.className='share-row';residual.innerHTML=`<i style="background:#e2e5dc"></i><span>Residual</span><strong>${number((1-model.r2)*100,1)}%</strong>`;$('shares').append(residual);
    renderPaired(years,values,sstSeries);
  }
  function renderPaired(years,values,sstSeries) {
    const local=state.index==='localSst';
    const keep=years.map((year,i)=>({year,y:values[i],x:local?sstSeries[meta.products.oisst.years.indexOf(year)]:climate.annual.values[state.index][climate.annual.years.indexOf(year-state.lag)]})).filter(r=>inYears(r.year)&&S.finite(r.y)&&S.finite(r.x));
    const ys=keep.map(r=>r.year),rawY=keep.map(r=>r.y),rawX=keep.map(r=>r.x);
    const y=state.detrend?S.detrend(rawY,ys):rawY,x=state.detrend?S.detrend(rawX,ys):rawX,r=S.correlation(y,x),d=state.detrend?'Detrended':'Raw';
    $('pairedTitle').textContent=`${labels[state.index]} & ${metricInfo[state.metric].name.toLowerCase()}`;
    $('pairedStat').textContent=`${d} r = ${number(r,2)} · n = ${keep.length}`;
    renderPlot('pairedPlot',[
      {x:ys,y:S.standardize(y),type:'scatter',mode:'lines+markers',name:`Heatwave metric${state.detrend?' (detrended)':''}`,line:{color:'#253444',width:2},marker:{size:3}},
      {x:ys,y:S.standardize(x),type:'scatter',mode:'lines',name:labels[state.index],line:{color:modeColors[state.index],width:1.8}}
    ],layout({margin:{l:52,r:15,t:35,b:38},yaxis:{title:'Standard deviations'},legend:{...baseLayout.legend,y:1.19},xaxis:{dtick:Math.max(1,Math.round((state.to-state.from)/9))}}),config);
    $('pairedCaption').textContent=local?`${d} annual series · same-year OISST mean SST at the attached habitat source cell · standardised over the same complete years.`:`${d} annual series · index lead ${state.lag} year${state.lag===1?'':'s'} · both series standardised over the same complete years.`;
  }
  function climateDateControls(){
    const dates=(state.climateSource==='latest'?liveClimate.monthly:climate.monthly).dates,first=Number(dates[0].slice(0,4)),last=Number(dates.at(-1).slice(0,4));
    state.climateFrom=Math.max(first,Math.min(state.climateFrom??last-10,last));state.climateTo=Math.max(state.climateFrom,Math.min(state.climateTo??last,last));
    for(const id of ['climateFrom','climateTo']){$(id).replaceChildren(...Array.from({length:last-first+1},(_,i)=>new Option(first+i,first+i)));$(id).value=state[id];}
    $('climateThisYear').disabled=state.climateSource!=='latest';
  }
  function renderLatestIndices(){
    $('latestIndexCards').replaceChildren(...climate.modes.map(mode=>{const dates=liveClimate.monthly.dates,values=liveClimate.monthly.values[mode];let i=values.length-1;while(i>=0&&!S.finite(values[i]))i--;const card=document.createElement('article');card.className='latest-index-card';
      const name=document.createElement('h3');name.textContent=labels[mode];const value=document.createElement('strong');value.textContent=i<0?'—':`${signed(values[i],2)}${['Nino34','IOD','NAtl_SSTA'].includes(mode)?' °C':''}`;const date=document.createElement('span');date.textContent=i<0?'Unavailable':monthLabel(dates[i]);
      card.append(name,value,date);return card;}));
  }
  function renderClimate() {
    const latest=state.climateSource==='latest',monthly=state.step==='monthly';let data=latest?liveClimate.monthly:climate[state.step];
    if(latest&&!monthly){const years=[...new Set(data.dates.map(d=>Number(d.slice(0,4))))],values={};for(const mode of climate.modes)values[mode]=years.map(year=>{const v=data.values[mode].filter((v,i)=>Number(data.dates[i].slice(0,4))===year&&S.finite(v));return v.length?S.mean(v):null;});data={years,values};}
    const x0=monthly?data.dates:data.years,keep=x0.map((x,i)=>({x,i,year:monthly?Number(x.slice(0,4)):x})).filter(d=>d.year>=state.climateFrom&&d.year<=state.climateTo);
    const modes=climate.modes.filter(m=>state.selectedModes.has(m));climateExport=[];
    keep.forEach(d=>{const row={date:d.x};modes.forEach(m=>{row[m]=data.values[m][d.i];if(latest&&!monthly)row[`${m}_months`]=liveClimate.monthly.values[m].filter((v,i)=>Number(liveClimate.monthly.dates[i].slice(0,4))===d.year&&S.finite(v)).length;});climateExport.push(row);});
    const traces=modes.map(m=>{const raw=keep.map(d=>data.values[m][d.i]),y=state.scale==='standard'?S.standardize(raw):raw;return {x:keep.map(d=>d.x),y,type:'scatter',mode:'lines',name:labels[m],line:{color:modeColors[m],width:monthly?1.3:2},connectgaps:false};});
    if(state.climateTrend)for(let k=0;k<modes.length;k++){const m=modes[k],line=traces[k],valid=line.y.map((v,i)=>S.finite(v)?i:-1).filter(i=>i>=0);if(valid.length<3)continue;const x=valid.map(i=>monthly?Date.parse(keep[i].x)/86400000:keep[i].x),fit=S.fit(valid.map(i=>line.y[i]),[x]),rawFit=S.fit(valid.map(i=>data.values[m][keep[i].i]),[x]);traces.push({x:valid.map(i=>line.x[i]),y:fit.pred,type:'scatter',mode:'lines',name:`${labels[m]} · fitted trend`,line:{color:modeColors[m],width:1.8,dash:'dot'}});valid.forEach((i,j)=>climateExport[i][`${m}_linear_fit`]=rawFit.pred[j]);}
    const tickformat=monthly?(state.climateFrom===state.climateTo?'%b %Y':'%Y'):'d';
    const climateRendering=renderPlot('climatePlot',traces,layout({xaxis:{type:monthly?'date':'linear',tickformat,dtick:monthly?undefined:Math.max(1,Math.round((state.climateTo-state.climateFrom)/9))},yaxis:{title:state.scale==='standard'?'Standard deviations':'Original index values'},annotations:traces.length?[]:[{text:'Select one or more indices above.',xref:'paper',yref:'paper',x:.5,y:.5,showarrow:false}]}),config);
    climateRendering.then(()=>window.dispatchEvent(new Event('atlasclimaterender')));
    $('climateRangeNote').textContent=`${state.climateFrom}–${state.climateTo} · climate dates are independent of heatwave analysis years`;
    $('climateCaption').textContent=latest?`NOAA feeds checked ${liveClimate.asOf} · latest: ${monthLabel(Object.values(liveClimate.latestByMode).sort().at(-1))}; IOD: ${monthLabel(liveClimate.latestByMode.IOD)} · missing months remain blank.${monthly?'':' Annual values for incomplete years are means of available months (year to date).'}`:state.scale==='standard'?`${monthly?'Monthly':'Annual'} indices · standardised within ${state.climateFrom}–${state.climateTo} · downloads retain original values.`:'Original values; index units differ. Use standardised scale for direct comparison.';
  }
  async function renderPointOutlook(){const pixel=state.pixel,product=state.product,f=await pointForecast(product,pixel);if(pixel!==state.pixel||product!==state.product)return;if(!f){$('pointOutlookTitle').textContent='Waiting for recent climate data';$('climateNextTitle').textContent='Waiting for recent climate data';$('climateNextDetail').textContent='';for(const id of ['pointProbability','pointBaseline','pointSkill'])$(id).textContent='—';return;}
    $('pointOutlookTitle').textContent=`${coordinate(pixel)} · ${meta.products[product].name}`;$('pointOutlookPeriod').textContent=`${monthLabel(f.seasonStart.slice(0,7))}–${monthLabel(f.seasonEnd.slice(0,7))} · ${f.leadMonths}-month lead · individual SST-source-cell model`;
    $('pointProbability').textContent=percent(f.probability);$('pointBaseline').textContent=percent(f.baseline);$('pointSkill').textContent=`${signed(f.skill*100,1)}%`;$('pointValidationYears').textContent=`Brier skill · ${f.nTest} test seasons`;
    $('climateNextTitle').textContent=`${monthLabel(f.seasonStart.slice(0,7))}–${monthLabel(f.seasonEnd.slice(0,7))} · ${percent(f.probability)} high-exposure probability`;
    $('climateNextDetail').textContent=`${coordinate(pixel)} · ${meta.products[product].name} · historical baseline ${percent(f.baseline)} · Brier skill ${signed(f.skill*100,1)}% (${f.nTest} test seasons) · ${f.leadMonths}-month lead`;
    if(state.mapMode==='probability'){$('recordMean').textContent=percent(f.baseline);$('pixelTrend').textContent=`${signed(f.skill*100,1)}%`;$('peakYear').textContent=f.nTest;}
  }
  async function renderOutlook(){
    const all=outlook.targets.filter(t=>t.available),latest=Object.values(liveClimate.latestByMode).sort().at(-1);
    $('freshness').textContent=`Annual history through 2025 · observations through 20 Oct 2026 · climate feeds to ${monthLabel(latest)} · IOD to ${monthLabel(liveClimate.latestByMode.IOD)}`;
    $('footerFreshness').textContent=`Climate checked ${liveClimate.asOf} · weekly refresh`;
    if(!all.length){$('outlookSubtitle').textContent='Waiting for the required recent climate observations.';$('outlookCards').innerHTML=`<div class="unavailable-outlook">${outlook.targets.map(t=>t.reason||'No dated outlook available.').join(' · ')}</div>`;return;}
    const first=all[0],start=new Date(first.seasonStart+'T00:00:00Z'),end=new Date(first.seasonEnd+'T00:00:00Z');
    const season=`${start.toLocaleDateString('en-GB',{month:'short',year:'numeric',timeZone:'UTC'})} – ${end.toLocaleDateString('en-GB',{month:'short',year:'numeric',timeZone:'UTC'})}`;
    $('outlookSubtitle').textContent=`${season} (${first.season}) · ${first.leadMonths}-month lead · ${state.outlookScope==='pixel'?'individual source-cell history':state.outlookScope==='overall'?'pooled habitat-cell means across the study domain':'habitat-cell means within each ecoregion'}`;
    $('outlookDates').replaceChildren(...[`Issue month: ${monthLabel(first.issueDate.slice(0,7))}`,`Indices used: ${monthLabel(first.predictorFirstMonth)}–${monthLabel(first.predictorLastMonth)}`,`Updated ${outlook.asOf}`,`MHW history: through 2025`].map(text=>{const e=document.createElement('span');e.textContent=text;return e;}));
    $('outlookDefinition').textContent=`Probability of a high-exposure season: ${state.outlookScope==='pixel'?'MHW days at this source cell':'habitat-cell mean MHW days'} above the training same-season 80th percentile, with a 10-day floor. ${state.outlookScope==='pixel'&&externalInfo(state.outlookRecord==='GHRSST MUR'?'mur':'oisst')?'The cell model tests an issued ENSO forecast alongside six observed indices.':'Six observed-index model.'} IOD forecasts are displayed separately.`;
    const rows=state.outlookScope==='pixel'?[await pointForecast(state.outlookRecord==='GHRSST MUR'?'mur':'oisst',state.pixel)]:all.filter(t=>t.product===state.outlookRecord&&t.scope===state.outlookScope&&(state.basin==='all'||t.basin===state.basin)&&(state.outlookScope==='overall'||state.region==='all'||t.region===meta.regions[Number(state.region)])&&(state.habitats&(1<<meta.habitats.indexOf(t.habitat)))).sort((a,b)=>meta.basins.findIndex(v=>v.id===a.basin)-meta.basins.findIndex(v=>v.id===b.basin)||meta.regions.indexOf(a.region)-meta.regions.indexOf(b.region)||meta.habitats.indexOf(a.habitat)-meta.habitats.indexOf(b.habitat));
    window.dispatchEvent(new CustomEvent('atlasoutlookchange',{detail:{rows}}));

  }
  function stop(){clearInterval(state.timer);state.timer=null;$('play').textContent='';$('play').setAttribute('aria-label','Play annual maps');}
  function forecastAvailability(){const enabled=!!outlook.pixelOutlooks[state.product];document.querySelector('#metric option[value="outlook_probability"]').disabled=!enabled;if(!enabled&&state.mapMode==='probability'){state.mapMode='history';$('metric').value=state.metric;}}
  async function createPointReport(){
    const button=$('createReport'),pixel=state.pixel,product=state.product,metric=state.metric,point=pixels[pixel],productInfo=meta.products[product];
    const association=modelData?.pixel===pixel&&modelData.product===product&&modelData.metric===metric?JSON.parse(JSON.stringify(modelData)):null;
    button.disabled=true;button.textContent='Preparing PDF…';
    try{
      const [arrays,forecast]=await Promise.all([Promise.all(meta.metrics.map(m=>array(product,m))),pointForecast(product,pixel)]);
      const histories=Object.fromEntries(meta.metrics.map((m,j)=>[m,series(pixel,arrays[j],product)]));
      let validation=[];let seasonal=[];
      if(forecast){const [predicted,observed,baseline,seasonArray]=await Promise.all(['backtest_predictions','backtest_observed','backtest_baselines'].map(name=>forecastArray(product,name)).concat([array(product,`season_${forecast.season}`)]));
        const seasonValues=series(pixel,seasonArray,product);seasonal=forecast.trainingYears.map(year=>({year,days:seasonValues[productInfo.years.indexOf(year)]}));
        validation=forecast.testYears.map((year,j)=>({year,probability:predicted[j*forecast.nativeCells+forecast.index],baseline:baseline[j*forecast.nativeCells+forecast.index],observedHigh:observed[j*forecast.nativeCells+forecast.index],days:seasonValues[productInfo.years.indexOf(year)],postBaseline:forecast.postBaselineMask[j]}));
      }
      if(forecast?.external&&forecast.trainingLastYear===2025){const season=seasonal.find(v=>v.year===2025);if(season)season.days=forecast.external.latest_season_days;const last=validation.find(v=>v.year===2025);if(last)last.days=forecast.external.latest_season_days;}
      const habitats=meta.habitats.filter((_,j)=>point[2]&(1<<j));
      const context=outlook.targets.filter(t=>t.available&&t.product===productInfo.name&&t.basin===pointBasin(point).id&&habitats.includes(t.habitat)&&(t.scope==='overall'||t.region===meta.regions[point[3]]));
      await window.AtlasReports.create({pixel:pixelId(pixel),latitude:point[1],longitude:point[0],habitats,region:meta.regions[point[3]],product:productInfo,
        source:productInfo.cells[sourceIndex(pixel,product)],distance:point[product==='mur'?6:7],metric,metricInfo:metricInfo[metric],histories,forecast,validation,seasonal,context,
        association,localSources:await window.AtlasResources?.forPoint(pixel),scenarios:window.AtlasScenarios?.compute(),detail:await window.AtlasDetails?.load(pixel,product),observed2026:await window.AtlasObserved2026?.forPoint(pixel,product),externalForecasts:await window.AtlasExternalForecasts?.data(),dailyClimate:await window.AtlasDetails?.climate(),updated:outlook.asOf,liveClimate,webUrl:`https://adawy2050.github.io/redsea-habitat-mhw-atlas/?lat=${point[1]}&lon=${point[0]}&product=${product}`});
      note('Point report downloaded.');
    }catch(error){console.error(error);note(`Report could not be created: ${error.message}`);}
    finally{button.disabled=false;button.textContent='Create point report (PDF) ';}
  }
  function exportMap(){
    const canvas=document.createElement('canvas'),w=$('map').clientWidth,h=$('map').clientHeight;
    canvas.width=w*2;canvas.height=h*2;const ctx=canvas.getContext('2d');ctx.scale(2,2);ctx.fillStyle=$('basemap').value==='satellite'?'#102f37':'#eaf0f4';ctx.fillRect(0,0,w,h);
    ctx.fillStyle='#24464a';ctx.strokeStyle='#51726d';ctx.lineWidth=.6;
    if($('basemap').value==='coastline')for(const feature of mapLand.features){const geometry=feature.geometry,polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
      for(const polygon of polygons){ctx.beginPath();for(const ring of polygon){ring.forEach((xy,i)=>{const p=map.latLngToContainerPoint([xy[1],xy[0]]);if(i===0)ctx.moveTo(p.x,p.y);else ctx.lineTo(p.x,p.y);});ctx.closePath();}ctx.fill('evenodd');ctx.stroke();}
    }
    const baseRect=$('map').getBoundingClientRect();ctx.globalAlpha=window.AtlasMapLayers?.state.satellite??1;for(const tile of $('map').querySelectorAll('img.leaflet-tile-loaded')){if(tile.complete&&tile.naturalWidth){const r=tile.getBoundingClientRect();ctx.drawImage(tile,r.x-baseRect.x,r.y-baseRect.y,r.width,r.height);}}
    ctx.globalAlpha=1;for(const name of ['shorelineOverview','shorelineDetailBackground','shorelineDetail']){const pane=map.getPane(name);if(!pane||getComputedStyle(pane).display==='none')continue;for(const c of pane.querySelectorAll('canvas')){const r=c.getBoundingClientRect();ctx.globalAlpha=Number(getComputedStyle(pane).opacity);ctx.drawImage(c,r.x-baseRect.x,r.y-baseRect.y,r.width,r.height);}}ctx.globalAlpha=1;
    ctx.drawImage(pixelLayer.canvas,0,0,w,h);
    const selected=map.latLngToContainerPoint([pixels[state.pixel][1],pixels[state.pixel][0]]);ctx.beginPath();ctx.arc(selected.x,selected.y,7,0,Math.PI*2);ctx.strokeStyle='#fff0b6';ctx.lineWidth=2;ctx.stroke();
    const forecast=outlook.pixelOutlooks[state.product],mapTitle=state.mapMode==='probability'?`Prediction probability · ${forecast.season} ${forecast.seasonStart.slice(0,4)}`:`${metricInfo[state.metric].name} · ${state.year}`;
    ctx.fillStyle='#102f37dd';ctx.fillRect(0,0,w,65);ctx.fillRect(0,h-70,w,70);ctx.fillStyle='#eeeade';ctx.font='15px system-ui';ctx.fillText(`${mapTitle} · ${meta.products[state.product].name}`,20,28);ctx.font='10px system-ui';ctx.fillText('COASTAL HABITAT HEATWAVE ATLAS · habitat cells only',20,47);
    const info=mapInfo();for(let i=0;i<140;i++){ctx.fillStyle=color(i/139*info.max,info.max);ctx.fillRect(20+i,h-42,1,6);}ctx.fillStyle='#ceded4';ctx.font='9px system-ui';ctx.fillText(`${info.axis}     0 — ${info.max}+`,20,h-50);ctx.fillText(state.mapMode==='probability'?`${forecast.leadMonths}-month lead · updated ${outlook.asOf} · ${meta.products[state.product].resolution} SST`:`Baseline ${meta.products[state.product].baseline} · ${meta.products[state.product].resolution} SST`,20,h-18);
    ctx.textAlign='right';ctx.fillText($('basemap').value!=='coastline'?'Imagery © Esri, Vantor, Earthstar Geographics, GIS User Community · GSHHG shoreline · UNEP-WCMC habitats':'GSHHG shoreline · UNEP-WCMC habitats · NASA/JPL · NOAA',w-20,h-18);
    canvas.toBlob(blob=>{if(!blob){note('Map image could not be generated.');return;}const a=document.createElement('a'),url=URL.createObjectURL(blob);a.href=url;a.download=`habitat_map_${state.product}_${state.year}.png`;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000);},'image/png');
  }
  async function yearChanged(){state.year=Number($('year').value);const product=state.product,metric=state.metric,year=state.year;if(year===2026&&state.mapMode==='history'){pixelLayer.currentArray=await mapValues(product,metric);if(product!==state.product||metric!==state.metric||year!==state.year)return;}pixelLayer.draw();window.dispatchEvent(new Event('atlasmapyearchange'));updateMapText();Plotly.relayout('historyPlot',{'shapes[0].x0':state.year,'shapes[0].x1':state.year}).catch(()=>{});}
  function bind() {
    window.addEventListener('atlaslanguagechange',()=>{renderHistory();renderModel();renderClimate();});
    $('product').onchange=()=>{stop();state.product=$('product').value;state.outlookRecord=meta.products[state.product].name;$('outlookRecord').value=state.outlookRecord;forecastAvailability();setYearControls();renderMap();renderClimate();renderOutlook();};
    $('metric').onchange=()=>{stop();if($('metric').value==='outlook_probability')state.mapMode='probability';else{state.mapMode='history';state.metric=$('metric').value;}renderMap();};
    $('basemap').onchange=()=>{if($('basemap').value!=='coastline'){map.removeLayer(landLayer);satelliteLayer.addTo(map);}else{map.removeLayer(satelliteLayer);landLayer.addTo(map);}};
    document.querySelectorAll('input[name="coverage"]').forEach(el=>el.onchange=()=>{el.checked?coverageLayers[el.value].addTo(map):map.removeLayer(coverageLayers[el.value]);});
    $('pixelOpacity').oninput=()=>{state.pixelOpacity=Number($('pixelOpacity').value);pixelLayer.draw();};$('showPixels').onchange=()=>{state.showPixels=$('showPixels').checked;pixelLayer.draw();};
    $('basin').onchange=()=>{state.selection=null;state.basin=$('basin').value;state.region='all';regionControls();filterChanged();fitStudy();const u=new URL(location.href);u.searchParams.set('basin',state.basin);history.replaceState(null,'',u);};
    $('region').onchange=()=>{state.region=$('region').value;filterChanged();};
    $('historySecondary').onchange=()=>{state.historySecondary=$('historySecondary').value;renderHistory();};
    $('showTrend').onchange=()=>{state.showTrend=$('showTrend').checked;renderHistory();};$('climateTrend').onchange=()=>{state.climateTrend=$('climateTrend').checked;renderClimate();};
    document.querySelectorAll('input[name="habitat"]').forEach(el=>el.onchange=()=>{state.habitats=[...document.querySelectorAll('input[name="habitat"]:checked')].reduce((s,e)=>s+Number(e.value),0);filterChanged();});
    $('year').oninput=yearChanged;
    $('play').onclick=()=>{if(state.timer){stop();return;}$('play').textContent='';$('play').setAttribute('aria-label','Pause annual maps');const p=meta.products[state.product];if(state.year===2026){$('year').value=p.years[0];yearChanged();}state.timer=setInterval(()=>{if(state.year>=2026){stop();return;}$('year').value=state.year+1;yearChanged();},750);};
    $('fitMap').onclick=fitStudy;
    $('pinPixel').onclick=()=>{if(state.pins.includes(state.pixel)){note('This cell is already in the comparison.');return;}if(state.pins.length>=5){note('Compare up to five pinned cells. Remove one to add another.');return;}state.pins.push(state.pixel);renderHistory();note('Cell added. Select another cell on the map to compare.');};
    $('clearPins').onclick=()=>{state.pins=[];renderHistory();};
    $('showLatestRecords').onclick=()=>{state.to=2026;$('toYear').value='2026';renderHistory();renderModel();window.dispatchEvent(new Event('atlasrangechange'));};
    $('fromYear').onchange=()=>{state.from=Number($('fromYear').value);if(state.from>state.to){state.to=state.from;$('toYear').value=state.to;}renderHistory();renderModel();renderClimate();window.dispatchEvent(new Event('atlasrangechange'));};
    $('toYear').onchange=()=>{state.to=Number($('toYear').value);if(state.to<state.from){state.from=state.to;$('fromYear').value=state.from;}renderHistory();renderModel();renderClimate();window.dispatchEvent(new Event('atlasrangechange'));};
    $('benchmark').onchange=()=>{state.benchmark=$('benchmark').value;renderModel();};$('lag').onchange=()=>{state.lag=Number($('lag').value);renderModel();};
    $('pairedIndex').onchange=()=>{state.index=$('pairedIndex').value;renderModel();};$('detrend').onchange=()=>{state.detrend=$('detrend').checked;renderModel();};
    $('climateStep').onchange=()=>{state.step=$('climateStep').value;renderClimate();};$('climateScale').onchange=()=>{state.scale=$('climateScale').value;renderClimate();};
    $('climateSource').onchange=()=>{state.climateSource=$('climateSource').value;state.climateTo=null;climateDateControls();renderClimate();};
    $('climateFrom').onchange=()=>{state.climateFrom=Number($('climateFrom').value);if(state.climateFrom>state.climateTo){state.climateTo=state.climateFrom;$('climateTo').value=state.climateTo;}renderClimate();};
    $('climateTo').onchange=()=>{state.climateTo=Number($('climateTo').value);if(state.climateTo<state.climateFrom){state.climateFrom=state.climateTo;$('climateFrom').value=state.climateFrom;}renderClimate();};
    $('climateThisYear').onclick=()=>{state.climateFrom=state.climateTo=Number(liveClimate.asOf.slice(0,4));state.step='monthly';$('climateStep').value='monthly';climateDateControls();renderClimate();};
    $('climateFullRecord').onclick=()=>{const dates=(state.climateSource==='latest'?liveClimate.monthly:climate.monthly).dates;state.climateFrom=Number(dates[0].slice(0,4));state.climateTo=Number(dates.at(-1).slice(0,4));climateDateControls();renderClimate();};
    $('outlookRecord').onchange=()=>{state.outlookRecord=$('outlookRecord').value;renderOutlook();};
    $('outlookScope').onchange=()=>{state.outlookScope=$('outlookScope').value;renderOutlook();};
    $('showPointOutlook').onclick=()=>{state.outlookScope='pixel';state.outlookRecord=meta.products[state.product].name;$('outlookScope').value='pixel';$('outlookRecord').value=state.outlookRecord;renderOutlook();$('outlook').scrollIntoView({behavior:'smooth'});};
    $('createReport').onclick=createPointReport;
    $('downloadOutlook').onclick=()=>download('seasonal_outlook.json',JSON.stringify({...outlook,externalCellModels:externalModels},null,2),'application/json');
    $('pairedIndex').replaceChildren(...[...climate.modes,'localSst'].map(m=>new Option(labels[m],m)));
    $('indexChips').replaceChildren(...climate.modes.map(m=>{const label=document.createElement('label');label.className='index-chip';const input=document.createElement('input');input.type='checkbox';input.checked=state.selectedModes.has(m);input.value=m;input.onchange=()=>{input.checked?state.selectedModes.add(m):state.selectedModes.delete(m);renderClimate();};const dot=document.createElement('i');dot.style.background=modeColors[m];label.append(input,dot,document.createTextNode(labels[m]));return label;}));
    for(const id of ['methodsOpen','methodsFooter','modelHelp'])$(id).onclick=showMethods;
    $('methodsClose').onclick=()=>$('methodsDialog').close();$('methodsDialog').onclick=e=>{if(e.target===$('methodsDialog'))$('methodsDialog').close();};
    $('locateForm').onsubmit=e=>{e.preventDefault();const parts=$('locate').value.trim().split(/[,\s]+/).map(Number);if(parts.length!==2||!parts.every(Number.isFinite)||parts[0]<-90||parts[0]>90||parts[1]<-180||parts[1]>180){$('locateMessage').textContent='Enter latitude, longitude; for example 21.5, 39.1';return;}const i=nearest(parts[0],parts[1],true);if(i<0){$('locateMessage').textContent='Select at least one habitat first.';return;}const d=Math.hypot(pixels[i][1]-parts[0],(pixels[i][0]-parts[1])*Math.cos(parts[0]*Math.PI/180))*111;$('locateMessage').textContent=`Nearest retained habitat cell: about ${number(d,1)} km away`;selectPixel(i,true);};
    $('downloadHistory').onclick=()=>download(`habitat_history_${state.product}_${state.metric}.csv`,csv(currentHistory));
    $('downloadClimate').onclick=()=>download(`climate_indices_${state.step}_${state.climateFrom}_${state.climateTo}.csv`,csv(climateExport));
    $('downloadPixel').onclick=async()=>{const pixel=state.pixel,product=state.product,p=meta.products[product],arrays=await Promise.all(meta.metrics.map(m=>array(product,m))),sst=await array('oisst','sst'),ss=series(pixel,sst,'oisst');
      const rows=p.years.map((year,j)=>{const row={pixel:pixelId(pixel),latitude:pixels[pixel][1],longitude:pixels[pixel][0],product:p.name,baseline:p.baseline,year,source_latitude:p.cells[sourceIndex(pixel,product)][1],source_longitude:p.cells[sourceIndex(pixel,product)][0]};meta.metrics.forEach((m,k)=>{row[m]=series(pixel,arrays[k],product)[j];});row.oisst_annual_mean_sst=ss[meta.products.oisst.years.indexOf(year)];climate.modes.forEach(m=>{row[m]=climate.annual.values[m][climate.annual.years.indexOf(year)];});return row;});download(`${pixelId(pixel)}_${product}.csv`,csv(rows));};
    $('downloadModel').onclick=()=>{if(!modelData){note('Select a longer period to fit the model.');return;}const d=modelData;download(`pixel_model_${pixelId(state.pixel)}.csv`,csv(d.rows.map((row,k)=>{const out={pixel:pixelId(state.pixel),latitude:pixels[state.pixel][1],longitude:pixels[state.pixel][0],year:row.year,observed:row.observed,fitted:d.model.pred[k],reference_only_fit:d.base.pred[k],reference:state.benchmark,reference_value:row.reference,oisst_annual_mean_sst:row.sst,index_lead_years:state.lag,climate_year:row.year-state.lag,product:meta.products[d.product].name,metric:d.metric,r2:d.model.r2,leave_one_year_out_r2:d.model.cvR2};climate.modes.forEach((m,j)=>{out[m]=row.indices[j];});d.names.forEach((name,j)=>{out[`${name}_share_r2`]=d.model.shares[j];out[`${name}_coefficient_per_sd`]=d.model.beta[j];out[`${name}_predictor_mean`]=d.model.means[j];out[`${name}_predictor_sd`]=d.model.scales[j];});return out;})));};
    $('mapDownload').onclick=exportMap;
  }
  function nearest(lat,lon,onlyVisible=false){let best=-1,distance=Infinity;for(let i=0;i<pixels.length;i++){const p=pixels[i];if(onlyVisible&&!visible(p))continue;const d=(p[1]-lat)**2+((p[0]-lon)*Math.cos(lat*Math.PI/180))**2;if(d<distance){distance=d;best=i;}}return best;}
  function filterChanged(){pixelLayer.draw();renderOutlook();if(!visible(pixels[state.pixel])){const index=pixels.findIndex(visible);if(index>=0)selectPixel(index);else note('Select at least one habitat to display cells.');}if(state.region!=='all'){const pts=pixels.filter(visible);if(pts.length)map.fitBounds(L.latLngBounds(pts.map(p=>[p[1],p[0]])),{padding:[70,65]});}}
  async function init(){
    try{[meta,climate]=await Promise.all([json('./data/metadata.json'),json('./data/climate.json')]);const [points,land,coverage,latest,seasonal,issued]=await Promise.all([json('./data/pixels.json'),json('./data/land.geojson'),json('./coverage/index.json'),json('./data/climate_latest.json'),json('./data/outlook.json'),json('./forecasts/cell_models.json').catch(()=>null)]);pixels=points.rows;coverageMeta=coverage;liveClimate=latest;outlook=seasonal;externalModels=issued;
      climateZ=Object.fromEntries(climate.modes.map(m=>[m,S.standardize(climate.annual.values[m].filter((_,i)=>climate.annual.years[i]>=1982))]));
      const params=new URLSearchParams(location.search);if(['mur','oisst'].includes(params.get('product')))state.product=params.get('product');$('product').value=state.product;if(params.get('variable')==='outlook_probability'){state.mapMode='probability';$('metric').value='outlook_probability';}else if(meta.metrics.includes(params.get('variable'))){state.metric=params.get('variable');$('metric').value=state.metric;}
      if(meta.basins.some(b=>b.id===params.get('basin')))state.basin=params.get('basin');$('basin').value=state.basin;regionControls();
      state.pixel=params.has('lat')&&params.has('lon')?nearest(Number(params.get('lat')),Number(params.get('lon')),true):nearest(21.4,39.05,true);
      if(!visible(pixels[state.pixel]))state.pixel=pixels.findIndex(visible);
      state.outlookRecord=meta.products[state.product].name;$('outlookRecord').value=state.outlookRecord;forecastAvailability();makeMap(land);setYearControls();bind();$('climateSource').value='latest';$('climateStep').value='monthly';climateDateControls();renderLatestIndices();await renderMap();renderClimate();renderOutlook();document.documentElement.dataset.ready='true';window.dispatchEvent(new Event('atlasready'));
    }catch(e){console.error(e);$('loadingText').textContent=`Atlas could not open: ${e.message}. Please reload.`;document.documentElement.dataset.error=e.message;}
  }
  window.AtlasUI={
    snapshot(){return {state:{...state},meta,pixels,climate,liveClimate,outlook,model:modelData,point:pixels[state.pixel],sourceIndex:sourceIndex(state.pixel),oisstIndex:sourceIndex(state.pixel,'oisst')};},
    mapValues,array:(p,m)=>m.startsWith('outlook_')?forecastArray(p,m.slice(8)):array(p,m),series,nearest,selectPixel,visible,mapInfo,pixelId,color,forecast:pointForecast,
    get map(){return map;},get fallbackLand(){return landLayer;},get satellite(){return satelliteLayer;},
    setOutlookInputs(value){outlookInputs=value;renderMap();renderOutlook();window.dispatchEvent(new Event('atlasforecastinputschange'));},
    hasIssuedForecast:product=>!!externalInfo(product,true),
    setYear(year){if(year===state.year||![...meta.products[state.product].years,2026].includes(year)||state.mapMode==='probability')return;$('year').value=year;yearChanged();},
    setRange(from,to){const first=Math.max(meta.products[state.product].years[0],Math.floor(from)),last=Math.min(2026,Math.floor(to));if(!Number.isFinite(first)||!Number.isFinite(last)||first>last)return;state.from=first;state.to=last;$('fromYear').value=state.from;$('toYear').value=state.to;renderHistory();renderModel();window.dispatchEvent(new Event('atlasrangechange'));},
    redraw(){pixelLayer.draw();},
    selectBounds(bounds){state.selection=bounds?[bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth()]:null;if(bounds){const centre=bounds.getCenter(),i=nearest(centre.lat,centre.lng,true);if(i>=0)selectPixel(i);}filterChanged();window.dispatchEvent(new Event('atlasselectionchange'));},
    async visit(step){
      state.basin=step.basin;state.region='all';state.habitats=15;state.selection=null;state.product='mur';state.metric='mhw_days';state.mapMode=step.forecast?'probability':'history';
      $('basin').value=state.basin;$('product').value=state.product;$('metric').value=step.forecast?'outlook_probability':state.metric;document.querySelectorAll('input[name="habitat"]').forEach(e=>e.checked=true);regionControls();setYearControls();state.year=2025;$('year').value=state.year;
      const i=nearest(step.lat,step.lon,true);state.pixel=i;await renderMap();selectPixel(i);const point=pixels[i];map.flyTo([point[1],point[0]],8,{animate:!matchMedia('(prefers-reduced-motion: reduce)').matches,duration:.8});
      if(step.forecast){state.outlookScope='pixel';$('outlookScope').value='pixel';await renderOutlook();const f=await pointForecast(state.product,i);return {en:`At ${coordinate(i)}, the ${f.season} high-exposure probability is ${percent(f.probability)}, compared with a historical ${percent(f.baseline)}. Brier skill: ${number(f.skill,2)}; ${f.nTest} test seasons.`,ar:`عند ${coordinate(i)}، احتمال ارتفاع التعرض في ${f.season} هو ${percent(f.probability)}، مقابل احتمال تاريخي ${percent(f.baseline)}. مهارة براير ${number(f.skill,2)} خلال ${f.nTest} مواسم تحقق.`};}
      const a=await array('mur','mhw_days'),v=series(i,a),years=meta.products.mur.years,trend=S.trend(years,v);return {en:`This ${meta.regions[point[3]]} cell recorded ${number(v[0],0)} heatwave days in ${years[0]} and ${number(v.at(-1),0)} in ${years.at(-1)}. Its full-record linear change is ${signed(trend,1)} days per decade.`,ar:`سجلت هذه الخلية ${number(v[0],0)} يومًا من الموجات الحارة في ${years[0]} و${number(v.at(-1),0)} يومًا في ${years.at(-1)}. التغير الخطي خلال السجل ${signed(trend,1)} يوم لكل عقد.`};
    }
  };
  window.AtlasDebug={state,get meta(){return meta;},get pixels(){return pixels;},get model(){return modelData;},get outlook(){return outlook;},get map(){return map;},get fallbackLand(){return landLayer;},get satellite(){return satelliteLayer;}};
  init();
})();
