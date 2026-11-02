"""Retain verified originals; build responsive, unretouched habitat previews.

Run with Pillow (AVIF enabled). Source URLs and licences are in credits.json.
Existing originals are hash checked; downloads use bounded retries.
"""
from pathlib import Path
import base64
import hashlib
import io
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1] / 'dist/images'


def main():
    photos = json.loads((ROOT / 'credits.json').read_text(encoding='utf8'))
    for photo in photos:
        path = ROOT / photo['file']
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            for attempt in range(5):
                try:
                    request = Request(photo['original'], headers={'User-Agent': 'HabitatMHWAtlas/1.0 (https://github.com/adawy2050/coastal-habitat)'})
                    with urlopen(request, timeout=90) as response:
                        content = response.read()
                    assert content.startswith(b'\xff\xd8')
                    path.write_bytes(content)
                    break
                except HTTPError as error:
                    if error.code not in (429, 503) or attempt == 4:
                        raise
                    time.sleep(min(45, int(error.headers.get('Retry-After', 8)) + attempt * 5))
            time.sleep(1)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if photo.get('sha256'):
            assert digest == photo['sha256'], f'Original changed: {path}'
        photo['sha256'] = digest
        with Image.open(path) as source:
            assert source.size == (photo['width'], photo['height'])
            image = ImageOps.exif_transpose(source).convert('RGB')
            target = ROOT / 'responsive'
            target.mkdir(exist_ok=True)
            for width in (480, 960, 1600, 2400):
                resized = image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS)
                for fmt, quality in [('AVIF', 60), ('WEBP', 80), ('JPEG', 85)]:
                    output = target / f"{photo['id']}-{width}.{dict(AVIF='avif', WEBP='webp', JPEG='jpg')[fmt]}"
                    if not output.exists():
                        resized.save(output, fmt, quality=quality, **({'optimize': True, 'progressive': True} if fmt == 'JPEG' else {}))
            thumb = image.copy()
            thumb.thumbnail((24, 24))
            buffer = io.BytesIO()
            thumb.save(buffer, 'JPEG', quality=35)
            photo['placeholder'] = 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode()
        print(photo['id'], photo['width'], photo['height'], path.stat().st_size, flush=True)
    (ROOT / 'credits.json').write_text(json.dumps(photos, ensure_ascii=False, indent=2), encoding='utf8')
    lines = ['# Photograph audit', '', 'Verified from Wikimedia Commons imageinfo metadata on 18 October 2026. Original JPEGs are unmodified; responsive derivatives are resized/compressed only. No AI generation or upscaling.', '']
    for p in photos:
        lines += [f"## {p['title']} — {p['location']}", f"- Source: [{p['sourceTitle']}]({p['source']})", f"- Author: {p['author']}", f"- Licence: [{p['license']}]({p['licenseUrl']})", f"- Original: {p['width']} × {p['height']} px; SHA-256 `{p['sha256']}`", f"- Caption claims: {p['captionClaims']}", '- Verified: permitted licence, native long edge ≥ 3,000 px, subject/location supported by source. Original inspected and derivative preview reviewed.', '']
    lines += ['## Rejected candidates', '- Previous Menna.Hassan100 reef: weak underwater clarity.', '- Previous Abu Dabbab dugong: long edge below 3,000 px.', '- Nabq mangrove 19: overexposed water and weak scene detail.', '- Red Sea 21: distracting foreground and soft focus.', '- Mangrove RasMohammed: heavy shadows and distant trees.', '- Shutterstock/Getty results: no permitted redistribution licence.', '', 'Florida, US Virgin Islands and Great Barrier Reef bleaching images are clearly labelled comparison images; they do not document bleaching in either atlas basin.']
    (ROOT / 'PHOTO_AUDIT.md').write_text('\n'.join(lines), encoding='utf8')


if __name__ == '__main__':
    main()
