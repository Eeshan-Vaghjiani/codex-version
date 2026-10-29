"""Restore the public CC-BY DDXPlus v15 files locally; never add raw data to git."""
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.prepare_data import process_split, respiratory_conditions
ARTICLE = 'https://api.figshare.com/v2/articles/20043374/versions/15'
NAMES = {'release_evidences.json', 'release_conditions.json',
         'release_train_patients.zip', 'release_validate_patients.zip', 'release_test_patients.zip'}


def md5(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'md5').hexdigest()


def download(info, folder):
    target = folder / info['name']
    if target.exists():
        if target.stat().st_size != info['size'] or md5(target) != info['computed_md5']:
            raise ValueError(f'Local file differs from official source; not overwriting {target.name}')
        return target
    with tempfile.NamedTemporaryFile(dir=folder, delete=False) as temporary:
        pending = Path(temporary.name)
        try:
            with urlopen(info['download_url'], timeout=120) as response:
                shutil.copyfileobj(response, temporary)
        except BaseException:
            temporary.close()
            pending.unlink(missing_ok=True)
            raise
    try:
        if pending.stat().st_size != info['size'] or md5(pending) != info['computed_md5']:
            raise ValueError(f'Official file checksum mismatch: {target.name}')
        pending.replace(target)
    finally:
        pending.unlink(missing_ok=True)
    return target


def unpack(archive, folder):
    name = archive.stem
    target = folder / name
    with ZipFile(archive) as bundle:
        # Copy one expected member to a fixed path, never extract archive paths.
        members = [item for item in bundle.infolist() if item.filename == name and not item.is_dir()]
        if len(members) != 1:
            raise ValueError(f'Unexpected DDXPlus archive layout: {archive.name}')
        if target.exists():
            if target.stat().st_size != members[0].file_size:
                raise ValueError(f'Local extracted file differs; not overwriting {name}')
            return target
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as temporary:
            pending = Path(temporary.name)
            try:
                with bundle.open(members[0]) as source:
                    shutil.copyfileobj(source, temporary)
            except BaseException:
                temporary.close()
                pending.unlink(missing_ok=True)
                raise
        pending.replace(target)
    return target


def main():
    folder = ROOT / 'data/raw'
    folder.mkdir(parents=True, exist_ok=True)
    with urlopen(ARTICLE, timeout=60) as response:
        article = json.load(response)
    files = [item for item in article['files'] if item['name'] in NAMES]
    if {item['name'] for item in files} != NAMES:
        raise ValueError('Pinned DDXPlus release is incomplete')
    for info in files:
        print('Restoring', info['name'], flush=True)
        path = download(info, folder)
        if path.suffix == '.zip':
            unpack(path, folder)
    manifest = {'source': ARTICLE, 'citation': article['citation'], 'license': article['license'],
                'clinical_validation': False, 'files': [
                    {key: item[key] for key in ('name', 'size', 'computed_md5', 'download_url')} for item in files]}
    (folder / 'download_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
    # Official condition metadata uses French keys, while patient labels are
    # English. Re-key only for scope verification; never rewrite source files.
    conditions = json.loads((folder / 'release_conditions.json').read_text(encoding='utf8'))
    conditions = {item.get('cond-name-eng', name): item for name, item in conditions.items()}
    classes = json.loads((ROOT / 'models/disease_classes.json').read_text())
    features = json.loads((ROOT / 'models/model_features.json').read_text())
    if respiratory_conditions(conditions) != classes:
        raise ValueError('Official respiratory scope differs from the frozen model')
    evidences = json.loads((folder / 'release_evidences.json').read_text(encoding='utf8'))
    output = ROOT / 'data/processed'
    output.mkdir(parents=True, exist_ok=True)
    for split in ('train', 'validate', 'test'):
        target = output / f'{split}.csv'
        if target.exists():
            continue
        # Reconstruct all 198 frozen source inputs, not the historical 2,000-row
        # V2 sample. Leave tracked feature/class metadata untouched.
        with tempfile.TemporaryDirectory(dir=output) as staging:
            process_split(str(folder), staging, split, classes, evidences, features, features[2:])
            (Path(staging) / target.name).replace(target)
    print('Official files and frozen-input cohorts restored locally; no training or threshold fitting performed.', flush=True)


if __name__ == '__main__':
    main()
