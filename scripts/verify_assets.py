"""Verify every presentation/display asset without altering study hashes."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'dist'
manifest=json.loads((ROOT/'asset-manifest.json').read_text(encoding='utf8'))
for name,record in manifest['files'].items():
    raw=(ROOT/name).read_bytes()
    assert len(raw)==record['bytes'] and hashlib.sha256(raw).hexdigest()==record['sha256'],name
print(f"PASS: {len(manifest['files']):,} presentation/display assets match the separate manifest.")
