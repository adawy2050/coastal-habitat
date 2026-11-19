/* Shoreline and imagery opacity can be adjusted independently. */
(() => {
  const $=id=>document.getElementById(id),T=s=>AtlasLanguage.translate(s),params=new URLSearchParams(location.search),state={satellite:Math.max(0,Math.min(1,+(params.get('satellite_opacity')??1))),shoreline:Math.max(0,Math.min(1,+(params.get('shoreline_opacity')??.45)))};
  AtlasLanguage.add({'Satellite + shoreline':'صور الأقمار الصناعية مع خط الساحل','Satellite opacity':'عتامة صور الأقمار الصناعية','Shoreline opacity':'عتامة خط الساحل','Layer opacity':'عتامة الطبقات'});
  const controls=document.createElement('div');controls.className='map-transparency';controls.setAttribute('aria-label','Layer opacity');controls.innerHTML='<span>Layer opacity</span><label>Satellite opacity<output id="satelliteOpacityValue"></output><input id="satelliteOpacity" type="range" min="0" max="1" step="0.05" aria-label="Satellite opacity"></label><label>Shoreline opacity<output id="shorelineOpacityValue"></output><input id="shorelineOpacity" type="range" min="0" max="1" step="0.05" aria-label="Shoreline opacity"></label>';document.querySelector('.map-card').append(controls);
  function apply(){if(document.documentElement.dataset.ready!=='true')return;AtlasUI.satellite?.setOpacity(state.satellite);const map=AtlasUI.map,mode=$('basemap').value;for(const pane of ['shorelineOverview','shorelineDetail','shorelineDetailBackground'])if(map.getPane(pane))map.getPane(pane).style.opacity=mode==='coastline'?String(state.shoreline):String(state.shoreline);
    $('satelliteOpacityValue').textContent=Math.round(state.satellite*100)+'%';$('shorelineOpacityValue').textContent=Math.round(state.shoreline*100)+'%';$('satelliteOpacity').disabled=mode==='coastline';$('shorelineOpacity').disabled=mode==='satellite';
  }
  for(const key of ['satellite','shoreline']){const input=$(key+'Opacity');input.value=state[key];input.oninput=()=>{state[key]=+input.value;apply();};input.onchange=()=>{const url=new URL(location.href);url.searchParams.set(key+'_opacity',state[key]);history.replaceState(null,'',url);};}
  $('basemap').addEventListener('change',apply);window.addEventListener('atlasready',apply);window.addEventListener('atlasshorelineready',apply);
  window.AtlasMapLayers={get state(){return {...state,mode:$('basemap').value};}};
})();
