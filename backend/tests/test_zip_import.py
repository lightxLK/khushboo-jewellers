import os
import zipfile
import pytest
from tasks import validate_and_index_zip


def _make_zip(path, entries):
    """entries: list of (arcname, content_bytes)"""
    with zipfile.ZipFile(path, 'w') as zf:
        for arcname, content in entries:
            zf.writestr(arcname, content)


def test_valid_zip_indexes_images_by_code(tmp_path):
    zip_path = tmp_path / 'images.zip'
    _make_zip(zip_path, [
        ('day1/ABC123.jpg', b'fake-jpeg-bytes'),
        ('day2/subfolder/XYZ999.PNG', b'fake-png-bytes'),
    ])

    index, extraction_dir = validate_and_index_zip(str(zip_path))

    assert set(index.keys()) == {'ABC123', 'XYZ999'}
    assert os.path.isfile(index['ABC123'])
    assert os.path.isfile(index['XYZ999'])
    assert os.path.isdir(extraction_dir)


def test_non_image_files_are_skipped_not_errors(tmp_path):
    zip_path = tmp_path / 'images.zip'
    _make_zip(zip_path, [
        ('IMG1.jpg', b'fake-jpeg-bytes'),
        ('.DS_Store', b'junk'),
        ('notes.txt', b'not an image'),
    ])

    index, extraction_dir = validate_and_index_zip(str(zip_path))

    assert set(index.keys()) == {'IMG1'}


def test_duplicate_image_codes_raise_value_error(tmp_path):
    zip_path = tmp_path / 'images.zip'
    _make_zip(zip_path, [
        ('ABC.jpg', b'fake-jpeg-bytes'),
        ('ABC.png', b'fake-png-bytes'),
    ])

    with pytest.raises(ValueError, match='ABC'):
        validate_and_index_zip(str(zip_path))


def test_path_traversal_entry_is_rejected(tmp_path):
    zip_path = tmp_path / 'evil.zip'
    _make_zip(zip_path, [
        ('../../evil.jpg', b'fake-jpeg-bytes'),
    ])

    with pytest.raises(ValueError, match='path traversal|outside'):
        validate_and_index_zip(str(zip_path))


def test_encrypted_entry_is_rejected(tmp_path):
    import struct
    zip_path = tmp_path / 'encrypted.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        info = zipfile.ZipInfo('SECRET.jpg')
        zf.writestr(info, b'fake-jpeg-bytes')

    # Manually set encryption flag in ZIP file bytes since stdlib doesn't support writing encrypted zips
    with open(zip_path, 'r+b') as f:
        data = bytearray(f.read())

    # Set encryption bit in local file header (bytes 6-7)
    offset = 0
    while offset < len(data):
        if data[offset:offset+4] == b'PK\x03\x04':
            flag_word = struct.unpack_from('<H', data, offset+6)[0]
            flag_word |= 0x1
            struct.pack_into('<H', data, offset+6, flag_word)
            break
        offset += 1

    # Set encryption bit in central directory header (bytes 8-9)
    offset = 0
    while offset < len(data):
        if data[offset:offset+4] == b'PK\x01\x02':
            flag_word = struct.unpack_from('<H', data, offset+8)[0]
            flag_word |= 0x1
            struct.pack_into('<H', data, offset+8, flag_word)
            break
        offset += 1

    with open(zip_path, 'wb') as f:
        f.write(data)

    with pytest.raises(ValueError, match='encrypted'):
        validate_and_index_zip(str(zip_path))


def test_too_many_files_is_rejected(tmp_path, monkeypatch):
    import tasks
    monkeypatch.setattr(tasks, 'MAX_IMPORT_FILES', 2)
    zip_path = tmp_path / 'images.zip'
    _make_zip(zip_path, [
        ('A.jpg', b'x'), ('B.jpg', b'x'), ('C.jpg', b'x'),
    ])

    with pytest.raises(ValueError, match='files'):
        validate_and_index_zip(str(zip_path))


def test_total_size_over_limit_is_rejected(tmp_path, monkeypatch):
    import tasks
    monkeypatch.setattr(tasks, 'MAX_IMPORT_TOTAL_BYTES', 5)
    zip_path = tmp_path / 'images.zip'
    _make_zip(zip_path, [
        ('A.jpg', b'this-is-more-than-five-bytes'),
    ])

    with pytest.raises(ValueError, match='bytes'):
        validate_and_index_zip(str(zip_path))


def test_not_a_zip_file_is_rejected(tmp_path):
    fake_zip = tmp_path / 'not-a-zip.zip'
    fake_zip.write_bytes(b'this is definitely not a zip archive')

    with pytest.raises(ValueError, match='not a valid ZIP'):
        validate_and_index_zip(str(fake_zip))


def test_extraction_dir_is_cleaned_up_when_extraction_fails(tmp_path, monkeypatch):
    """A failure during zf.extractall()/indexing (not our own validation code)
    must still clean up the temp extraction dir instead of leaking it."""
    zip_path = tmp_path / 'images.zip'
    _make_zip(zip_path, [
        ('ABC123.jpg', b'fake-jpeg-bytes'),
    ])

    captured_dirs = []

    import tasks as tasks_module
    original_mkdtemp = tasks_module.tempfile.mkdtemp

    def spying_mkdtemp(*args, **kwargs):
        d = original_mkdtemp(*args, **kwargs)
        captured_dirs.append(d)
        return d

    def boom(self, *args, **kwargs):
        raise OSError("simulated extraction failure")

    monkeypatch.setattr(tasks_module.tempfile, 'mkdtemp', spying_mkdtemp)
    monkeypatch.setattr(zipfile.ZipFile, 'extractall', boom)

    with pytest.raises(OSError, match='simulated extraction failure'):
        validate_and_index_zip(str(zip_path))

    assert len(captured_dirs) == 1
    assert not os.path.isdir(captured_dirs[0])
