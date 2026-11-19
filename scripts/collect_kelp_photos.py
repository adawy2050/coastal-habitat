"""Add geotagged open-licence coastal photographs, retaining original credits."""
from pathlib import Path
import hashlib,html,json,re,time,io
import requests
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'dist/kelp';OUT=D/'photos';OUT.mkdir(exist_ok=True)
existing=json.loads((ROOT/'dist/images/credits.json').read_text(encoding='utf-8'));known={p['source'] for p in existing}
path=D/'data/photos.json';selected=json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
known.update(p['source'] for p in selected)
session=requests.Session();session.headers['User-Agent']='CoastalHabitatObservatory/1.0 (research photographs; ahmed.eladawy@jamstec.go.jp)'
plain=lambda s:html.unescape(re.sub('<[^>]+>',' ',s)).strip()
for place in ['Hokkaido coast','Shiretoko coast','Nemuro coast','Kushiro coast','Muroran coast','Hakodate coast','Rishiri coast','Otaru coast','Sanriku coast','Aomori coast','Miyako beach','Iwaki coast','Cape Nosappu','Kiritappu','Cape Erimo','Shiretoko','Nemuro','Muroran','Rausu']:
 try:
  params={'action':'query','format':'json','generator':'search','gsrnamespace':6,'gsrlimit':30,'gsrsearch':place,'prop':'imageinfo|revisions','rvprop':'content','rvslots':'main','iiprop':'url|size|extmetadata','iiurlwidth':1280}
  r=session.get('https://commons.wikimedia.org/w/api.php',params=params,timeout=30);r.raise_for_status();count=0
  for p in r.json().get('query',{}).get('pages',{}).values():
   info=p.get('imageinfo',[{}])[0];meta=info.get('extmetadata',{});get=lambda k:meta.get(k,{}).get('value','');lic=get('LicenseShortName');text=plain(get('ImageDescription'))+' '+p['title']
   if re.search(r'ASTER|vortices|Joint Government|Patrol Vessel|Guide board|Super ARCS',text,re.I) or p['title'].lower()=='file:nosappu.jpg':continue
   if not re.search(r'coast|cape|beach|shore|sea |bay|peninsula|ocean|岬|海|浜|岸|湾',text,re.I):continue
   if not (lic.startswith('CC BY') or lic in ['CC0','Public domain','PDM']) or 'NC' in lic or 'ND' in lic:continue
   if info.get('width',0)<1600 or info.get('height',0)<900 or not info.get('url','').split('?')[0].lower().endswith(('.jpg','.jpeg')):continue
   if info.get('descriptionurl') in known:continue
   lat,lon=get('GPSLatitude'),get('GPSLongitude');coords=p.get('coordinates',[])
   if coords:lat,lon=coords[0]['lat'],coords[0]['lon']
   if not lat or not lon:
    content=p.get('revisions',[{}])[0].get('slots',{}).get('main',{}).get('*','');m=re.search(r'\{\{(?:[Ll]ocation|[Oo]bject location|[Ll]ocation dec)\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)',content)
    if m:lat,lon=m.groups()
   try:lat,lon=float(lat),float(lon)
   except (ValueError,TypeError):continue
   if not (36<=lat<=46.5 and 136<=lon<=147):continue
   image=session.get(info.get('thumburl',info['url']),timeout=30);image.raise_for_status();im=Image.open(io.BytesIO(image.content)).convert('RGB');im.thumbnail((1280,960));ident='kelp-'+hashlib.sha256(p['title'].encode()).hexdigest()[:12];im.save(OUT/(ident+'.webp'),'WEBP',quality=85)
   selected.append({'id':ident,'imagePath':'./photos/'+ident+'.webp','title':p['title'][5:].rsplit('.',1)[0].replace('_',' '),'location':p['title'][5:].rsplit('.',1)[0].replace('_',' ')+', Japan','latitude':lat,'longitude':lon,'coordinateSource':'Wikimedia Commons geotag','source':info['descriptionurl'],'original':info['url'],'author':plain(get('Artist')),'license':lic,'licenseUrl':get('LicenseUrl'),'originalWidth':info['width'],'originalHeight':info['height'],'changes':'Resized and converted to WebP; no crop.','retrieved':'2026-11-02'});known.add(info['descriptionurl']);count+=1
   if count>=3:break
  path.write_text(json.dumps(selected,ensure_ascii=False,separators=(',',':')),encoding='utf-8');print(place,count,'total',len(selected),flush=True)
 except Exception as e:print(place,type(e).__name__,str(e)[:100],flush=True)
 time.sleep(.25)
print('Added licensed coastal photos:',len(selected),flush=True)
