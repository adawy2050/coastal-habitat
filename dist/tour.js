/* Guided selections use the existing map state and verified per-cell records. */
(() => {
  const steps=[
    {title:'Northern Red Sea',ar:'شمال البحر الأحمر',lat:27,lon:34,basin:'redsea',section:'explore'},
    {title:'Southern Red Sea',ar:'جنوب البحر الأحمر',lat:16.5,lon:41.8,basin:'redsea',section:'history'},
    {title:'Gulf of Aden',ar:'خليج عدن',lat:12.6,lon:45,basin:'redsea',section:'history'},
    {title:'Arabian Gulf',ar:'الخليج العربي',lat:25.3,lon:54.5,basin:'gulf',section:'connections'},
    {title:'Gulf of Oman',ar:'خليج عُمان',lat:25.3,lon:57,basin:'gulf',section:'climate'},
    {title:'Okinawa reefs',ar:'شعاب أوكيناوا',lat:26.2,lon:127.3,basin:'eastasia',section:'history'},
    {title:'Northern Japan seagrass and kelp',ar:'الأعشاب والطحالب في شمال اليابان',lat:43,lon:144,basin:'eastasia',section:'history'},
    {title:'Philippine habitats',ar:'موائل الفلبين',lat:10.3,lon:119.2,basin:'eastasia',section:'climate'},
    {title:'Western Pacific islands',ar:'جزر غرب المحيط الهادئ',lat:7.5,lon:134.5,basin:'eastasia',section:'connections'},
    {title:'Next-season probability',ar:'احتمال الموسم القادم',lat:25.3,lon:57,basin:'gulf',section:'outlook',forecast:true}
  ];
  let index=0,running=false,busy=false;
  const panel=document.createElement('aside');panel.id='tourPanel';panel.className='tour-panel';panel.hidden=true;panel.setAttribute('aria-labelledby','tourHeading');panel.innerHTML='<div class="tour-progress" id="tourProgress"></div><div class="tour-heading"><h2 id="tourHeading"></h2><button id="tourExit">Exit tour</button></div><p id="tourFinding" aria-live="polite"></p><div class="tour-actions"><button id="tourBack">Previous step</button><span id="tourPosition"></span><button id="tourNext">Next step</button></div>';document.body.append(panel);
  const $=id=>document.getElementById(id), ar=()=>AtlasLanguage.current==='ar';
  async function show(n){if(!window.AtlasUI||busy)return;index=Math.max(0,Math.min(steps.length-1,n));running=true;busy=true;panel.hidden=false;$('tourNext').disabled=$('tourBack').disabled=true;const step=steps[index];$('tourHeading').textContent=ar()?step.ar:step.title;$('tourFinding').textContent=ar()?'جارٍ اختيار الخلية…':'Selecting the habitat cell…';
    try{const finding=await AtlasUI.visit(step);if(!running)return;$('tourFinding').textContent=ar()?finding.ar:finding.en;$('tourProgress').replaceChildren(...steps.map((s,k)=>{const b=document.createElement('button');b.className=k===index?'current':'';b.setAttribute('aria-label',ar()?s.ar:s.title);b.setAttribute('aria-current',k===index?'step':'false');b.onclick=()=>show(k);return b;}));$('tourPosition').textContent=`${index+1} / ${steps.length}`;$('tourNext').textContent=index===steps.length-1?'Finish tour':'Next step';$('tourBack').disabled=index===0;$('tourNext').disabled=false;const url=new URL(location.href);url.searchParams.set('tour',String(index+1));history.replaceState(null,'',url);$(step.section).scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
    }finally{busy=false;}}
  function exit(){running=false;panel.hidden=true;const url=new URL(location.href);url.searchParams.delete('tour');history.replaceState(null,'',url);$('tourButton')?.focus();}
  $('tourBack').onclick=()=>show(index-1);$('tourNext').onclick=()=>index===steps.length-1?exit():show(index+1);$('tourExit').onclick=exit;
  for(const id of ['tourButton','tourStart'])$(id).onclick=()=>show(0);
  window.addEventListener('atlaslanguagechange',()=>{if(running)show(index);});
  function init(){const n=Number(new URL(location.href).searchParams.get('tour'));if(n>=1&&n<=steps.length)show(n-1);}
  window.addEventListener('atlasready',init);if(document.documentElement.dataset.ready==='true')init();
})();
