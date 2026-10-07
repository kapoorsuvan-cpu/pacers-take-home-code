"""Download the exact public 2024-25 inputs used in the analysis."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('--data',type=Path,default=Path('data'));a=P.parse_args();a.data.mkdir(parents=True,exist_ok=True)
manifest=json.load(open(Path(__file__).with_name('data_manifest.json')))
for entry in manifest['files']:
 target=a.data/entry['file']
 if not target.exists():
  print('Downloading',entry['file']);urllib.request.urlretrieve(entry['url'],target)
 digest=hashlib.sha256(target.read_bytes()).hexdigest()
 if digest!=entry['sha256']:raise ValueError(f'Checksum mismatch: {target}')
 print('Verified',target.name)
