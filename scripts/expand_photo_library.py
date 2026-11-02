"""Download a source-backed coastal photo library and compact atlas previews.

Full-resolution originals live outside the GitHub Pages payload. The public
catalogue retains their source URL and SHA256; photographs are never upscaled.
Discovery, downloads and preview generation are resumable. Run --discover,
then --download. A human can reject candidates via _cache/photo_reject_ids.json.
"""
import argparse, base64, hashlib, html, io, json, re, time, sys, os
sys.stdout.reconfigure(encoding="utf-8")
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter, deque
import requests
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/'_cache/photo_expansion'
LIBRARY = ROOT.parent/'atlas-photo-library'
UA = 'HabitatMHWAtlas/1.1 (https://github.com/adawy2050/coastal-habitat; openly licensed coastal photographs)'
# Area-centre coordinates are explicitly approximate, never presented as GPS.
# Names must occur in the source title/description unless its GPS is nearby.
AREAS = [
 ('redsea','Egypt','Dahab',28.50,34.51),('redsea','Egypt','Hurghada',27.26,33.81),
 ('redsea','Egypt','Ras Mohammed',27.73,34.25),('redsea','Egypt','Marsa Alam',25.07,34.89),
 ('redsea','Egypt','Safaga',26.74,33.94),('redsea','Egypt','Sharm el Sheikh',27.86,34.30),
 ('redsea','Egypt','Nabq',28.10,34.43),('redsea','Egypt','El Quseir',26.10,34.28),
 ('redsea','Egypt','El Gouna',27.40,33.68),('redsea','Saudi Arabia','Farasan',16.71,42.12),
 ('redsea','Saudi Arabia','Jeddah',21.49,39.12),('redsea','Saudi Arabia','Yanbu',24.09,38.05),
 ('redsea','Saudi Arabia','Umluj',25.05,37.26),('redsea','Sudan','Sanganeb',19.73,37.44),
 ('redsea','Sudan','Suakin',19.10,37.34),('redsea','Sudan','Port Sudan',19.62,37.25),
 ('redsea','Djibouti','Tadjoura',11.78,42.88),('redsea','Djibouti','Djibouti',11.61,43.15),
 ('redsea','Djibouti','Obock',11.96,43.29),('redsea','Yemen','Socotra',12.50,53.87),
 ('redsea','Eritrea','Dahlak',15.70,40.00),('redsea','Yemen','Aden',12.79,45.02),
 ('gulf','United Arab Emirates','Abu Dhabi',24.47,54.37),('gulf','United Arab Emirates','Fujairah',25.13,56.36),
 ('gulf','United Arab Emirates','Dubai',25.27,55.30),('gulf','United Arab Emirates','Sir Bani Yas',24.32,52.60),
 ('gulf','Qatar','Al Thakira',25.74,51.55),('gulf','Qatar','Al Khor',25.68,51.50),
 ('gulf','Qatar','Qatar',25.3,51.5),('gulf','Bahrain','Bahrain',26.07,50.55),
 ('gulf','Kuwait','Kuwait',29.35,48.00),('gulf','Iran','Kish',26.54,54.01),
 ('gulf','Iran','Qeshm',26.75,55.75),('gulf','Iran','Hormuz',27.07,56.46),
 ('gulf','Oman','Musandam',26.16,56.25),('gulf','Oman','Muscat',23.60,58.59),
 ('gulf','Oman','Dibba',25.62,56.26),('gulf','Oman','Daymaniyat',23.85,58.09),
 ('eastasia','Japan','Okinawa',26.50,128.0),('eastasia','Japan','Iriomote',24.32,123.82),
 ('eastasia','Japan','Ishigaki',24.42,124.20),('eastasia','Japan','Miyako',24.77,125.32),
 ('eastasia','Japan','Kerama',26.18,127.30),('eastasia','Japan','Amami',28.30,129.43),
 ('eastasia','Japan','Ogasawara',27.09,142.19),('eastasia','Japan','Yakushima',30.34,130.53),
 ('eastasia','Japan','Kagoshima',31.50,130.66),('eastasia','Japan','Sanriku',39.0,141.8),
 ('eastasia','Japan','Hokkaido',43.1,144.0),('eastasia','Japan','Shiretoko',44.0,145.1),
 ('eastasia','Taiwan','Kenting',21.95,120.78),('eastasia','Taiwan','Penghu',23.57,119.57),
 ('eastasia','Taiwan','Green Island Taiwan',22.66,121.49),('eastasia','Taiwan','Taiwan',23.5,121.0),
 ('eastasia','China','Hainan',19.15,110.0),('eastasia','China','Sanya',18.25,109.51),
 ('eastasia','China','Hong Kong',22.30,114.18),('eastasia','China','Dongzhaigang',19.95,110.56),
 ('eastasia','Vietnam','Nha Trang',12.24,109.20),('eastasia','Vietnam','Ha Long',20.91,107.10),
 ('eastasia','Philippines','Palawan',10.0,118.8),('eastasia','Philippines','Tubbataha',8.95,119.87),
 ('eastasia','Philippines','Apo Island',9.08,123.27),('eastasia','Philippines','Anilao',13.76,120.93),
 ('eastasia','Philippines','Moalboal',9.94,123.37),('eastasia','Philippines','Bohol',9.83,124.15),
 ('eastasia','Philippines','Cebu',10.30,123.90),('eastasia','Philippines','Dumaguete',9.31,123.31),
 ('eastasia','Philippines','Puerto Galera',13.50,120.95),('eastasia','Philippines','Coron',12.00,120.20),
 ('eastasia','Philippines','El Nido',11.18,119.39),('eastasia','Philippines','Siargao',9.85,126.05),
 ('eastasia','Malaysia','Sipadan',4.11,118.63),('eastasia','Malaysia','Mabul',4.25,118.63),
 ('eastasia','Malaysia','Sabah',5.5,118.0),('eastasia','Malaysia','Semporna',4.48,118.61),
 ('eastasia','Malaysia','Kuching',1.56,110.34),('eastasia','Brunei','Brunei',4.8,114.9),
 ('eastasia','Indonesia','Bunaken',1.62,124.76),('eastasia','Indonesia','Manado',1.48,124.84),
 ('eastasia','Indonesia','Lembeh',1.46,125.24),('eastasia','Indonesia','Raja Ampat',0.3,130.5),
 ('eastasia','Palau','Palau',7.5,134.5),('eastasia','Palau','Koror',7.35,134.48),
 ('eastasia','Micronesia','Chuuk',7.44,151.85),('eastasia','Micronesia','Pohnpei',6.90,158.2),
 ('eastasia','Guam','Guam',13.45,144.75),('eastasia','Northern Mariana Islands','Saipan',15.18,145.75),
 ('eastasia','Northern Mariana Islands','Rota',14.15,145.20),('eastasia','South Korea','Jeju',33.40,126.50),
 ('eastasia','Russia','Sakhalin',48.0,142.5),('eastasia','Russia','Vladivostok',43.10,131.90),
]
# Smaller named sites improve geographical specificity and regional variety.
AREAS += [
('redsea','Egypt','Abu Dabbab',25.34,34.74),('redsea','Egypt','Elphinstone',25.30,34.86),('redsea','Egypt','Wadi el Gemal',24.50,35.10),('redsea','Egypt','Marsa Mubarak',25.53,34.65),('redsea','Egypt','Tiran',27.95,34.57),('redsea','Egypt','Giftun',27.19,33.96),('redsea','Egypt','Shadwan',27.50,33.99),('redsea','Egypt','Daedalus',24.91,35.87),('redsea','Egypt','Zabargad',23.61,36.19),('redsea','Egypt','Hamata',24.28,35.39),('redsea','Saudi Arabia','Thuwal',22.30,39.10),('redsea','Saudi Arabia','Al Wajh',26.24,36.45),('redsea','Saudi Arabia','Duba',27.35,35.69),('redsea','Sudan','Shaab Rumi',19.94,37.40),
('gulf','Oman','Khasab',26.18,56.25),('gulf','Oman','Qantab',23.55,58.65),('gulf','Oman','Bandar Khayran',23.52,58.73),('gulf','Oman','Sifah',23.42,58.81),('gulf','Oman','Fins',22.91,59.23),('gulf','Oman','Tiwi',22.82,59.26),('gulf','Oman','Ras al Hadd',22.53,59.80),('gulf','Iran','Hengam',26.67,55.88),('gulf','Iran','Laft',26.90,55.79),('gulf','Iran','Hara',26.84,55.74),('gulf','Kuwait','Failaka',29.43,48.28),('gulf','Kuwait','Kubbar',29.07,48.49),('gulf','Bahrain','Hawar',25.65,50.76),('gulf','Saudi Arabia','Tarut',26.58,50.08),('gulf','Saudi Arabia','Jubail',27.01,49.66),('gulf','United Arab Emirates','Saadiyat',24.54,54.44),('gulf','United Arab Emirates','Al Zorah',25.42,55.46),('gulf','United Arab Emirates','Umm Al Quwain',25.58,55.57),('gulf','United Arab Emirates','Kalba',25.05,56.36),('gulf','United Arab Emirates','Khor Fakkan',25.34,56.35),
('eastasia','Japan','Zamami',26.23,127.30),('eastasia','Japan','Tokashiki',26.18,127.36),('eastasia','Japan','Kume',26.34,126.79),('eastasia','Japan','Taketomi',24.32,124.09),('eastasia','Japan','Hateruma',24.06,123.78),('eastasia','Japan','Yonaguni',24.46,122.99),('eastasia','Japan','Yoron',27.04,128.43),('eastasia','Japan','Onna',26.50,127.85),('eastasia','Japan','Kushimoto',33.47,135.78),('eastasia','Japan','Shirahama',33.68,135.35),('eastasia','Japan','Izu',34.85,138.85),('eastasia','Japan','Matsushima',38.37,141.06),('eastasia','Japan','Kesennuma',38.90,141.58),('eastasia','Japan','Otaru',43.19,141.0),('eastasia','Japan','Rishiri',45.18,141.22),
('eastasia','Taiwan','Lanyu',22.04,121.55),('eastasia','Taiwan','Hengchun',22.0,120.74),('eastasia','Taiwan','Tamsui',25.18,121.42),('eastasia','Taiwan','Taitung',22.76,121.15),('eastasia','China','Wenchang',19.65,110.75),('eastasia','China','Wuzhizhou',18.31,109.76),('eastasia','China','Zhanjiang',21.20,110.40),('eastasia','China','Shenzhen',22.52,114.40),
('eastasia','Philippines','Puerto Princesa',9.74,118.75),('eastasia','Philippines','Subic',14.81,120.27),('eastasia','Philippines','Batangas',13.75,121.0),('eastasia','Philippines','Dauin',9.19,123.27),('eastasia','Philippines','Siquijor',9.18,123.60),('eastasia','Philippines','Panglao',9.58,123.75),('eastasia','Philippines','Malapascua',11.33,124.11),('eastasia','Philippines','Bantayan',11.16,123.72),('eastasia','Philippines','Camiguin',9.17,124.72),('eastasia','Philippines','Davao',7.05,125.62),('eastasia','Philippines','Baclayon',9.62,123.91),('eastasia','Philippines','Guimaras',10.58,122.60),('eastasia','Philippines','Romblon',12.57,122.27),('eastasia','Philippines','Bolinao',16.38,119.89),('eastasia','Philippines','Pagudpud',18.56,120.79),('eastasia','Philippines','Batanes',20.45,121.97),('eastasia','Philippines','Port Barton',10.41,119.17),('eastasia','Philippines','Culion',11.88,120.02),('eastasia','Philippines','Mactan',10.29,124.0),('eastasia','Philippines','Caramoan',13.77,123.87),
('eastasia','Malaysia','Bako',1.70,110.45),('eastasia','Malaysia','Bintulu',3.20,113.0),('eastasia','Malaysia','Miri',4.40,113.99),('eastasia','Malaysia','Kota Kinabalu',5.98,116.08),('eastasia','Malaysia','Sandakan',5.84,118.1),('eastasia','Malaysia','Kudat',6.89,116.84),('eastasia','Malaysia','Tawau',4.23,117.88),('eastasia','Indonesia','Likupang',1.67,125.06),('eastasia','Indonesia','Morotai',2.3,128.5),('eastasia','Indonesia','Ternate',0.8,127.4),('eastasia','Indonesia','Waigeo',0.20,130.8),('eastasia','Indonesia','Halmahera',1.5,128.0),
]
DISCOVERY_TARGET=1600
SUBJECTS = [('coral','coral reef'),('mangrove','mangrove'),('coast','coast sea'),('coast','beach'),('coral','reef underwater'),('coast','shoreline')]
REJECT = re.compile(r'\b(food|sushi|restaurant|dishes|dish|clock tower|dog|sign|map|diagram|logo|stamp|postcard|painting|drawing|illustration|micrograph|graph|museum|aquarium|fossil|aircraft|portrait|basketball|football|stadium|conference|flag|army|military|sunset|night|missile|live.fire|coast guard|training|U S SOF|exercise|USS|USNS|USCG|military|admiralty|nautical chart|territorial claim|East Asia and Oceania|plan of|statue|lighthouse|mosque|sculpture|hummingbird|flycatcher|local speciality|marine life species|marina boulevard|promenade|distance sign|signpost|road sign|dessole|hotel|resort|architecture|USMC|USCGC|MEU|navy|naval|marines|helicopter|raid force|squadron|warship|vessel|airfield|airport|amphibious|soldier|sailor|patrol|destroyer|carrier|military|harbour crane|harbor crane)\b',re.I)

def clean(v): return html.unescape(re.sub('<[^>]*>',' ',str(v))).strip()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); temp=path.with_suffix(path.suffix+f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8');temp.replace(path)
def progress(stage,**values):
    path=CACHE/'progress.json'
    try:old=json.loads(path.read_text('utf8')) if path.exists() else {}
    except (json.JSONDecodeError,OSError):old={}
    old.update(values);old.update(stage=stage,updated=datetime.now(timezone.utc).isoformat())
    save(path,old)
    save(ROOT/'dist/status/photos.json',old)
def session():
    s=requests.Session();s.headers['User-Agent']=UA;return s
def get(s,url,**kw):
    for attempt in range(6):
        try:
            r=s.get(url,timeout=90,**kw)
            if r.status_code in (429,503,502,504): time.sleep(5+attempt*5);continue
            r.raise_for_status();return r
        except requests.RequestException:
            if attempt==5:raise
            time.sleep(3+attempt*4)
    raise RuntimeError('Repeated source error')
def discover():
    path=CACHE/'candidates.json'; candidates=json.loads(path.read_text('utf8')) if path.exists() else []
    donefile=CACHE/'searches.json';done=json.loads(donefile.read_text('utf8')) if donefile.exists() else []
    existing=json.loads((ROOT/'dist/images/credits.json').read_text('utf8')); seen={p['sourceTitle'] for p in existing+candidates}
    s=session()
    for basin,country,area,la,lo in AREAS:
      for habitat,subject in SUBJECTS:
        query=area+' '+subject+' filetype:bitmap'
        if query in done:continue
        params={'action':'query','format':'json','generator':'search','gsrnamespace':6,'gsrlimit':40,'gsrsearch':query,'prop':'imageinfo|revisions','rvprop':'content','rvslots':'main','iiprop':'url|size|extmetadata','iiextmetadatafilter':'LicenseShortName|LicenseUrl|Artist|ImageDescription|GPSLatitude|GPSLongitude'}
        try: pages=get(s,'https://commons.wikimedia.org/w/api.php',params=params).json().get('query',{}).get('pages',{}).values()
        except Exception as e:print('SEARCH FAILED',query,str(e),flush=True);continue
        added=0
        for p in pages:
            if p['title'] in seen:continue
            info=p.get('imageinfo',[{}])[0];meta=info.get('extmetadata',{});val=lambda k:meta.get(k,{}).get('value','')
            lic=val('LicenseShortName');url=info.get('url','').split('?')[0]
            if max(info.get('width',0),info.get('height',0))<3000 or not url.lower().endswith(('.jpg','.jpeg')):continue
            if not (lic.startswith(('CC BY','CC0')) or lic in ('Public domain','PDM')) or 'NC' in lic or 'ND' in lic:continue
            title=p['title'][5:].rsplit('.',1)[0].replace('_',' ');desc=clean(val('ImageDescription'));text=title+' '+desc
            if REJECT.search(title) or re.search(r'map of|nautical chart|geographical map|lithograph|engraving|woodcut|aquarium|captivity|fish tank',desc,re.I):continue
            if re.match(r'^\d{3}-CFD|^\d{6}-[A-Z]-',title):continue
            if not re.search(r'\b(coral|reef|mangrove|coast|shore|beach|island|underwater|seagrass|seaweed|kelp|lagoon|sea|ocean|bay|islet|diving|intertidal)\b',text,re.I):continue
            lat,lon=val('GPSLatitude'),val('GPSLongitude');precision='GPS'
            content=p.get('revisions',[{}])[0].get('slots',{}).get('main',{}).get('*','')
            m=re.search(r'\{\{(?:[Ll]ocation|[Oo]bject location|[Ll]ocation dec)\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)',content)
            if m and not lat:
                full=re.search(r'\{\{(?:[Ll]ocation|[Oo]bject location|[Ll]ocation dec)\s*\|([^{}]+)\}\}',content)
                parts=[v.strip() for v in full.group(1).split('|')] if full else []
                try:
                    if len(parts)>=8 and parts[3].upper() in ('N','S') and parts[7].upper() in ('E','W'):
                        lat=(float(parts[0])+float(parts[1])/60+float(parts[2])/3600)*(-1 if parts[3].upper()=='S' else 1)
                        lon=(float(parts[4])+float(parts[5])/60+float(parts[6])/3600)*(-1 if parts[7].upper()=='W' else 1)
                    else:lat,lon=m.groups()
                except ValueError:lat=lon=None
            area_tokens=[t.lower() for t in re.findall(r'[A-Za-z]+',area) if t.lower() not in ('el','al','island')]
            named=all(t in text.lower() for t in area_tokens)
            if not lat or not lon:
                # A species' distribution paragraph is not a photograph location.
                if not all(t in title.lower() for t in area_tokens):continue
                lat,lon=la,lo;precision='Photo area (approximate)'
            try:lat,lon=float(lat),float(lon)
            except ValueError:continue
            if not named and (abs(lat-la)>2 or abs(lon-lo)>2):continue
            if basin=='eastasia' and not (0<=lat<=55 and 110<=lon<=160):continue
            if basin!='eastasia' and not (9<=lat<=32 and 31<=lon<=61):continue
            # Classification follows source description, not the search query.
            actual='mangrove' if re.search(r'\bmangrove',text,re.I) else 'seagrass' if re.search(r'\bseagrass|zostera',text,re.I) else 'kelp_macroalgae' if re.search(r'\bkelp|seaweed forest',text,re.I) else 'coral' if re.search(r'\bcoral|reef',text,re.I) else 'coast'
            ident='photo-'+hashlib.sha256(p['title'].encode()).hexdigest()[:12]
            licenseurl=val('LicenseUrl').replace('http://','https://')
            if not licenseurl:licenseurl='https://commons.wikimedia.org/wiki/Template:PD-old' if lic in ('Public domain','PDM') else 'https://creativecommons.org/publicdomain/zero/1.0/'
            candidates.append({'id':ident,'file':f'external/{ident}.jpg','title':title,'titleAr':title,'location':area+', '+country,'locationAr':area+', '+country,'country':country,'basin':basin,'habitat':actual,'latitude':lat,'longitude':lon,'coordinateSource':'Wikimedia Commons photo coordinates' if precision=='GPS' else 'Named area in source; approximate area centre','locationPrecision':precision,'source':info['descriptionurl'],'original':url,'width':info['width'],'height':info['height'],'author':clean(val('Artist')),'license':lic if lic!='PDM' else 'Public domain','licenseUrl':licenseurl,'retrieved':datetime.now(timezone.utc).strftime('%Y-%m-%d'),'captionClaims':desc,'sourceTitle':p['title'],'query':query,'originalHosted':False,'formats':['webp'],'responsiveWidths':[480,960,1600],'changes':'Original unchanged; previews resized and compressed only'})
            seen.add(p['title']);added+=1
            if added>=12:break
        done.append(query);save(path,candidates);save(donefile,done)
        progress('discovery',searches=len(done),candidateCount=len(candidates),targetNew=423)
        print(query,added,'candidates',len(candidates),flush=True);time.sleep(.5)
        if len(candidates)>=DISCOVERY_TARGET:return

def download():
    existing=json.loads((ROOT/'dist/images/credits.json').read_text('utf8')); base=json.loads((CACHE/'base_catalogue.json').read_text('utf8')) if (CACHE/'base_catalogue.json').exists() else [p for p in existing if p.get('libraryGeneration')=='original47']
    candidates=json.loads((CACHE/'candidates.json').read_text('utf8')); rejects=set(json.loads((CACHE/'rejected.json').read_text('utf8'))) if (CACHE/'rejected.json').exists() else set()
    if (CACHE/'manual_rejected.json').exists():rejects.update(json.loads((CACHE/'manual_rejected.json').read_text('utf8')))
    complete=json.loads((CACHE/'downloaded.json').read_text('utf8')) if (CACHE/'downloaded.json').exists() else []
    known={p['id'] for p in complete};hashes={p['sha256'] for p in base+complete};s=session()
    # Visit countries and named areas in turn rather than exhausting Egypt/Japan first.
    groups=defaultdict(deque)
    for p in candidates:groups[(p['country'],p['location'])].append(p)
    ordered=[];counts=Counter(p['country'] for p in complete)
    while groups:
        key=min(groups,key=lambda k:(counts[k[0]],len([q for q in ordered if q['location']==k[1]]),k))
        p=groups[key].popleft();ordered.append(p);counts[key[0]]+=1
        if not groups[key]:del groups[key]
    candidates=ordered

    LIBRARY.mkdir(exist_ok=True)
    from concurrent.futures import ThreadPoolExecutor
    def fetch_one(p):
        path=LIBRARY/(p['id']+'.jpg')
        if not path.exists():
            content=get(session(),p['original']).content
            if not content.startswith(b'\xff\xd8'):raise ValueError('Not a JPEG')
            temp=path.with_suffix('.jpg.part');temp.write_bytes(content);temp.replace(path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        with Image.open(path) as source:
            source.load()
            if max(source.size)<3000:raise ValueError('Source below3000px')
            p['width'],p['height']=source.size;im=ImageOps.exif_transpose(source).convert('RGB')
            p['responsiveWidths']=[w for w in (480,960,1600) if w<=im.width]
            if 960 not in p['responsiveWidths']:raise ValueError('Source width below960px')
            for w in p['responsiveWidths']:
                out=ROOT/'dist/images/responsive'/f"{p['id']}-{w}.webp"
                if not out.exists():im.resize((w,round(im.height*w/im.width)),Image.Resampling.LANCZOS).save(out,'WEBP',quality=70,method=4)
            thumb=im.copy();thumb.thumbnail((24,24));buf=io.BytesIO();thumb.save(buf,'JPEG',quality=35)
            p['placeholder']='data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode()
        p['sha256']=digest;p['originalBytes']=path.stat().st_size
        return p
    todo=[]
    for p in candidates:
        if p['id'] in known or p['id'] in rejects:continue
        if REJECT.search(p['title']):rejects.add(p['id']);continue
        if not re.search(r'coast|sea|reef|mangrove|beach|coral|lagoon|island|tide|bay|shore|rock|aerial|dunes|underwater|seagrass|zostera|kelp|Kenting|Raja Ampat|Ishigaki|Iriomote|Kushimoto|Ogasawara|Penghu',p['title'],re.I):rejects.add(p['id']);continue
        if re.match(r'^ISS\d|^AS\d|^\d{3}-CFD|^\d{6}-[A-Z]-',p['title']):rejects.add(p['id']);continue
        todo.append(p)
    save(CACHE/'rejected.json',sorted(rejects))
    # Two concurrent transfers, bounded to respect the Wikimedia source service.
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=[];it=iter(todo)
        for _ in range(2):
            p=next(it,None)
            if p:pending.append((p,pool.submit(fetch_one,p)))
        while pending:
            p,future=pending.pop(0)
            try:
                p=future.result()
                if p['sha256'] in hashes:rejects.add(p['id'])
                else:
                    complete.append(p);hashes.add(p['sha256']);known.add(p['id']);save(CACHE/'downloaded.json',complete)
                    progress('download',downloadedNew=len(complete),acceptedNew=sum(q['id'] not in rejects for q in complete),total=len(base)+sum(q['id'] not in rejects for q in complete),targetTotal=470,originalBytes=sum(q['originalBytes'] for q in complete))
                    print('DOWNLOADED',len(complete),p['id'],p['basin'],p['title'][:90],flush=True)
            except Exception as e:print('DOWNLOAD FAILED',p['id'],str(e),flush=True)
            if len([q for q in complete if q['id'] not in rejects])+len(base)<470:
                p=next(it,None)
                if p:pending.append((p,pool.submit(fetch_one,p)))
    if (CACHE/'manual_rejected.json').exists():rejects.update(json.loads((CACHE/'manual_rejected.json').read_text('utf8')))
    save(CACHE/'rejected.json',sorted(rejects))
    selected=[q for q in complete if q['id'] not in rejects][:470-len(base)]
    save(LIBRARY/'catalogue.json',base+selected)
    if len(base)+len(selected)==470:
        save(CACHE/'proposed_catalogue.json',base+selected)
        print('PROPOSED CATALOGUE470; visual review and finalization required',flush=True)
    contacts(selected)

def contacts(photos):
    for start in range(0,len(photos),70):
        subset=photos[start:start+70];sheet=Image.new('RGB',(1400,((len(subset)+6)//7)*125),'white');draw=ImageDraw.Draw(sheet)
        for k,p in enumerate(subset):
            im=Image.open(ROOT/'dist/images/responsive'/f"{p['id']}-480.webp");im.thumbnail((194,94));x=(k%7)*200;y=(k//7)*125;sheet.paste(im,(x,y));draw.text((x,y+95),f"{start+k+1} {p['id'][-6:]} {p['basin']}",fill='black');draw.text((x,y+109),p['title'][:26].encode('ascii','replace').decode(),fill='black')
        sheet.save(CACHE/f'contact-{start//70+1}.jpg',quality=85)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--discover',action='store_true');parser.add_argument('--download',action='store_true');args=parser.parse_args()
    if args.discover:discover()
    if args.download:download()
