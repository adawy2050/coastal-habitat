/* Native GSHHG vertices load only when the coastline is inspected closely. */
(() => {
  let manifest,map,overview,serial=0;const cache=new Map(),active=new Map();
  const $=id=>document.getElementById(id);
  function group(data,pane){const sorted=[...data.features].sort((a,b)=>(a.properties.kind==='coast'?9:a.properties.level)-(b.properties.kind==='coast'?9:b.properties.level));return L.geoJSON({type:'FeatureCollection',features:sorted},{pane,interactive:false,smoothFactor:0,style:feature=>feature.properties.kind==='coast'?{color:'#647581',weight:.7,opacity:1,fill:false}:{stroke:pane==='shorelineOverview',color:'#647581',weight:.5,fill:true,fillColor:feature.properties.kind==='water'?'#eaf0f4':'#d7dde0',fillOpacity:1}});}
  async function redraw(){if(!manifest)return;const stamp=++serial,enabled=$('basemap').value!=='satellite';document.querySelector('.map-card').classList.toggle('shoreline-map',enabled);if(AtlasUI.fallbackLand)map.removeLayer(AtlasUI.fallbackLand);if(map.getPane('shorelineDetailBackground'))map.getPane('shorelineDetailBackground').style.display=$('basemap').value==='blend'?'none':'';
    if(!enabled){if(overview)map.removeLayer(overview);for(const layer of active.values())map.removeLayer(layer);return;}
    const detailed=map.getZoom()>=manifest.detailMinZoom,bounds=map.getBounds().pad(.1);
    if(!detailed){for(const layer of active.values())map.removeLayer(layer);overview?.addTo(map);return;}
    const needed=manifest.tiles.filter(t=>bounds.intersects(L.latLngBounds([t.bounds[1],t.bounds[0]],[t.bounds[3],t.bounds[2]]))),keys=new Set(needed.map(t=>t.path));
    for(const [key,layer] of active)if(!keys.has(key))map.removeLayer(layer);
    // Each tile has its own ocean background, preventing coarse land underneath.
    overview?.addTo(map);
    await Promise.all(needed.map(async tile=>{if(!cache.has(tile.path))cache.set(tile.path,fetch('./coastline/'+tile.path).then(r=>{if(!r.ok)throw Error('Shoreline tile unavailable');return r.json();}).catch(error=>{cache.delete(tile.path);throw error;}));try{const data=await cache.get(tile.path);if(stamp!==serial)return;let layer=active.get(tile.path);if(!layer){const b=tile.bounds,fill=L.rectangle([[b[1],b[0]],[b[3],b[2]]],{pane:'shorelineDetailBackground',interactive:false,stroke:false,fillColor:'#eaf0f4',fillOpacity:1});layer=L.layerGroup([fill,group(data,'shorelineDetail')]);active.set(tile.path,layer);}layer.addTo(map);}catch(error){console.warn(error.message);}}));
    if(stamp===serial&&needed.length&&needed.every(t=>active.get(t.path)&&map.hasLayer(active.get(t.path))))overview&&map.removeLayer(overview);
  }
  window.addEventListener('atlasready',async()=>{map=AtlasUI.map;map.createPane('shorelineOverview');map.getPane('shorelineOverview').style.zIndex=250;map.createPane('shorelineDetailBackground');map.getPane('shorelineDetailBackground').style.zIndex=255;map.createPane('shorelineDetail');map.getPane('shorelineDetail').style.zIndex=260;
    try{const r=await fetch('./coastline/index.json');if(!r.ok)return;manifest=await r.json();manifest.detailMinZoom??=8;const d=await fetch('./coastline/'+manifest.overview.path).then(r=>r.json());overview=group(d,'shorelineOverview');map.on('moveend zoomend',redraw);$('basemap').addEventListener('change',redraw);map.attributionControl.addAttribution(manifest.attributionHtml);redraw();}catch(error){console.warn('Detailed shoreline:',error.message);}
  });
})();
