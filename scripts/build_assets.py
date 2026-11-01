"""Assemble the build-free portal's source modules and separate asset manifest.

Original scientific files and their manifest are never rewritten. Generated
bundles reduce startup requests; all source modules remain editable in dist/.
"""
import hashlib
import json
from pathlib import Path
import re
import argparse
import subprocess

ROOT=Path(__file__).resolve().parents[1]/'dist'
SCRIPTS=['i18n.js','ui-strings.js','gallery.js','stats.js','app.js','point-report.js','tour.js','detail.js','exploration.js','scenarios.js','organisation.js','resources.js','identity.js','world.js','scientific.js','point-window.js','shoreline.js','observed2026.js','map-layers.js','external-forecasts.js','point-timeline.js','outlook-combinations.js','refresh.js']
STYLES=['styles.css','atlas.css','point.css','portal.css','upgrade.css','world.css','scientific.css','point-window.css','refresh.css']


def write_utf8(path, text):
    # Path.write_text(newline=...) requires Python 3.10; the data server uses 3.9.
    with path.open('w', encoding='utf8', newline='\n') as stream:
        stream.write(text)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--tracked-only',action='store_true',help='Package only files currently staged/tracked during an incremental release');args=parser.parse_args()
    tracked=set(subprocess.check_output(['git','ls-files','--cached','-z'],cwd=ROOT.parent).decode('utf8').split('\0')) if args.tracked_only else None
    fonts=(ROOT/'fonts/fonts.css').read_text().replace("url('./","url('./fonts/")
    css=fonts+'\n'+'\n'.join((ROOT/name).read_text(encoding='utf8') for name in STYLES)
    css=re.sub(r'/\*.*?\*/','',css,flags=re.S)
    css=re.sub(r'\s+',' ',css).strip()
    write_utf8(ROOT/'interface.css', css)
    write_utf8(ROOT/'language.js', '\n;\n'.join((ROOT/name).read_text(encoding='utf8') for name in ['locales.js',*SCRIPTS[:2]]))
    js='\n;\n'.join((ROOT/name).read_text(encoding='utf8') for name in SCRIPTS[2:])
    write_utf8(ROOT/'interface.js', js)
    records={}
    for path in sorted(ROOT.rglob('*')):
        if tracked is not None and 'dist/'+path.relative_to(ROOT).as_posix() not in tracked:continue
        if not path.is_file() or path.relative_to(ROOT).parts[0]=='data' or path.name=='asset-manifest.json' or path.relative_to(ROOT).as_posix() in ['status/current.json','status/photos.json','observed2026/status.json']:continue
        raw=path.read_bytes();records[path.relative_to(ROOT).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    write_utf8(ROOT/'asset-manifest.json', json.dumps({'scope':'Presentation assets and separate observed display records; study files retain data/manifest.json','files':records},separators=(',',':')))
    print(f'Built interface bundles; {len(records):,} assets with SHA-256 hashes.')


if __name__=='__main__':main()
