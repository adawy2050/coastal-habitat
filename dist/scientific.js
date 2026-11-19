/* Habitat figures share region colours; future segments show one seasonal probability. */
(() => {
  const $=id=>document.getElementById(id),T=s=>AtlasLanguage.translate(s);
  AtlasLanguage.add({'Right axis':'المحور الأيمن','None':'بدون','Save SVG':'حفظ SVG','Each square is one month. Hover for the day count.':'يمثل كل مربع شهراً واحداً. مرّر المؤشر لعرض عدد الأيام.','Solid lines: past tests. Dotted lines: next season. Each future segment is one probability for the whole season.':'الخطوط المتصلة: التحقق السابق. المنقطة: الموسم القادم. يمثل كل مقطع مستقبلي احتمالاً واحداً للموسم كله.','Click a region to hide or show its line':'اضغط على الإقليم لإخفاء خطه أو إظهاره'});
  const palette=['#355c7d','#8b5a46','#57755b','#78658a','#9b813e','#4c8183','#956477','#646b73','#a16f32','#6c789d','#85934c','#995454'];
  let rows=[],token=0,busy=false,pending=false;const figures=new Map();
  const old=$('outlookTimeline').closest('.chart-card');old.hidden=true;old.style.display='none';
  document.querySelector('#outlook .outlook-note').textContent='Solid lines: past tests. Dotted lines: next season. Each future segment is one probability for the whole season.';
  async function draw(){
    const ticket=token,d=AtlasUI.snapshot(),host=$('outlookCards');
    host.className='habitat-outlook-figures';
    for(const figure of figures.values())figure.hidden=true;
    let empty=host.querySelector('.empty-season');if(!empty){empty=document.createElement('p');empty.className='empty-season detail-note';host.append(empty);}empty.textContent=T('Select a habitat to show its seasonal curves.');empty.hidden=rows.length>0;
    const groups=new Map();for(const row of rows.filter(Boolean)){if(!groups.has(row.habitat))groups.set(row.habitat,[]);groups.get(row.habitat).push(row);}
    const regions=[...new Set(d.outlook.targets.filter(t=>t.available).map(t=>t.region))].sort();
    let letter=0;
    for(const [habitat,items] of groups){
      let figure=figures.get(habitat);if(!figure){figure=document.createElement('figure');figure.className='habitat-outlook-figure';figures.set(habitat,figure);host.append(figure);}figure.hidden=false;
      const caption=document.createElement('figcaption'),title=document.createElement('h3'),save=document.createElement('button');
      title.textContent=`${String.fromCharCode(97+letter++)}. ${T(({coral:'Coral reefs',seagrass:'Seagrass',mangrove:'Mangroves',kelp_macroalgae:'Kelp & seaweeds'})[habitat]||habitat)}`;
      save.className='text-button';save.textContent=T('Save SVG');save.type='button';caption.append(title,save);
      let plot=figure.querySelector('.habitat-outlook-plot');if(!plot){plot=document.createElement('div');plot.className='habitat-outlook-plot';}
      const key=document.createElement('div');key.className='region-line-key';key.setAttribute('aria-label',T('Ecoregion'));
      figure.querySelector('figcaption')?.remove();figure.querySelector('.region-line-key')?.remove();figure.prepend(caption);figure.append(plot,key);
      const traces=[];
      for(const row of items){
        let predictions=row.backtest.predictions;
        if(row.scope==='pixel'){
          const pred=await AtlasUI.array(row.product,'outlook_backtest_predictions');if(ticket!==token)return;
          predictions=row.testYears.map((year,k)=>({year,probability:pred[k*row.nativeCells+row.index]}));
        }
        const ri=Math.max(0,regions.indexOf(row.region)),color=palette[ri%palette.length],dash=ri>=palette.length?'dash':'solid';
        // The saved target year is the season-start year, including December for DJF.
        const dateForYear=year=>`${year}-${row.seasonStart.slice(5)}`;
        const group=`${habitat}:${row.region}`,indices=[traces.length,traces.length+1];
        traces.push({x:predictions.map(p=>dateForYear(p.year)),y:predictions.map(p=>p.probability*100),type:'scatter',mode:'lines+markers',name:T(row.region),legendgroup:group,showlegend:false,line:{color,width:1.4,dash},marker:{size:3},hovertemplate:'%{x|%Y-%m}: %{y:.1f}%<extra>'+T(row.region)+'</extra>'});
        traces.push({x:[row.seasonStart,row.seasonEnd],y:[row.probability*100,row.probability*100],type:'scatter',mode:'lines+markers',name:T(row.region)+' · '+T('Next-season estimate'),legendgroup:group,showlegend:false,line:{color,width:2.2,dash:'dot'},marker:{size:4},hovertemplate:'%{y:.1f}%<extra>'+T(row.region)+' · '+row.season+'</extra>'});
        const button=document.createElement('button');button.type='button';button.className='region-line-toggle';button.setAttribute('aria-pressed','true');
        const swatch=document.createElement('span');swatch.className='line-swatch';swatch.style.borderColor=color;swatch.style.borderTopStyle=ri>=palette.length?'dashed':'solid';
        const name=document.createElement('span');name.textContent=T(row.region);const value=document.createElement('span');value.className='region-probability';value.textContent=(row.probability*100).toFixed(1)+'%';
        button.append(swatch,name,value);button.title=T('Click a region to hide or show its line');
        button.onclick=()=>{const visible=button.getAttribute('aria-pressed')!=='true';button.setAttribute('aria-pressed',String(visible));Plotly.restyle(plot,{visible},indices);};key.append(button);
      }
      const first=items[0],dark=document.documentElement.dataset.theme==='dark',fg=dark?'#d6dee4':'#3b4650',grid=dark?'#334550':'#e5e8ea';
      await Plotly.react(plot,traces,{paper_bgcolor:'transparent',plot_bgcolor:'transparent',margin:{l:65,r:22,t:24,b:46},font:{family:'Arial, sans-serif',size:11,color:fg},hovermode:'closest',xaxis:{type:'date',tickformat:'%Y',showgrid:false,showline:true,linecolor:grid,zeroline:false},yaxis:{title:T('Probability (%)'),range:[0,100],dtick:20,gridcolor:grid,zeroline:false,showline:true,linecolor:grid},shapes:[{type:'rect',xref:'x',yref:'paper',x0:first.seasonStart,x1:first.seasonEnd,y0:0,y1:1,fillcolor:dark?'#ffffff0a':'#00000005',line:{width:0}}]},{responsive:true,displaylogo:false,toImageButtonOptions:{format:'svg',filename:`seasonal_${habitat}`}});
      if(ticket!==token)return;
      // SVG downloads include the region key inside the exported figure.
      save.onclick=async()=>{await Plotly.relayout(plot,{showlegend:true,legend:{orientation:'h',y:-.2,font:{size:10}},margin:{l:65,r:22,t:24,b:150}});await Plotly.restyle(plot,{showlegend:true},traces.map((_,i)=>i).filter(i=>i%2===0));try{await Plotly.downloadImage(plot,{format:'svg',filename:`seasonal_${habitat}`,width:1200,height:650});}finally{await Plotly.restyle(plot,{showlegend:false});await Plotly.relayout(plot,{showlegend:false,margin:{l:65,r:22,t:24,b:46}});}};
    }
  }
  async function schedule(){pending=true;token++;if(busy)return;busy=true;try{while(pending){pending=false;await draw();}}catch(error){console.error(error);}finally{busy=false;}}
  window.addEventListener('atlasoutlookchange',event=>{rows=event.detail.rows;schedule();});
  window.addEventListener('atlaslanguagechange',schedule);
})();
