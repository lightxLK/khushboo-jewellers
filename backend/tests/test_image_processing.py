import io
import os
from PIL import Image
from tasks import process_and_store_image


def test_process_and_store_image_produces_1080_square_webp(tmp_path):
    img = Image.new('RGB', (2000, 1000), color=(200, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')

    result_path = process_and_store_image(buf.getvalue(), 'ABC123', 'products/primary', str(tmp_path))

    assert result_path.startswith('/uploads/products/primary/')
    assert result_path.endswith('.webp')
    saved_file = tmp_path / 'products' / 'primary' / os.path.basename(result_path)
    assert saved_file.exists()
    with Image.open(saved_file) as saved_img:
        assert saved_img.size == (1080, 1080)
        assert saved_img.format == 'WEBP'


def test_process_and_store_image_flattens_transparency_to_white(tmp_path):
    img = Image.new('RGBA', (1200, 1200), color=(10, 20, 30, 0))
    buf = io.BytesIO()
    img.save(buf, format='PNG')

    result_path = process_and_store_image(buf.getvalue(), 'XYZ999', 'segments', str(tmp_path))

    saved_file = tmp_path / 'segments' / os.path.basename(result_path)
    with Image.open(saved_file) as saved_img:
        assert saved_img.mode == 'RGB'


def test_process_and_store_image_filename_includes_image_code(tmp_path):
    img = Image.new('RGB', (500, 500), color=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format='JPEG')

    result_path = process_and_store_image(buf.getvalue(), 'PROD42', 'products/gallery', str(tmp_path))

    assert 'PROD42' in result_path
