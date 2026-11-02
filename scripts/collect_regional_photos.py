"""Find openly licensed, geotagged photographs for the atlas; cache metadata."""
import hashlib,html,json,re,time
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[1]
QUERIES=[('Japan','coral','Okinawa coral reef'),('Japan','seagrass','Japan seagrass'),('Japan','kelp_macroalgae','Japan kelp underwater'),('Japan','mangrove','Iriomote mangrove'),('Japan','coast','Hokkaido coast'),('Japan','coast','Sanriku coast'),('Japan','coast','Ogasawara coast'),('Taiwan','coral','Taiwan coral underwater'),('Taiwan','mangrove','Taiwan mangrove'),('China','mangrove','Hainan mangrove'),('China','coast','Hong Kong coast'),('Vietnam','coral','Vietnam coral reef'),('Vietnam','mangrove','Vietnam mangrove'),('Philippines','coral','Philippines coral reef'),('Philippines','seagrass','Philippines seagrass'),('Philippines','mangrove','Philippines mangroves'),('Philippines','coast','Palawan coast'),('Indonesia','coral','Bunaken coral reef'),('Indonesia','coral','Raja Ampat reef'),('Indonesia','mangrove','Indonesia mangrove'),('Malaysia','coral','Sabah coral reef'),('Malaysia','mangrove','Borneo mangrove'),('Brunei','mangrove','Brunei mangrove'),('Palau','coral','Palau coral reef'),('Micronesia','coast','Pohnpei coast'),('Micronesia','coast','Kosrae coast'),('Micronesia','coral','Chuuk reef'),('Guam','coral','Guam coral reef'),('Northern Mariana Islands','coast','Saipan coast'),('South Korea','coast','Jeju coast'),('Russia','coast','Sakhalin coast'),('Egypt','coral','Dahab coral reef'),('Saudi Arabia','coral','Red Sea Saudi Arabia coral reef'),('Sudan','coast','Sudan Red Sea coast'),('Djibouti','coast','Djibouti coast'),('Oman','coral','Oman coral underwater'),('Iran','coast','Kish island coast'),('United Arab Emirates','mangrove','Abu Dhabi mangrove'),('Qatar','mangrove','Qatar mangrove')]
LOCATIONS={'Japan':(26.5,128.0,'Okinawa'), 'Taiwan':(22.1,120.8,'Taiwan'), 'China':(19.5,110.0,'Hainan'), 'Vietnam':(16.0,108.0,'Vietnam'), 'Philippines':(11.0,123.0,'Philippines'), 'Indonesia':(1.62,124.75,'Bunaken'), 'Malaysia':(5.5,118.0,'Sabah'), 'Brunei':(4.8,114.9,'Brunei'), 'Palau':(7.5,134.5,'Palau'), 'Micronesia':(6.9,158.2,'Pohnpei'), 'Guam':(13.45,144.75,'Guam'), 'Northern Mariana Islands':(15.2,145.75,'Saipan'), 'South Korea':(33.4,126.5,'Jeju'), 'Russia':(48.0,142.5,'Sakhalin'), 'Egypt':(28.5,34.5,'Dahab'), 'Saudi Arabia':(21.5,39.0,'Jeddah'), 'Sudan':(19.6,37.3,'Port Sudan'), 'Djibouti':(11.6,43.1,'Djibouti'), 'Oman':(23.6,58.5,'Muscat'), 'Iran':(26.54,54.0,'Kish'), 'United Arab Emirates':(24.45,54.5,'Abu Dhabi'), 'Qatar':(25.74,51.55,'Al Thakira')}
def main():
    session=requests.Session();session.headers['User-Agent']='HabitatMHWAtlas/1.0 (https://github.com/adawy2050/coastal-habitat; research photographs)'
    cache=ROOT/'_cache/regional_photo_candidates.json';selected=json.loads(cache.read_text('utf8')) if cache.exists() else []
    done={p['query'] for p in selected}
    for country,habitat,query in QUERIES:
        if query in done:continue
        params={'action':'query','format':'json','generator':'search','gsrnamespace':6,'gsrlimit':20,'gsrsearch':query+' filetype:bitmap','prop':'imageinfo|revisions','rvprop':'content','rvslots':'main','iiprop':'url|size|extmetadata','iiurlwidth':480}
        response=session.get('https://commons.wikimedia.org/w/api.php',params=params,timeout=45);response.raise_for_status();pages=response.json().get('query',{}).get('pages',{}).values();count=0
        for p in pages:
            info=p.get('imageinfo',[{}])[0];meta=info.get('extmetadata',{});get=lambda k:meta.get(k,{}).get('value','');lic=get('LicenseShortName');lat,lon=get('GPSLatitude'),get('GPSLongitude')
            if max(info.get('width',0),info.get('height',0))<3000 or not info.get('url','').split('?')[0].lower().endswith(('.jpg','.jpeg')):continue
            if not (lic.startswith(('CC BY','CC0')) or lic in ['Public domain','PDM']) or 'NC' in lic or 'ND' in lic:continue
            precision='GPS'
            content=p.get('revisions',[{}])[0].get('slots',{}).get('main',{}).get('*','')
            match=re.search(r'\{\{(?:[Ll]ocation|[Oo]bject location|[Ll]ocation dec)\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|\s*(-?\d+(?:\.\d+)?)',content)
            if match and not lat:lat,lon=match.groups()
            if not lat or not lon:
                text=html.unescape(re.sub('<[^>]+>',' ',get('ImageDescription')))+' '+p['title']
                la,lo,place=LOCATIONS[country]
                if place.lower() not in text.lower():continue
                lat,lon=la,lo;precision='Photo area (approximate)'
                if 'Hokkaido' in text:lat,lon,place=43.0,144.0,'Hokkaido'
            else:place=country
            if any(x.get('sourceTitle')==p['title'] for x in selected):continue
            try:lat,lon=float(lat),float(lon)
            except ValueError:continue
            # Search results must actually lie within the atlas bounds.
            east=0<=lat<=55 and 110<=lon<=160;west=9<=lat<=32 and 31<=lon<=60
            if not (east or west):continue
            description=re.sub('<[^>]+>',' ',get('ImageDescription'));description=html.unescape(re.sub(r'\s+',' ',description)).strip()
            ident='photo-'+hashlib.sha256(p['title'].encode()).hexdigest()[:12]
            selected.append({'id':ident,'file':f'originals/{ident}.jpg','title':p['title'][5:].rsplit('.',1)[0].replace('_',' '),'titleAr':p['title'][5:].rsplit('.',1)[0].replace('_',' '),'location':place+', '+country,'locationAr':place+', '+country,'country':country,'basin':'eastasia' if east else ('redsea' if lon<47 else 'gulf'),'habitat':habitat,'latitude':lat,'longitude':lon,'coordinateSource':'Wikimedia Commons GPS metadata' if precision=='GPS' else 'Named area in photo source; approximate area centre','locationPrecision':precision,'source':info['descriptionurl'],'original':info['url'].split('?')[0],'width':info['width'],'height':info['height'],'author':html.unescape(re.sub('<[^>]+>','',get('Artist'))).strip(),'artistHtml':get('Artist'),'license':lic,'licenseUrl':get('LicenseUrl'),'retrieved':'2026-10-18','captionClaims':description,'sourceTitle':p['title'],'sourceDescriptionHtml':get('ImageDescription'),'changes':'Original unchanged; previews resized only','query':query,'thumb':info.get('thumburl','')})
            count+=1
            if count>=2:break
        cache.write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf8');print(query,count,'total',len(selected),flush=True);time.sleep(1.1)
if __name__=='__main__':main()
