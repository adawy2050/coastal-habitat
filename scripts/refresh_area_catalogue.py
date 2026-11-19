"""Reviewed regional sources and explicit study-area bounds for the atlas.

Bounds describe the named study area, not an observation at the selected cell.
Metadata are fetched from the DOI registry; future and non-journal items fail.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import datetime,html,json,requests,sys,time

ROOT=Path(__file__).resolve().parents[1]/'dist/content'
TODAY='2026-11-01'
AREAS={
 'aqaba':('Gulf of Aqaba',[34,27.4,35.6,30]),
 'egypt':('Southern Egyptian Red Sea',[34,22,36.8,26]),
 'egyptcoast':('Egyptian Red Sea coast',[32,22,36.8,28.2]),
 'central':('Central Red Sea',[34.5,20,40.8,25.8]),
 'south':('Southern Red Sea and Bab el Mandeb',[38,12,44.5,20]),
 'gulf':('Arabian Gulf',[47,23,57,31]),
 'uae':('UAE coast',[51,23,56.6,26.5]),
 'abudhabi':('Abu Dhabi coast',[51.2,23,54.9,25.4]),
 'iran':('Southern Iranian islands',[49,26,57,30]),
 'oman':('Gulf of Oman',[55.5,22,61,27]),
 'japan':('Japan and surrounding seas',[127,29,151,47]),
 'kuroshio':('Kuroshio and Kuroshio Extension',[128,28,155,40]),
 'northjapan':('Northern Japan',[138,36,151,47]),
 'ryukyu':('Ryukyu Islands and southern Japan',[122,23,137,35]),
 'jeju':('Jeju Island and southern Korea',[125,32,130,36]),
 'scs':('South China Sea',[104,0,122,25]),
 'philippines':('Philippine seas',[116,4,129,22]),
 'seasia':('Southeast Asia and tropical western Pacific',[95,-12,145,26]),
 'nwpacific':('Northwestern Pacific',[120,20,165,50])}

def coverage(keys):return [{'name':AREAS[k][0],'bounds':AREAS[k][1]} for k in keys]

ADDITIONS=[
 ('10.1016/j.scitotenv.2025.180463','redsea','habitats',['aqaba'],'خليج العقبة كملاذ حراري: أربع سنوات من الموجات البحرية الحارة المتزايدة'),
 ('10.1016/j.wace.2025.100771','redsea','regional',['south'],'الموجات البحرية الحارة تحت السطح وابيضاض المرجان في جنوب البحر الأحمر'),
 ('10.21608/ejabf.2025.451010','redsea','habitats',['egypt'],'المرونة الحرارية للمرجان في شعاب جنوب البحر الأحمر المصرية'),
 ('10.3390/environments12070248','redsea','habitats',['egypt','central'],'صور الغواصين لتقييم آثار الموجات الحارة على شعاب وسط البحر الأحمر'),
 ('10.1016/j.scitotenv.2025.179073','redsea','habitats',['central'],'موجة بحرية حارة شديدة مرتبطة بنفوق جماعي للأسماك في البحر الأحمر'),
 ('10.3390/su18147456','redsea','habitats',['egyptcoast'],'حوكمة البحر الأحمر المصري ومرونة الشعاب تحت الضغوط المناخية والبشرية'),
 ('10.1016/j.marenvres.2025.107522','eastasia','habitats',['jeju'],'تغير تعاقب العوالق النباتية خلال الحرارة البحرية الشديدة على ساحل كوريا الجنوبي'),
 ('10.1126/sciadv.adz4647','eastasia','methods',['nwpacific'],'روابط بين الأحواض تطيل الموجات البحرية الحارة في شمال غرب المحيط الهادئ'),
 ('10.1029/2025JC023755','eastasia','habitats',['scs'],'استمرار الموجات البحرية الحارة يغير العوالق والإنتاجية في بحر الصين الجنوبي'),
 ('10.3390/d18100618','eastasia','habitats',['jeju'],'اختلاف ابيضاض المرجان حسب العمق والنوع في جزيرة جيجو خلال الحدث العالمي الرابع'),
 ('10.3390/rs17061048','eastasia','habitats',['philippines'],'الموجات البحرية الحارة وتحمض المحيط في بيئات المرجان بالفلبين'),
 ('10.1038/s41598-026-43302-4','gulf','habitats',['iran'],'حالة المرجان وتوزيعه حول ثلاث جزر في جنوب إيران'),
 ('10.1007/s00338-026-02922-y','gulf','habitats',['abudhabi'],'زيادة الأمراض في شعاب أبوظبي مع ارتفاع حرارة الخليج'),
 ('10.1029/2025JC023614','eastasia','regional',['seasia'],'تزايد تكرار الموجات البحرية الحارة ومدتها وعمقها عبر جنوب شرق آسيا'),
 ('10.1038/s41467-026-78279-1',None,'forecast',[],'إمكان توقع الموجات البحرية الحارة في مناطق الشعاب على مدى عدة سنوات'),
 ('10.1029/2026EF008642',None,'methods',[],'ظهور حالات الموجات البحرية الحارة الدائمة عبر المحيطات العالمية')]

def metadata(row):
 doi,basin,topic,keys,ar=row
 r=requests.get('https://api.crossref.org/works/'+doi,headers={'User-Agent':'HabitatAtlasSourceReview/1.0 (mailto:ahmed.eladawy@jamstec.go.jp)'},timeout=55);r.raise_for_status();m=r.json()['message']
 assert m['DOI'].lower()==doi.lower() and m['type']=='journal-article'
 parts=next(m[k]['date-parts'][0] for k in ['published-online','published','issued'] if k in m)
 published='-'.join(str(v) if i==0 else f'{v:02d}' for i,v in enumerate(parts));assert published<=TODAY,(doi,published)
 return {'doi':doi,'title':html.unescape(m['title'][0]).strip(),'titleAr':ar,'journal':html.unescape(m['container-title'][0]),'year':int(published[:4]),'published':published,'url':'https://doi.org/'+doi,'verified':TODAY,'crossrefType':m['type'],'authors':[' '.join([a.get('given',''),a.get('family','')]).strip() for a in m.get('author',[])],'topic':topic,'basins':[basin] if basin else [],'coverage':coverage(keys),'geographySource':'Named study area in the publisher title/abstract; bounds are a search area, not sampled sites.'}

def main():
 papers=json.loads((ROOT/'papers.json').read_text('utf8'));known={p['doi'].lower():p for p in papers['items']}
 def reviewed(row):
  doi,basin,topic,keys,ar=row;old=known.get(doi.lower())
  if old and old.get('verified')==TODAY:return {**old,'titleAr':ar,'basins':[basin] if basin else [],'topic':topic,'coverage':coverage(keys)}
  return metadata(row)
 with ThreadPoolExecutor(max_workers=2) as pool:
  additions=list(pool.map(reviewed,ADDITIONS))
 for item in additions:
  if item['doi'].lower() in known:known[item['doi'].lower()].update(item)
  else:papers['items'].append(item)
 tags={
 '10.1016/j.rsma.2023.102934':['philippines'],'10.1029/2021jc017792':['scs'],'10.1016/j.accre.2022.04.003':['scs'],
 '10.1038/s41598-024-65291-y':['northjapan'],'10.1029/2025jc023614':['seasia'],'10.3390/rs13193989':['nwpacific'],
 '10.1007/s10872-026-00787-x':['japan'],'10.1038/s41598-026-65095-2':['japan'],
 '10.1038/s41598-025-17669-9':['gulf','oman'],'10.1016/j.rsma.2026.105384':['gulf'],'10.5194/os-21-3241-2025':['gulf']}
 for p in papers['items']:
  if p['doi'].lower() in tags:p['coverage']=coverage(tags[p['doi'].lower()])
  p.setdefault('coverage',[])
 def verify_existing(p):
  r=requests.get('https://api.crossref.org/works/'+p['doi'],headers={'User-Agent':'HabitatAtlasSourceReview/1.0'},timeout=55);r.raise_for_status();m=r.json()['message'];assert m['DOI'].lower()==p['doi'].lower()
  parts=next(m[k]['date-parts'][0] for k in ['published-online','published','issued'] if k in m);published='-'.join(str(v) if i==0 else f'{v:02d}' for i,v in enumerate(parts));assert published<=TODAY
  p['published']=published;p['verified']=TODAY
 if '--check-all' in sys.argv:
  for p in papers['items']:
   if p.get('verified')==TODAY:continue
   try:verify_existing(p)
   except requests.HTTPError as error:
    if error.response.status_code==429:print('DOI service rate limit: retained the previous check dates.');break
    raise
   time.sleep(1)
 papers['checked']=min(p['verified'] for p in papers['items'])
 papers['geographyChecked']=TODAY
 news=json.loads((ROOT/'news.json').read_text('utf8'))
 ntag={'jamstec-eastasia-heat-2023':['northjapan','japan'],'jamstec-kuroshio-rain':['kuroshio'],'kaust-microbial-2026':['central'],'kaust-reefs-2026':['central'],'nyuad-stress-2026':['uae','oman'],'gulf-drivers-2025':['gulf'],'japan-variability-2026':['japan'],'japan-bleaching-2026':['japan']}
 for n in news['items']:n['coverage']=coverage(ntag.get(n['id'],[]))
 fresh=[
  {'id':'nyuad-bacteria-20261027','date':'2026-10-27','source':'NYU Abu Dhabi','title':'Coral-associated bacteria help Gulf corals withstand heat','titleAr':'بكتيريا مرتبطة بالمرجان تساعد مرجان الخليج على تحمل الحرارة','summary':'Researchers studying Arabian Gulf corals, including colonies near Saadiyat Island, report a bacterial contribution to the coral heat-stress response.','summaryAr':'تتناول دراسة لمرجان الخليج، بما فيه مستعمرات قرب جزيرة السعديات، دور البكتيريا في استجابة المرجان للإجهاد الحراري.','url':'https://nyuad.nyu.edu/en/news/latest-news/science-and-technology/2026/october/nyuad-study-coral-bacteria-heat.html','basins':['gulf'],'coverage':coverage(['abudhabi'])},
  {'id':'nyuad-drivers-20251229','date':'2025-12-29','source':'NYU Abu Dhabi','title':'Wind patterns behind extreme summer heat in the Gulf','titleAr':'أنماط الرياح وراء حرارة الصيف الشديدة في الخليج','summary':'A Gulf study examines how weaker Shamal winds and a stronger summer monsoon contribute to unusually warm summers.','summaryAr':'تبحث دراسة للخليج دور ضعف رياح الشمال واشتداد الرياح الموسمية الصيفية في ارتفاع حرارة البحر.','url':'https://nyuad.nyu.edu/en/news/latest-news/science-and-technology/2025/december/nyuad-scientists-identify-heatwave-trigger.html','basins':['gulf'],'coverage':coverage(['gulf'])}
 ]
 summaries={
  '10.3390/su18147456':('Egyptian Red Sea reefs under climate and coastal pressures','الشعاب المصرية تحت الضغوط المناخية والساحلية','A multi-decadal study examines warming and human pressures on reef condition along the Egyptian Red Sea coast.','تبحث دراسة متعددة العقود الاحترار والضغوط البشرية على حالة الشعاب على الساحل المصري للبحر الأحمر.'),
  '10.1029/2025JC023614':('Heatwaves deepen and lengthen across Southeast Asia','امتداد الموجات الحارة إلى أعماق ومدد أكبر عبر جنوب شرق آسيا','A regional study examines the frequency, duration and vertical structure of marine heatwaves across Southeast Asia and the tropical western Pacific.','تبحث دراسة إقليمية تكرار الموجات البحرية الحارة ومدتها وبنيتها الرأسية عبر جنوب شرق آسيا وغرب المحيط الهادئ المداري.'),
  '10.1016/j.scitotenv.2025.180463':('Gulf of Aqaba corals examined through four warm summers','دراسة مرجان خليج العقبة خلال أربعة أصياف حارة','A study follows coral responses through successive marine heatwaves in the Gulf of Aqaba.','تتابع دراسة استجابة المرجان للموجات البحرية الحارة المتعاقبة في خليج العقبة.'),
  '10.21608/ejabf.2025.451010':('Coral recovery after bleaching on the Egyptian Red Sea coast','تعافي المرجان بعد الابيضاض على الساحل المصري للبحر الأحمر','Field assessments examine coral recovery and mortality after the 2023 bleaching event in southern Egyptian reefs.','تبحث مسوحات ميدانية التعافي والنفوق بعد ابيضاض 2023 في الشعاب المصرية الجنوبية.'),
  '10.1016/j.wace.2025.100771':('Subsurface heat and bleaching in the southern Red Sea','الحرارة تحت السطح وابيضاض المرجان في جنوب البحر الأحمر','A regional ocean study examines subsurface warming and remote forcing during southern Red Sea bleaching events.','تبحث دراسة محيطية إقليمية الاحترار تحت السطح والتأثيرات البعيدة خلال ابيضاض المرجان في جنوب البحر الأحمر.'),
  '10.3390/d18100618':('Jeju coral bleaching differs between depths and taxa','اختلاف ابيضاض مرجان جيجو باختلاف العمق والنوع','Observations document differing coral bleaching responses during the 2024 heatwave around Jeju Island.','توثق رصدات اختلاف استجابة المرجان للابيضاض خلال موجة 2024 قرب جزيرة جيجو.'),
  '10.1029/2025JC023755':('Persistent heatwaves and plankton changes in the South China Sea','استمرار الموجات الحارة وتغير العوالق في بحر الصين الجنوبي','A new study examines the links between heatwave duration, phytoplankton size and marine productivity.','تبحث دراسة الروابط بين مدة الموجات الحارة وحجم العوالق النباتية والإنتاجية البحرية.'),
  '10.3390/rs17061048':('Thermal stress and acidification in Philippine coral environments','الإجهاد الحراري والتحمض في بيئات المرجان بالفلبين','Satellite and reanalysis records are used to examine heatwaves and acidification affecting Philippine coral environments.','تُستخدم بيانات الأقمار الصناعية وإعادة التحليل لدراسة الموجات الحارة والتحمض في بيئات المرجان بالفلبين.'),
  '10.1038/s41598-026-43302-4':('A survey of corals around southern Iranian islands','مسح للمرجان حول جزر جنوب إيران','A regional study reports coral health and distribution around three islands in the southern Iranian Gulf.','تتناول دراسة إقليمية صحة المرجان وتوزيعه حول ثلاث جزر قبالة جنوب إيران.'),
  '10.1007/s00338-026-02922-y':('Heat stress and coral disease on Abu Dhabi reefs','الإجهاد الحراري وأمراض المرجان في شعاب أبوظبي','Long-term observations examine coral disease following marked summer heat stress and bleaching.','تبحث رصدات طويلة الأجل أمراض المرجان بعد الإجهاد الحراري الصيفي والابيضاض.'),
  '10.1126/sciadv.adz4647':('Why northwestern Pacific heatwaves can persist','لماذا قد تستمر الموجات الحارة في شمال غرب المحيط الهادئ','A study examines cross-basin atmospheric links associated with persistent northwestern Pacific marine heatwaves.','تبحث دراسة روابط جوية بين الأحواض ترتبط باستمرار الموجات البحرية الحارة في شمال غرب المحيط الهادئ.')}
 for p in additions:
  if p['doi'] not in summaries:continue
  title,ar,summary,summary_ar=summaries[p['doi']]
  fresh.append({'id':'research-'+p['doi'].split('/')[-1],'date':p['published'],'source':p['journal'],'kind':'Research update','title':title,'titleAr':ar,'summary':summary,'summaryAr':summary_ar,'url':p['url'],'basins':p['basins'],'coverage':p['coverage']})
 index={n['id']:n for n in news['items']}
 for n in fresh:
  n['checked']=TODAY
  if n['id'] in index:index[n['id']].update(n)
  else:news['items'].append(n)
 news['geographyChecked']=TODAY;news['refreshed']=TODAY
 for name,obj in [('papers',papers),('news',news)]:
  (ROOT/(name+'.json')).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print('Regional catalogue:',len(papers['items']),'papers;',len(news['items']),'news/research updates; reviewed area bounds',TODAY)

if __name__=='__main__':main()
