/* Paint the photograph and bilingual introduction before loading chart engines. */
(() => {
  const load=path=>new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=new URL(path,document.baseURI).href;script.onload=resolve;script.onerror=()=>reject(Error('Unable to load '+path));document.head.append(script);});
  async function start(){
    const hero=document.querySelector('.hero-image img');
    await document.fonts.ready;
    await new Promise(requestAnimationFrame);await new Promise(requestAnimationFrame);
    try{await Promise.all([load('./vendor/leaflet.js'),load('./vendor/plotly-cartesian.min.js')]);await load('./interface.js?v=20261101-final-coverage-r1');}
    catch(error){document.querySelector('#loadingText').textContent=error.message;document.documentElement.dataset.error=error.message;}
  }
  start();
})();
