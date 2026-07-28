import io
import os
from unittest.mock import patch
from PIL import Image
from tasks import resolve_image


def _write_test_image(path):
    img = Image.new('RGB', (500, 500), color=(100, 100, 100))
    img.save(path, format='JPEG')


def test_resolve_image_returns_none_for_empty_code(tmp_path):
    assert resolve_image('', 'products/primary', str(tmp_path), {}, None) is None
    assert resolve_image(None, 'products/primary', str(tmp_path), {}, None) is None


def test_resolve_image_uses_local_index_when_present(tmp_path):
    source = tmp_path / 'source.jpg'
    _write_test_image(source)
    local_index = {'ABC123': str(source)}

    with patch('tasks.download_image_from_drive') as mock_drive:
        result = resolve_image('ABC123', 'segments', str(tmp_path), local_index, 'some-folder-id')

    mock_drive.assert_not_called()
    assert result is not None
    assert 'ABC123' in result


def test_resolve_image_falls_back_to_drive_when_not_in_local_index(tmp_path):
    with patch('tasks.download_image_from_drive', return_value='/uploads/segments/from_drive.webp') as mock_drive:
        result = resolve_image('NOTLOCAL', 'segments', str(tmp_path), {}, 'some-folder-id')

    mock_drive.assert_called_once_with('some-folder-id', 'NOTLOCAL', 'segments', str(tmp_path))
    assert result == '/uploads/segments/from_drive.webp'


def test_resolve_image_returns_none_when_no_local_and_no_folder_id(tmp_path):
    result = resolve_image('MISSING', 'segments', str(tmp_path), {}, None)
    assert result is None


def test_resolve_image_local_wins_over_drive_when_both_available(tmp_path):
    source = tmp_path / 'source.jpg'
    _write_test_image(source)
    local_index = {'BOTH': str(source)}

    with patch('tasks.download_image_from_drive') as mock_drive:
        result = resolve_image('BOTH', 'segments', str(tmp_path), local_index, 'some-folder-id')

    mock_drive.assert_not_called()
    assert result is not None


def test_resolve_image_returns_none_for_corrupt_local_file(tmp_path):
    bad_file = tmp_path / 'corrupt.jpg'
    bad_file.write_bytes(b'this is not a valid jpeg')
    local_index = {'CORRUPT1': str(bad_file)}

    result = resolve_image('CORRUPT1', 'segments', str(tmp_path), local_index, None)

    assert result is None
