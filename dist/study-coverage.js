/* Study bounds remain visible above every basemap and year, without filtering cells. */
(() => {
  'use strict';
  const T=s=>AtlasLanguage.translate(s),outlines=[],labels=[];
  AtlasLanguage.add({'East Asia':'شرق آسيا','Study coverage':'نطاق الدراسة','Dotted outline: study coverage':'الإطار المنقط: نطاق الدراسة','Mangrove (near)':'المانغروف (بالقرب)','Mangroves (near)':'المانغروف (بالقرب)'});
  const near={ja:'近傍', 'zh-Hans':'邻近','zh-Hant':'鄰近',ko:'인근',fil:'malapit',id:'dekat',ms:'berdekatan',vi:'lân cận',ru:'рядом',fa:'نزدیک'};
  function mangroveLabels(){
    const locale=AtlasLanguage.current;
    for(const input of document.querySelectorAll('input[name="habitat"][value="4"],input[name="coverage"][value="mangrove"]')){
      const label=input.closest('label');let text=[...label.childNodes].find(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());
      if(!text){text=document.createTextNode('');label.append(text);}
      const base=input.name==='coverage'?'Mangroves':'Mangrove';
      text.textContent=locale==='en'?base+' (near)':locale==='ar'?T(base+' (near)'):T(base)+' ('+(near[locale]||'near')+')';
    }
  }
  function language(){mangroveLabels();if(!AtlasUI.map)return;const compact=AtlasUI.map.getZoom()<=2;AtlasUI.map.getContainer().classList.toggle('coverage-overview',compact);for(const {layer,name,shortName,id} of labels){layer.options.offset=[7,compact?(id==='redsea'?28:id==='gulf'?-8:10):10];layer.setContent(T(compact?shortName:name));}const key=document.getElementById('studyCoverageKey');if(key)key.querySelector('span').textContent=T('Dotted outline: study coverage');}
  function init(){
    const {meta}=AtlasUI.snapshot(),map=AtlasUI.map;
    map.createPane('studyCoverage');Object.assign(map.getPane('studyCoverage').style,{zIndex:'440',pointerEvents:'none'});
    map.createPane('studyCoverageNames');Object.assign(map.getPane('studyCoverageNames').style,{zIndex:'450',pointerEvents:'none'});
    const renderer=L.svg({pane:'studyCoverage',padding:.3});
    for(const basin of meta.basins){
      const bounds=L.latLngBounds(basin.bounds);
      const box=L.rectangle(bounds,{pane:'studyCoverage',renderer,color:'#747c80',weight:1.8,opacity:1,dashArray:'1 7',lineCap:'round',fill:false,interactive:false,className:'study-coverage-box'}).addTo(map);
      outlines.push({id:basin.id,bounds:basin.bounds,layer:box});
      const layer=L.tooltip({pane:'studyCoverageNames',permanent:true,interactive:false,direction:'right',offset:[7,10],className:'study-coverage-name',opacity:1}).setLatLng([bounds.getNorth()-.45,bounds.getWest()+.15]).setContent(T(basin.name)).addTo(map);
      labels.push({layer,id:basin.id,name:basin.name,shortName:{redsea:'Red Sea',gulf:'Arabian Gulf',eastasia:'East Asia'}[basin.id]});
    }
    const key=document.createElement('div');key.id='studyCoverageKey';key.className='study-coverage-key';key.innerHTML='<i aria-hidden="true"></i><span></span>';document.querySelector('.map-legend').append(key);map.on('zoomend',language);language();
    window.AtlasStudyCoverage={outlines,labels};
  }
  window.addEventListener('atlasready',init);window.addEventListener('atlaslanguagechange',language);
  mangroveLabels();
})();
