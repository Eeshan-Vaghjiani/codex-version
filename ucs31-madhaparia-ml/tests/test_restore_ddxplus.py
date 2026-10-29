import hashlib
from io import BytesIO
from zipfile import ZipFile

import pytest
from scripts import restore_ddxplus as restore


def test_download_checks_checksum_and_preserves_local_work(tmp_path, monkeypatch):
    data = b'official test fixture'
    monkeypatch.setattr(restore, 'urlopen', lambda *args, **kwargs: BytesIO(data))
    info = {'name': 'release_evidences.json', 'size': len(data),
            'computed_md5': hashlib.md5(data).hexdigest(), 'download_url': 'https://example.invalid/fixture'}
    target = restore.download(info, tmp_path)
    assert target.read_bytes() == data
    assert restore.download(info, tmp_path) == target
    target.write_bytes(b'user work')
    with pytest.raises(ValueError, match='not overwriting'):
        restore.download(info, tmp_path)
    assert target.read_bytes() == b'user work'


def test_corrupt_download_never_becomes_source_data(tmp_path, monkeypatch):
    monkeypatch.setattr(restore, 'urlopen', lambda *args, **kwargs: BytesIO(b'bad'))
    with pytest.raises(ValueError, match='checksum'):
        restore.download({'name': 'source.zip', 'size': 3, 'computed_md5': '0' * 32,
                          'download_url': 'https://example.invalid/fixture'}, tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_archive_only_copies_the_expected_member(tmp_path):
    archive = tmp_path / 'release_train_patients.zip'
    with ZipFile(archive, 'w') as bundle:
        bundle.writestr('release_train_patients', 'fixture')
    assert restore.unpack(archive, tmp_path).read_text() == 'fixture'


def test_unexpected_archive_path_is_rejected(tmp_path):
    archive = tmp_path / 'release_train_patients.zip'
    with ZipFile(archive, 'w') as bundle:
        bundle.writestr('../release_train_patients', 'unsafe')
    with pytest.raises(ValueError, match='layout'):
        restore.unpack(archive, tmp_path)
