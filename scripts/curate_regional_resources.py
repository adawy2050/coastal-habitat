"""One-time regional catalogue curation; subsequent checks preserve geography."""
from pathlib import Path
import json, html
import requests

ROOT=Path(__file__).resolve().parents[1]/'dist/content'

def main():
    papers=json.loads((ROOT/'papers.json').read_text('utf8'))
    for i,p in enumerate(papers['items']):
        p.setdefault('basins',['redsea'] if i<2 else ['gulf'] if i<4 else ['eastasia'] if i>=20 else [])
        p['journal']=html.unescape(p['journal'])
    additions=[
      ('10.1007/s10872-026-00787-x','eastasia','regional','الموجات الحارة حول اليابان وعلاقتها بتقلب حرارة سطح البحر'),
      ('10.1038/s41598-026-65095-2','eastasia','habitats','ابيضاض المرجان في اليابان تحت إجهاد حراري بحري قياسي'),
      ('10.5194/os-21-3241-2025','gulf','regional','المحركات المحلية والبعيدة لحرارة سطح البحر الصيفية الشديدة في الخليج العربي')]
    known={p['doi'].lower() for p in papers['items']}
    for doi,basin,topic,ar in additions:
        if doi.lower() in known:continue
        r=requests.get('https://api.crossref.org/works/'+doi,timeout=40);r.raise_for_status();m=r.json()['message']
        assert m['DOI'].lower()==doi.lower()
        papers['items'].append({'doi':doi,'title':html.unescape(m['title'][0]),
            'journal':html.unescape(m['container-title'][0]),'year':m.get('published',m['issued'])['date-parts'][0][0],
            'authors':[' '.join([a.get('given',''),a.get('family','')]).strip() for a in m.get('author',[])],
            'url':'https://doi.org/'+doi,'verified':'2026-10-22','crossrefType':m['type'],
            'titleAr':ar,'topic':topic,'basins':[basin]})
    news=json.loads((ROOT/'news.json').read_text('utf8'))
    for p in news['items']:p.setdefault('basins',['eastasia'] if p['id'].startswith('jamstec-') else [])
    rows=[
      ('kaust-microbial-2026','redsea','2026-09-13','KAUST','Microbial therapies tested on heat-stressed Red Sea corals','اختبار علاجات ميكروبية لمرجان البحر الأحمر المتأثر بالحرارة','A field study examined live and inactivated bacterial treatments during a central Red Sea heatwave.','اختبرت دراسة ميدانية بكتيريا حية ومعطلة خلال موجة حارة في وسط البحر الأحمر.','https://www.kaust.edu.sa/en/news/microbial-therapies-improve-heat-stressed-coral-health'),
      ('kaust-reefs-2026','redsea','2026-04-16','KAUST Discovery','Testing ways to support Red Sea reefs in warmer seas','اختبار وسائل لدعم شعاب البحر الأحمر مع ارتفاع حرارة البحر','KAUST reviews field research on coral heat tolerance and reef restoration.','تستعرض كاوست دراسات ميدانية لتحمل المرجان للحرارة واستعادة الشعاب.','https://discovery.kaust.edu.sa/en/article/26756/buying-time-for-coral-reefs/'),
      ('nyuad-stress-2026','gulf','2026-01-28','NYU Abu Dhabi','UAE-wide coral heat-tolerance tests','اختبارات تحمل المرجان للحرارة على امتداد الإمارات','Researchers tested corals on both UAE coasts to compare their response to extreme heat.','اختبر الباحثون المرجان على ساحلي الإمارات لمقارنة استجابته للحرارة الشديدة.','https://nyuad.nyu.edu/en/news/latest-news/science-and-technology/2026/january/nyuad-researchers-conduct-testing-identify-heat-resistant-corals.html'),
      ('gulf-drivers-2025','gulf','2025-12-02','Ocean Science','Local and remote drivers of extreme Gulf summer temperatures','المحركات المحلية والبعيدة لحرارة الصيف الشديدة في الخليج','A published study examines the circulation and climate patterns linked to extreme Gulf sea temperatures.','تفحص دراسة منشورة الدوران وأنماط المناخ المرتبطة بحرارة البحر الشديدة في الخليج.','https://os.copernicus.org/articles/21/3241/2025/'),
      ('japan-variability-2026','eastasia','2026-05-25','Ehime University','Warming and ocean variability shape heatwaves around Japan','الاحترار وتقلب المحيط يؤثران في موجات اليابان البحرية','Researchers examined four decades of heatwaves and their links to North Pacific temperature patterns.','درس الباحثون أربعة عقود من الموجات الحارة وصلتها بأنماط حرارة شمال المحيط الهادئ.','https://www.cmes.ehime-u.ac.jp/newsen/marine-heatwaves-around-japan-the-role-of-global-warming-and-oceanic-variability/'),
      ('japan-bleaching-2026','eastasia','2026-08-25','Scientific Reports','Coral bleaching across subtropical and temperate Japan','ابيضاض المرجان في اليابان شبه المدارية والمعتدلة','A study documents the response of Japanese coral communities to the record marine heat of 2024.','توثق دراسة استجابة تجمعات المرجان اليابانية لحرارة البحر القياسية في 2024.','https://www.nature.com/articles/s41598-026-65095-2')]
    known={p['id'] for p in news['items']}
    for id,basin,date,source,title,ar,summary,sar,url in rows:
        if id not in known:news['items'].append(dict(id=id,basins=[basin],date=date,source=source,title=title,titleAr=ar,summary=summary,summaryAr=sar,url=url,checked='2026-10-22'))
    for name,data in [('papers',papers),('news',news)]:
        data['areaFiltering']='Regional items follow the map selection. Global references remain in the editable catalogue.'
        (ROOT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
