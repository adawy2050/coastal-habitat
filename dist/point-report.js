/* Fully browser-local point reports. No coordinates/data are sent to a server. */
(() => {
  const ascii=s=>String(s).replace(/[–—−]/g,'-').replace(/°/g,' deg').replace(/σ/g,'SD');
  const num=(v,d=1)=>v===null||!Number.isFinite(v)?'-':Number(v).toFixed(d);
  const pct=v=>`${num(v*100,1)}%`;
  let dependencies;
  async function loadDependencies(){if(window.jspdf?.jsPDF?.API?.autoTable)return;if(!dependencies)dependencies=(async()=>{for(const path of ['./vendor/jspdf.umd.min.js','./vendor/jspdf-autotable.min.js'])await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=new URL(path,document.baseURI).href;script.onload=resolve;script.onerror=()=>reject(Error('PDF dependency unavailable'));document.head.append(script);});})().catch(e=>{dependencies=null;throw e;});return dependencies;}
  async function create(r){
    window.AtlasReportRendering=true;
    try{
    await loadDependencies();
    const {jsPDF}=window.jspdf,doc=new jsPDF({orientation:'portrait',unit:'mm',format:'a4',compress:true});
    const ink=[23,33,46],blue=[23,79,134],grey=[85,101,117],W=180,X=15;
    const title=(name,sub)=>{doc.setFont('helvetica','normal');doc.setFontSize(6.5);doc.setTextColor(...grey);doc.text('RESEARCH PREVIEW - UNDER TESTING',195,10,{align:'right'});doc.setFont('helvetica','bold');doc.setFontSize(17);doc.setTextColor(...ink);doc.text(ascii(name),X,21);doc.setFont('helvetica','normal');doc.setFontSize(8);doc.setTextColor(...grey);doc.text(doc.splitTextToSize(ascii(sub),W),X,28);};
    const heading=(name,y)=>{doc.setFont('helvetica','bold');doc.setFontSize(11);doc.setTextColor(...ink);doc.text(ascii(name),X,y);doc.setFont('helvetica','normal');return y+7;};
    const para=(text,y,size=8.5)=>{doc.setFontSize(size);doc.setTextColor(...grey);const lines=doc.splitTextToSize(ascii(text),W);doc.text(lines,X,y);return y+lines.length*(size*.42)+4;};
    const table=(head,body,y,extra={})=>{doc.autoTable({head:[head.map(ascii)],body:body.map(row=>row.map(ascii)),startY:y,margin:{left:X,right:X,bottom:19},theme:'striped',styles:{fontSize:8,cellPadding:2,overflow:'linebreak',textColor:ink},headStyles:{fillColor:blue,textColor:255,fontStyle:'bold'},alternateRowStyles:{fillColor:[243,246,249]},...extra});return doc.lastAutoTable.finalY+8;};
    const coordinate=`${r.latitude.toFixed(2)} N, ${r.longitude.toFixed(2)} E`;
    title('Habitat marine heatwave point report',`${coordinate} | ${r.product.name} | Generated ${new Date().toISOString().slice(0,10)}`);
    let y=43;
    y=table(['Location and sampling','Value'],[
      ['Habitat grid cell',r.pixel],['Mapped habitat(s)',r.habitats.join(', ')],['Ecoregion',r.region],
      ['Observed record',`${r.product.years[0]}-${r.product.years.at(-1)} | ${r.product.resolution} SST | baseline ${r.product.baseline}`],
      ['Sampled SST centre',`${r.source[1].toFixed(3)} N, ${r.source[0].toFixed(3)} E (${num(r.distance,2)} km from habitat centre)`]
    ],y,{columnStyles:{0:{cellWidth:46}},styles:{fontSize:8,cellPadding:1.8}});
    y=heading('Upcoming-season outlook at this point',y);
    if(r.forecast){const f=r.forecast;y=table(['Season','Point probability','Historical baseline','Brier skill','Test seasons'],[
      [`${f.season} ${f.seasonStart.slice(0,4)}`,pct(f.probability),pct(f.baseline),pct(f.skill),String(f.nTest)]
    ],y);
      y=para(`Season: ${f.seasonStart} to ${f.seasonEnd}. High exposure: more than ${num(f.threshold,1)} MHW days at this source cell. Training: ${f.trainingYears[0]}-${f.trainingYears.at(-1)} (${f.trainingYears.length} seasons). ${f.leadMonths}-month lead; estimate updated ${r.updated}.`,y);
      y=para('This model uses the point history itself. Brier skill is relative to a historical-probability baseline; negative values indicate worse held-out performance. Probabilities are research estimates, not operational alert levels.',y,8);
    }else y=para('A current seasonal estimate is waiting for the required climate observations.',y);
    y=heading(`Annual ${r.metricInfo.name.toLowerCase()}`,y);
    const scratch=document.createElement('div');scratch.dataset.reportChart='true';scratch.style.cssText='position:fixed;left:-10000px;top:0;width:1100px;height:390px';document.body.append(scratch);
    let image;
    const traces=[{x:r.product.years,y:r.histories[r.metric],name:'Observed',mode:'lines+markers',type:'scatter',line:{color:'#1768ac',width:2},marker:{size:4}}];
    if(r.observed2026)traces.push(AtlasObserved2026.runningTrace(r.observed2026,r.metric));
    const valid=r.histories[r.metric].map((v,i)=>Number.isFinite(v)?i:-1).filter(i=>i>=0);
    if(valid.length>=3){const x=valid.map(i=>r.product.years[i]),fit=window.AtlasStats.fit(valid.map(i=>r.histories[r.metric][i]),[x]);traces.push({x,y:fit.pred,name:'Fitted linear trend',type:'scatter',mode:'lines',line:{color:'#34465b',width:2,dash:'dot'}});}
    try{await Plotly.newPlot(scratch,traces,
      {width:1100,height:390,paper_bgcolor:'#fff',plot_bgcolor:'#fff',margin:{l:75,r:25,t:35,b:55},legend:{orientation:'h',y:1.15},font:{family:'Arial',size:15,color:'#34465b'},xaxis:{tickformat:'d',gridcolor:'#e8edf3'},yaxis:{title:r.metricInfo.axis,gridcolor:'#e8edf3',zeroline:false}}, {staticPlot:true,displayModeBar:false});image=await Plotly.toImage(scratch,{format:'png',width:1100,height:390,scale:1.5});}
    finally{Plotly.purge(scratch);scratch.remove();}
    doc.addImage(image,'PNG',X,y,W,64);y+=70;
    doc.setFontSize(8);doc.setTextColor(...blue);doc.textWithLink('Open this point in the interactive atlas',X,Math.min(y,275),{url:r.webUrl});
    doc.addPage();title('Observed annual history',`${coordinate} | ${r.product.name} | MHW observations through ${r.product.years.at(-1)}`);
    y=table(['Year','MHW days','Events','Mean duration\n(days)','Mean intensity\n(degC)','Max intensity\n(degC)','Cumulative\n(degC days)'],r.product.years.map((year,j)=>[
      year,num(r.histories.mhw_days[j],0),num(r.histories.mhw_frequency[j],0),num(r.histories.mhw_mean_duration[j]),num(r.histories.mhw_mean_intensity[j],2),num(r.histories.mhw_max_intensity[j],2),num(r.histories.mhw_cumulative_intensity[j],1)
    ]),40,{styles:{fontSize:7.3,cellPadding:1},columnStyles:{0:{cellWidth:15}}});
    if(y<268)para('Intensity is temperature above the seasonal 90th-percentile threshold. A dash indicates no event intensity/duration. Cross-year event allocation follows the corrected manuscript pipeline.',y,8);
    doc.addPage();title('Seasonal validation and habitat context',`${coordinate} | ${r.product.name} | Chronological training-only predictions`);
    y=40;
    if(r.forecast){y=para(`Post-baseline validation: ${r.forecast.nTest} seasons; Brier score ${num(r.forecast.brier,4)} versus baseline ${num(r.forecast.baseline_brier,4)}. Full retrospective validation: ${r.forecast.nTestRetrospective} seasons, skill ${pct(r.forecast.skill_all)}.`,y);
      y=table(['Season start\nyear','MHW days','Observed high\n(1=yes)','Model\nprobability','Baseline\nprobability','SST baseline ready'],r.validation.map(v=>[v.year,num(v.days,0),num(v.observedHigh,0),pct(v.probability),pct(v.baseline),v.postBaseline?'Yes':'No']),y,{styles:{fontSize:7,cellPadding:1.5}});
    }
    if(y>225){doc.addPage();title('Habitat context and climate associations',`${coordinate} | ${r.product.name}`);y=42;}
    y=heading('Habitat-scale context',y);
    y=table(['Habitat','Scope','Probability','Baseline','Brier skill'],r.context.map(t=>[t.habitat,t.scope==='overall'?`${t.region} (whole habitat)`:t.region,pct(t.probability),pct(t.historicalProbability),pct(t.backtest.scores.baseline_available.skill)]),y,{styles:{fontSize:7,cellPadding:1.5}});
    if(r.association){
      if(y>202){doc.addPage();title('Annual climate associations',`${coordinate} | selected analysis period`);y=42;}
      const a=r.association;y=heading('Annual pixel model',y);y=para(`Analysis years ${a.rows[0].year}-${a.rows.at(-1).year}; outcome ${r.metricInfo.name.toLowerCase()}. Fitted R2: ${num(a.model.r2,3)}. Leave-one-year-out R2: ${num(a.model.cvR2,3)}. Shares below allocate full-record fitted variation; they are separate from the seasonal logistic probability model.`,y);
      y=table(['Predictor','Share of total variance','Coefficient per predictor SD'],a.names.map((name,j)=>[name,pct(a.model.shares[j]),num(a.model.beta[j],3)]),y,{styles:{fontSize:7,cellPadding:1.5}});
    }
    async function extraChart(traces,options={}){
      const el=document.createElement('div');el.dataset.reportChart='true';el.style.cssText='position:fixed;left:-10000px;top:0;width:1100px;height:400px';document.body.append(el);
      try{await Plotly.newPlot(el,traces,{width:1100,height:400,paper_bgcolor:'#fff',plot_bgcolor:'#fff',margin:{l:65,r:65,t:40,b:45},legend:{orientation:'h',y:1.15,font:{size:12}},font:{size:12,color:'#34465b'},...options},{staticPlot:true,displayModeBar:false});return await Plotly.toImage(el,{format:'png',width:1100,height:400,scale:1.4});}finally{Plotly.purge(el);el.remove();}
    }
    if(r.detail){
      doc.addPage();title('Daily temperature and monthly heatwave history',`${coordinate} | Daily OISST source ${r.detail.daily.cell[1]} N, ${r.detail.daily.cell[0]} E`);y=40;
      const cutoff=String(+r.detail.period[1].slice(0,4)-4),daily=r.detail.daily,keep=daily.dates.map((date,i)=>date>=cutoff?i:-1).filter(i=>i>=0),means=window.AtlasDetails.monthlyMeans(daily),mk=means.dates.map((date,i)=>date>=cutoff?i:-1).filter(i=>i>=0),monthly=r.detail.monthly,hk=monthly.dates.map((date,i)=>date>=cutoff?i:-1).filter(i=>i>=0);
      const dense=await extraChart([{x:keep.map(i=>daily.dates[i]),y:keep.map(i=>daily.values[i]),name:'Daily OISST',mode:'lines',line:{color:'rgba(36,94,136,.24)',width:.8}},{x:mk.map(i=>means.dates[i]),y:mk.map(i=>means.values[i]),name:'Monthly mean SST',mode:'lines',line:{color:'#245e88',width:2}},{x:hk.map(i=>monthly.dates[i]),y:hk.map(i=>monthly.values[i]),name:'Monthly MHW days',mode:'lines',yaxis:'y2',line:{color:'#b35b32',width:1.2}}],{xaxis:{type:'date'},yaxis:{title:'SST (degC)'},yaxis2:{title:'MHW days / month',overlaying:'y',side:'right',showgrid:false,rangemode:'tozero'}});
      doc.addImage(dense,'PNG',X,y,W,68);y+=74;y=para(`Daily observations: ${r.detail.period[0]} to ${r.detail.period[1]} (${daily.dates.length.toLocaleString('en')} dates). Figure shows the latest five years; all daily values can be downloaded from the atlas. Monthly MHW days use ${monthly.product} at the point's attached source cell.`,y,8);
      const last=monthly.dates.map((date,i)=>({date,i})).slice(-24);y=table(['Month','Observed mean SST (degC)','Observed MHW days'],last.map(d=>{const k=means.dates.indexOf(d.date);return [d.date.slice(0,7),num(means.values[k],2),num(monthly.values[d.i],0)];}),y,{styles:{fontSize:7,cellPadding:1.1}});
    }
    if(r.detail){
      doc.addPage();title('Heatwave calendar and next-season outlook',`${coordinate} | ${r.region} | ${r.product.name}`);y=40;
      const monthly=r.detail.monthly,years=[...r.product.years,...(r.detail.currentYear?[r.detail.currentYear]:[])],calendar=years.map(year=>Array.from({length:12},(_,m)=>{const key=`${year}-${String(m+1).padStart(2,'0')}`;const i=monthly.dates.findIndex(d=>d.startsWith(key));return i<0?null:monthly.values[i];}));
      const heat=await extraChart([{x:['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],y:years,z:calendar,type:'heatmap',colorscale:[[0,'#f3eee2'],[.5,'#4b737c'],[1,'#9f542e']],zmin:0,zmax:31,colorbar:{title:'Days',thickness:12}}],{xaxis:{type:'category',side:'top'},yaxis:{autorange:'reversed',tickformat:'d',dtick:years.length>30?4:2}});doc.addImage(heat,'PNG',X,y,W,85);y+=91;
      const days=r.histories.mhw_days.filter(Number.isFinite),mean=v=>v.reduce((a,b)=>a+b,0)/v.length;
      y=para(`Mean heatwave days per year: first five years ${num(mean(days.slice(0,5)),1)}; last five years ${num(mean(days.slice(-5)),1)}; difference ${num(mean(days.slice(-5))-mean(days.slice(0,5)),1)} days/year.`,y,9);
      if(r.forecast){const f=r.forecast,tests=r.validation||[],plot=await extraChart([{x:tests.map(v=>`${v.year}-${f.seasonStart.slice(5)}`),y:tests.map(v=>v.probability*100),name:'Past model tests',mode:'lines',line:{color:'#245e88',width:2}},{x:[f.seasonStart,f.seasonEnd],y:[f.probability*100,f.probability*100],name:'Next season',mode:'lines',line:{color:'#a45d36',width:3,dash:'dot'}},{x:[tests.length?`${tests[0].year}-01-01`:f.seasonStart,f.seasonEnd],y:[f.baseline*100,f.baseline*100],name:'Historical chance',mode:'lines',line:{color:'#92947f',dash:'dot'}}],{xaxis:{type:'date'},yaxis:{title:'Probability (%)',range:[0,100]}});doc.addImage(plot,'PNG',X,y,W,65);y+=72;y=para(`The dotted future line covers ${f.seasonStart} to ${f.seasonEnd}. It is one probability for the whole season.`,y,8);}
    }
    if(r.observed2026){
      const current=r.observed2026,index=current.index,v=current.values,cut=v.sst.map((x,i)=>x-v.intensity[i]);
      doc.addPage();title('Observed heatwaves: 2026 to date',`${coordinate} | ${current.product==='mur'?'GHRSST MUR':'NOAA OISST'} | through ${index.dateEnd}`);y=40;
      const image=await extraChart([{x:index.dates,y:v.sst,name:'Daily SST',mode:'lines',line:{color:'#355c7d',width:1.3}},{x:index.dates,y:cut,name:'90th-percentile threshold',mode:'lines',line:{color:'#777',dash:'dot',width:1.2}},{x:index.dates,y:v.sst.map((x,i)=>v.mhw[i]?x:null),name:'Heatwave days',mode:'markers',marker:{color:'#98614d',size:3}}],{xaxis:{type:'date',tickformat:'%b'},yaxis:{title:'SST (degC)'}});doc.addImage(image,'PNG',X,y,W,80);y+=88;
      y=para(`Observed heatwave days in 2026 through ${index.dateEnd}: ${v.mhw.reduce((a,b)=>a+b,0)}. SST source: ${current.source[1]} N, ${current.source[0]} E. Fixed baseline ${current.product==='mur'?'2003-2022':'1982-2011'}.`,y,9);
      if(current.metrics)y=table(['2026 to date','Value','Units'],current.metrics.map((v,i)=>[['Heatwave days','Event segments','Mean segment duration','Mean intensity above threshold','Maximum intensity above threshold','Cumulative intensity'][i],num(v,i<2?0:2),['days','segments','days','degC','degC','degC days'][i]]),y,{styles:{fontSize:7.5,cellPadding:1.5}});
      const rows=index.monthDates.map(month=>{const keep=index.dates.map((d,i)=>d.startsWith(month)?i:-1).filter(i=>i>=0),sst=keep.map(i=>v.sst[i]).filter(Number.isFinite);return [month,keep.reduce((sum,i)=>sum+v.mhw[i],0),num(sst.reduce((a,b)=>a+b,0)/sst.length,2)];});y=table(['Month','Observed MHW days','Mean SST (degC)'],rows,y,{styles:{fontSize:7.5,cellPadding:1.5}});
      y=para(`${index.source}. The latest month and year are incomplete. Event membership near the end of the record can change as further daily observations arrive. Complete-year annual models retain their original training records.`,y,8);
    }
    if(r.liveClimate){
      doc.addPage();title('Climate observations and conditional annual extension',`${coordinate} | Monthly feeds checked ${r.liveClimate.asOf}`);y=40;
      const monthly=r.liveClimate.monthly,start=String(+r.liveClimate.asOf.slice(0,4)-4),keep=monthly.dates.map((date,i)=>date>=start?i:-1).filter(i=>i>=0),colours=['#9b5844','#3b7772','#7b6b85','#4e708f','#958044','#9b6f7b','#73855c'];
      const ct=r.liveClimate.modes.map((m,j)=>({x:keep.map(i=>monthly.dates[i]),y:window.AtlasStats.standardize(keep.map(i=>monthly.values[m][i])),name:m,mode:'lines',line:{color:colours[j],width:1.4}}));
      if(r.dailyClimate)for(const mode of ['AO','NAO']){const source=r.dailyClimate.modes[mode],indices=source.dates.map((date,i)=>date>=start?i:-1).filter(i=>i>=0),raw=keep.map(i=>monthly.values[mode][i]).filter(Number.isFinite),mean=window.AtlasStats.mean(raw),sd=Math.sqrt(window.AtlasStats.mean(raw.map(v=>(v-mean)**2)));ct.push({x:indices.map(i=>source.dates[i]),y:indices.map(i=>(source.values[i]-mean)/(sd||1)),name:mode+' daily',mode:'lines',line:{color:mode==='AO'?'rgba(54,106,162,.20)':'rgba(126,82,160,.20)',width:.7}});}
      const cimage=await extraChart(ct,{xaxis:{type:'date'},yaxis:{title:'Standard deviations'}});doc.addImage(cimage,'PNG',X,y,W,68);y+=75;
      y=table(['Index','Latest monthly observation','Value','Current-year months'],r.liveClimate.modes.map(mode=>{let k=monthly.values[mode].length-1;while(k>=0&&!Number.isFinite(monthly.values[mode][k]))k--;return [mode,monthly.dates[k].slice(0,7),num(monthly.values[mode][k],3),monthly.values[mode].filter((v,i)=>monthly.dates[i].startsWith(r.liveClimate.asOf.slice(0,4))&&Number.isFinite(v)).length];}),y,{styles:{fontSize:7.5,cellPadding:1.5}});
      y=para('Faint daily AO/NAO are genuine NOAA daily products. The monthly record and original normalisations are retained; daily observations are display-only and do not replace the model predictors.',y,8);
      if(r.scenarios?.length){y=heading('Conditional annual model values',y);y=table(['Year','Conditional metric value','Climate input year'],r.scenarios.map(v=>[v.year,num(v.value,2),v.climateYear]),y);y=para('These dotted annual extensions are conditional scenarios, separate from the next-season probability model. Current-year index means use only available months; future indices and annual SST, when used, are held at their latest available values. They are not observed MHW values.',y,8);}
    }
    if(r.association){
      doc.addPage();title('Observed, fitted and conditional annual curves',`${coordinate} | ${r.product.name} | ${r.metricInfo.name}`);y=40;
      const a=r.association,ys=a.rows.map(v=>v.year),traces=[{x:ys,y:a.rows.map(v=>v.observed),name:'Observed',mode:'lines+markers',line:{color:'#245e88',width:2},marker:{size:4}},{x:ys,y:a.base.pred,name:a.names[0],mode:'lines',line:{color:'#90977d',dash:'dot',width:1.5}},{x:ys,y:a.model.pred,name:'Combined annual model',mode:'lines',line:{color:'#34465b',dash:'dot',width:2}}];
      if(r.observed2026)traces.push(AtlasObserved2026.runningTrace(r.observed2026,r.metric));
      if(r.scenarios?.length)traces.push({x:[ys.at(-1),...r.scenarios.map(v=>v.year)],y:[a.model.pred.at(-1),...r.scenarios.map(v=>v.value)],name:'Conditional annual extension',mode:'lines+markers',line:{color:'#b15b35',dash:'dot',width:2}});
      const plot=await extraChart(traces,{xaxis:{tickformat:'d'},yaxis:{title:r.metricInfo.unit}});doc.addImage(plot,'PNG',X,y,W,78);y+=85;
      y=para(`Solid: observations. Dotted 2026 observed curves: running values through ${r.observed2026?.index.dateEnd||'the latest observation'}. Other dotted lines: model fit, reference-only fit and conditional extension. The extension holds unavailable future predictors at their latest available values; it is separate from the seasonal exposure probability forecast.`,y,8);
      if(r.scenarios?.length)y=table(['Index','2026 input year','Available months','Mean index input'],r.scenarios[0].inputs.map(i=>[i.mode,i.year,i.months,num(i.value,3)]),y,{styles:{fontSize:7.5,cellPadding:1.6}});
    }
    if(y>190){doc.addPage();title('Sources, methods and contacts',coordinate);y=42;}
    y=heading('Sources and interpretation',y);
    y=para('SST: NASA/JPL GHRSST MUR v4.1 and NOAA OISST v2.1. Habitats: UNEP-WCMC inventories; East Asia also uses modelled seagrass grids and macroalgae occurrence records. Climate: NOAA CPC, PSL and NCEI. The observed-index reference uses Nino-3.4, NAO, AO, EAWR, North Atlantic SST anomaly and PDO. The IOD feed is delayed and is shown separately in the atlas.',y,8);
    y=para('High exposure exceeds the training same-season 80th percentile, with a 10-day floor. Every backtest refits using earlier seasons only, including thresholds, detrending, standardisation and regularisation. A source cell may be shared by several habitat locations. These results describe surface heatwave exposure, not species-specific damage.',y,8);
    y=heading('Contacts',y);y=para('Ahmed Eladawy, JAMSTEC: ahmed.eladawy@jamstec.go.jp',y,8);
    if(r.externalForecasts){
      const issued=r.externalForecasts;doc.addPage();title('Issued climate-index forecasts',`${coordinate} | Columbia/IRI issue ${issued.iri.issueMonth} | JAMSTEC source snapshot ${issued.retrieved.slice(0,10)}`);y=40;
      const traces=[];for(const [k,key] of ['Nino34','DMI'].entries()){const s=issued.jamstec[key];if(s.observedDates)traces.push({x:s.observedDates,y:s.observedValues,name:key+' observed',mode:'lines',line:{color:k?'#8b5a46':'#355c7d',width:1.5}});for(const member of s.members)traces.push({x:s.dates,y:member,name:key+' member',showlegend:false,hoverinfo:'skip',mode:'lines',line:{color:k?'rgba(139,90,70,.12)':'rgba(53,92,125,.12)',width:.6}});traces.push({x:s.dates,y:s.mean,name:'JAMSTEC '+key,mode:'lines',line:{color:k?'#8b5a46':'#355c7d',dash:'dot',width:2}});}
      const image=await extraChart(traces,{xaxis:{type:'date'},yaxis:{title:'Index anomaly (degC)'}});doc.addImage(image,'PNG',X,y,W,80);y+=87;
      y=table(['Month','JAMSTEC Nino3.4','JAMSTEC IOD'],issued.jamstec.Nino34.dates.map((date,i)=>[date.slice(0,7),num(issued.jamstec.Nino34.mean[i],3),num(issued.jamstec.DMI.mean[i],3)]),y,{styles:{fontSize:8,cellPadding:1.7}});
      y=para(`Columbia/IRI published combined-average DJF forecast: ${num(issued.iri.seasons.DJF,2)} degC. This is a three-month mean. JAMSTEC values are monthly anomalies against 1983-2015; faint lines show model members. Missing source values remain blank.`,y,8);
      if(r.forecast?.external){const f=r.forecast,a=f.external;y=para(`Cell outlook: ${pct(f.probability)}; observed-index reference: ${pct(a.reference_probability)}; issued-ENSO model weight: ${pct(a.selected_weight)}. ${f.nTest} earlier test seasons after baseline availability. All forecast-input and blend choices use earlier data. Eight test seasons and a lower past Brier score are required to add the forecast. IOD is displayed but is not yet a cell-model input.`,y,8);}
      y=para('Sources: https://forecast.ccsr.columbia.edu/forecasts/enso/plumes ; https://www.jamstec.go.jp/aplinfo/sintexf/e/seasonal/data_download.html',y,7);
    }
    if(r.localSources){
      const local=r.localSources;doc.addPage();title('Selected coast: photograph and sources',`${coordinate} | ${local.area} | Catalogue updated ${local.checked}`);y=42;
      const nearest=window.AtlasPhotos?.forPoint(r.latitude,r.longitude,1,local.basin,r.habitats.reduce((sum,h)=>sum+({coral:1,seagrass:2,mangrove:4,kelp_macroalgae:8}[h]||0),0))[0];
      if(nearest){
        try{const p=nearest.photo,img=new Image();img.src=AtlasPhotos.previewUrl(p,960);await img.decode();const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;canvas.getContext('2d').drawImage(img,0,0);const h=Math.min(76,W*img.naturalHeight/img.naturalWidth),w=h*img.naturalWidth/img.naturalHeight;doc.addImage(canvas.toDataURL('image/jpeg',.90),'JPEG',X+(W-w)/2,y,w,h);y+=h+6;y=para(`${p.location}; ${num(nearest.distance,0)} km from the selected habitat cell. Collection photograph, separate from the SST record. ${p.author}; ${p.license}.`,y,7);doc.setFontSize(7);doc.textWithLink('Photograph source and licence',X,y,{url:p.source});y+=10;}catch{y=para('The collection photograph could not be loaded; source links remain available below.',y,8);}
      }
      for(const [label,items] of [['News and research updates',local.news.slice(0,2)],['Papers for this area',local.papers.slice(0,2)]]){
        if(y>232){doc.addPage();title('Sources for the selected coast',coordinate);y=42;}
        y=heading(label,y);
        if(!items.length)y=para('No geographically matched items are in this catalogue yet.',y,8);
        for(const item of items){if(y>239){doc.addPage();title('Sources for the selected coast',coordinate);y=42;}y=para(item.title,y,8);y=para(`${item.source||item.journal} | ${item.date||item.published||item.year} | ${item.geography?.name||local.area}`,y,7);doc.setTextColor(...blue);doc.setFontSize(7);doc.textWithLink('Read at source',X,y,{url:item.url});y+=9;}
      }
      if(y<252){y=para('Source geography describes a study area, not a measurement at this habitat pixel.',y,7);doc.textWithLink('More sources for this point in the atlas',X,y,{url:r.webUrl});}
    }
    const pages=doc.getNumberOfPages();for(let page=1;page<=pages;page++){doc.setPage(page);doc.setDrawColor(215,222,230);doc.line(X,282,195,282);doc.setFont('helvetica','normal');doc.setFontSize(7);doc.setTextColor(...grey);doc.text('Coastal Habitat Heatwave Atlas | Ahmed Eladawy',X,287);doc.text(`${page} / ${pages}`,195,287,{align:'right'});doc.setFontSize(6.5);doc.text('Research preview - Under testing | Comments: ahmed.eladawy@jamstec.go.jp',X,292);}
    doc.setProperties({title:`MHW point report: ${coordinate}`,author:'Ahmed Eladawy',subject:'Habitat-cell history, seasonal probabilities and chronological validation'});
    doc.save(`MHW_${r.latitude.toFixed(2)}N_${r.longitude.toFixed(2)}E_${r.product.name.replaceAll(' ','_')}_report.pdf`);
    }finally{window.AtlasReportRendering=false;window.dispatchEvent(new Event('atlasreportcomplete'));}
  }
  window.AtlasReports={create};
})();
