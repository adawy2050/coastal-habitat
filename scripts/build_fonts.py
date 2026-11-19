"""Self-host OFL Google Fonts as compact WOFF2 subsets, retaining shaping."""
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT=Path(__file__).resolve().parents[1]
FONTS=[('inter','Inter[opsz,wght].ttf','Inter','U+0020-024F,U+2000-206F'),('sourceserif4','SourceSerif4[opsz,wght].ttf','Source Serif 4','U+0020-024F,U+2000-206F'),('notosansarabic','NotoSansArabic[wdth,wght].ttf','Noto Sans Arabic','U+0020-024F,U+0600-06FF,U+0750-077F,U+08A0-08FF,U+2000-206F,U+FB50-FDFF,U+FE70-FEFF')]


def main():
    out=ROOT/'dist/fonts';out.mkdir(exist_ok=True);rules=[]
    for folder,filename,name,unicodes in FONTS:
        base='https://raw.githubusercontent.com/google/fonts/main/ofl/'+folder+'/'
        original=ROOT/'_cache'/filename
        if not original.exists():original.write_bytes(urlopen(base+quote(filename)).read())
        (out/(folder+'-OFL.txt')).write_bytes(urlopen(base+'OFL.txt').read())
        font=TTFont(original);options=subset.Options();options.layout_features=['*'];options.flavor='woff2';sub=subset.Subsetter(options=options);sub.populate(unicodes=subset.parse_unicodes(unicodes));sub.subset(font);axes={a.axisTag:((400,700) if a.axisTag=='wght' else a.defaultValue) for a in font['fvar'].axes};instantiateVariableFont(font,axes,inplace=True);font.flavor='woff2';font.save(out/(folder+'.woff2'))
        rules.append(f"@font-face{{font-family:'{name}';font-style:normal;font-weight:400 700;font-display:swap;src:url('./{folder}.woff2') format('woff2')}}")
        print(folder,(out/(folder+'.woff2')).stat().st_size)
    (out/'fonts.css').write_text('\n'.join(rules))
    (out/'README.md').write_text('Fonts sourced from https://github.com/google/fonts/tree/main/ofl/ on 18 October 2026. Inter, Source Serif 4 and Noto Sans Arabic use SIL Open Font License 1.1; see individual OFL files. WOFF2 subsets retain layout shaping and variable weights. Rebuild with python scripts/build_fonts.py.\n')


if __name__=='__main__':main()
