"""Apply the coverage-neutral atlas shell and keep existing control IDs."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]/'dist'
def main():
    p=ROOT/'index.html';s=p.read_text('utf8')
    if 'Coastal Habitat Heatwave Atlas' in s:print('UI migration already applied');return
    s=s.replace('Red Sea & Arabian Gulf Habitat Heatwave Atlas','Coastal Habitat Heatwave Atlas').replace('RED SEA & ARABIAN GULF HABITAT HEATWAVE ATLAS','COASTAL HABITAT HEATWAVE ATLAS').replace('RED SEA & ARABIAN GULF','RED SEA · ARABIAN GULF · EAST ASIA')
    s=re.sub(r'<meta name="description" content="[^"]+">','<meta name="description" content="Marine heatwave maps and habitat histories across the Red Sea, Arabian Gulf, East Asia and the western Pacific. Explore coral, seagrass, mangrove and kelp cells, climate records and seasonal outlooks.">',s)
    s=s.replace('20261018-upgrade','20261018-eastasia')
    s=s.replace('Both study areas','All study areas').replace('<option value="gulf">Arabian Gulf & Gulf of Oman</option>','<option value="gulf">Arabian Gulf & Gulf of Oman</option><option value="eastasia">East Asia & western Pacific</option>')
    s=s.replace('<span class="habitat-dot mangrove"></span>Mangrove</label></fieldset>','<span class="habitat-dot mangrove"></span>Mangrove</label><label><input type="checkbox" name="habitat" value="8" checked><span class="habitat-dot kelp_macroalgae"></span>Kelp &amp; seaweeds</label></fieldset>')
    s=s.replace('Compare annual exposure at selected habitat cells.','Follow annual and monthly heatwaves, daily water temperature and changes between years.')
    s=s.replace('Marine heatwave exposure at coral, seagrass and mangrove habitat cells across the Red Sea, Gulf of Aden, Arabian Gulf and Gulf of Oman.','Marine heatwave records for coral reefs, seagrass, mangroves and kelp across the Red Sea, Arabian Gulf, East Asia and western Pacific.')
    s=s.replace('Red Sea and Arabian Gulf</option>','Regional studies</option>')
    s=s.replace('Red Sea and Arabian Gulf habitats','Coastal habitats across the atlas').replace('RED SEA & GULF HABITATS','COASTAL HABITATS').replace('Reefs, seagrass and mangroves','Reefs, seagrass, mangroves and kelp')
    s=s.replace('<option value="gulf">Arabian Gulf & Gulf of Oman</option><option value="representative">','<option value="gulf">Arabian Gulf & Gulf of Oman</option><option value="eastasia">East Asia & western Pacific</option><option value="representative">')
    s=s.replace('Original photographs from both study areas; native-resolution originals and source credits.','Photographs from across the atlas, with source locations, credits and full-resolution originals.')
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/'app.js';s=p.read_text('utf8').replace("20261018-gulf","20261018-eastasia")
    s=s.replace('habitats:7, pixel:0','habitats:15, selection:null, pixel:0').replace('state.habitats=7;','state.habitats=15;state.selection=null;')
    s=s.replace("pointBasin(pixels[i]).id==='gulf'?'gulf_':''","pointBasin(pixels[i]).id==='redsea'?'':pointBasin(pixels[i]).id+'_'")
    s=s.replace("return (p[2]&state.habitats)!==0", "return (!state.selection||(p[0]>=state.selection[0]&&p[0]<=state.selection[2]&&p[1]>=state.selection[1]&&p[1]<=state.selection[3]))&&(p[2]&state.habitats)!==0")
    s=s.replace('coverageMeta.tiles[habitat]);','coverageMeta.tiles[habitat]||[]);')
    s=s.replace("detail:{basin:pointBasin(p).id,habitats:p[2]}","detail:{basin:pointBasin(p).id,habitats:p[2],latitude:p[1],longitude:p[0],pixel:index}")
    s=s.replace("window.AtlasLanguage?.current==='ar'","window.AtlasLanguage?.current!=='en'")
    s=s.replace("$('basin').onchange=()=>{state.basin=", "$('basin').onchange=()=>{state.selection=null;state.basin=")
    s=s.replace("redraw(){pixelLayer.draw();},", "redraw(){pixelLayer.draw();},\n    selectBounds(bounds){state.selection=bounds?[bounds.getWest(),bounds.getSouth(),bounds.getEast(),bounds.getNorth()]:null;filterChanged();window.dispatchEvent(new Event('atlasselectionchange'));},")
    s=s.replace("const pair=document.createElement('div');pair.className='probability-pair';pair.innerHTML=", "e.dataset.outlookIndex=rows.indexOf(t);const pair=document.createElement('div');pair.className='probability-pair';pair.innerHTML=")
    s=s.replace("if(!rows.length)$('outlookCards')", "window.dispatchEvent(new CustomEvent('atlasoutlookchange',{detail:{rows}}));\n    if(!rows.length)$('outlookCards')")
    p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/'boot.js';s=p.read_text('utf8').replace('20261018-upgrade','20261018-eastasia');p.write_text(s,encoding='utf8',newline='\n')
    for name in ['detail.js','exploration.js','identity.js','scenarios.js']:
        p=ROOT/name;s=p.read_text('utf8').replace("AtlasLanguage.current==='ar'?AtlasLanguage.translate(s):s","AtlasLanguage.current!=='en'?AtlasLanguage.translate(s):s");p.write_text(s,encoding='utf8',newline='\n')
    p=ROOT/'exploration.js';s=p.read_text('utf8').replace("selection(bounds);}})","selection(bounds);window.dispatchEvent(new CustomEvent('atlasboxdrawn',{detail:{bounds}}));}})")
    # Keep the existing distribution view and add a true map filter to its selection.
    s=s.replace("async function selection(bounds){", "async function selection(bounds){AtlasUI.selectBounds(bounds);")
    p.write_text(s,encoding='utf8',newline='\n')
    print('Coverage-neutral UI ready')
if __name__=='__main__':main()
