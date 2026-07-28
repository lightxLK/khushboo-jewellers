# Local Image ZIP Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the admin bulk-import ~250 products / 700+ images from local photo folders by
uploading one ZIP alongside the existing Excel import, instead of requiring every image to be
hosted on Google Drive first.

**Architecture:** A new pure-function layer in `backend/tasks.py` validates and indexes an
uploaded ZIP (rejecting encrypted/oversized/path-traversal/duplicate-code archives before
extracting anything), extracts the existing Drive-download image-processing code into a shared
helper both the Drive path and the new local path call, and a small dispatcher
(`resolve_image`) that prefers a local ZIP match and falls back to Drive. `routes.py` streams
the uploaded ZIP straight to a temp file (never buffered fully in memory) and threads its path
through the existing background-import machinery. `MAX_CONTENT_LENGTH` becomes env-configurable
so the 3GB limit needed for this import stays out of the production `.env`.

**Tech Stack:** Flask, SQLAlchemy, openpyxl (existing Excel parsing, untouched), Pillow (image
processing, untouched logic — just relocated), Python's stdlib `zipfile`/`tempfile`/`shutil`.
New: `pytest` as a dev-only dependency — this is the first test suite in the repo, scoped to the
new pure functions only (see Task 1).

## Global Constraints

- No spreadsheet column layout changes — image-code columns work exactly as today.
- No changes to how Categories/Subcategories/Segments/Products match their parents.
- No new production-facing behavior — `MAX_CONTENT_LENGTH_BYTES` stays at the current 100MB
  default in the production `.env`; the 3GB value is set only in the local `.env` used to run
  this import.
- The local ZIP is the primary image source: when a code exists both in the ZIP and via a row's
  Drive link, the ZIP wins.
- Supported image extensions: `.jpg`, `.jpeg`, `.png`, `.webp`. Everything else in the ZIP is
  skipped (not an error).
- Duplicate image codes inside the ZIP are a hard failure (import aborts, zero DB writes),
  never a silent "last one wins".
- Encrypted/password-protected ZIPs are rejected outright.
- Existing per-sheet/per-row commit behavior in `run_import_logic` is unchanged by this feature
  (see spec §7) — not something this plan touches.

---

### Task 1: Add a minimal pytest scaffold

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Interfaces:**
- Produces: a working `pytest` invocation (`cd backend && pytest`) that later tasks' tests run
  under. No app/DB fixtures needed yet — the functions under test in this plan take all their
  inputs as parameters (file bytes, paths) and don't touch the database.

- [ ] **Step 1: Create `backend/requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
```

- [ ] **Step 2: Install it**

```bash
cd backend
pip install -r requirements-dev.txt
```

- [ ] **Step 3: Create `backend/tests/__init__.py`** (empty file, makes `tests` a package)

```bash
mkdir -p backend/tests
touch backend/tests/__init__.py
```

- [ ] **Step 4: Create `backend/tests/conftest.py`**

`tasks.py` does `from app import logger` at module level, and `app.py` raises `RuntimeError` if
`SECRET_KEY` is unset while `FLASK_ENV` defaults to `production`. Tests need `FLASK_ENV` set to
`development` *before* `tasks.py` is ever imported, so this has to happen in `conftest.py`
(pytest loads it before collecting test modules):

```python
import os
import sys

os.environ.setdefault('FLASK_ENV', 'development')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 5: Verify the scaffold works with a trivial smoke test**

Create `backend/tests/test_smoke.py` temporarily:

```python
def test_tasks_module_imports():
    import tasks
    assert hasattr(tasks, 'get_drive_file_id')
```

Run:

```bash
cd backend
pytest tests/test_smoke.py -v
```

Expected: PASS. Delete `backend/tests/test_smoke.py` after confirming — it was only to prove the
scaffold works; Task 2 replaces it with real tests.

- [ ] **Step 6: Commit**

```bash
git add backend/requirements-dev.txt backend/tests/__init__.py backend/tests/conftest.py
git commit -m "Add pytest scaffold for backend unit tests"
```

---

### Task 2: Extract `process_and_store_image` from `download_image_from_drive`

**Files:**
- Modify: `backend/tasks.py`
- Create: `backend/tests/test_image_processing.py`

**Interfaces:**
- Produces: `process_and_store_image(file_bytes: bytes, image_code: str, save_folder: str, upload_folder: str) -> str` — resizes to 1080x1080 (crop-to-fill), flattens transparency onto
  white, encodes WEBP quality 85, saves to `{upload_folder}/{save_folder}/{timestamp}_{image_code}.webp`, returns the public path `/uploads/{save_folder}/{filename}`. Used by Task 3's
  Drive-refactor and Task 4's dispatcher.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_image_processing.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_image_processing.py -v
```

Expected: FAIL with `ImportError: cannot import name 'process_and_store_image' from 'tasks'`.

- [ ] **Step 3: Extract the function in `tasks.py`**

Replace `download_image_from_drive` (currently lines 29–105) with the function split into two:
the new shared helper, and a trimmed version of the Drive downloader that calls it.

```python
def process_and_store_image(file_bytes, image_code, save_folder, upload_folder):
    img = Image.open(io.BytesIO(file_bytes))
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
        img = background

    img_ratio = img.size[0] / img.size[1]
    if img_ratio > 1.0:
        new_height = 1080
        new_width = int(new_height * img_ratio)
    else:
        new_width = 1080
        new_height = int(new_width / img_ratio)
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    left = (new_width - 1080) // 2
    top = (new_height - 1080) // 2
    img = img.crop((left, top, left + 1080, top + 1080))

    out = io.BytesIO()
    img.save(out, format='WEBP', quality=85)
    out.seek(0)

    folder_path = os.path.join(upload_folder, save_folder)
    os.makedirs(folder_path, exist_ok=True)
    save_filename = f"{int(datetime.now().timestamp())}_{image_code}.webp"
    save_path = os.path.join(folder_path, save_filename)
    with open(save_path, 'wb') as f:
        f.write(out.read())

    return f"/uploads/{save_folder}/{save_filename}"


def download_image_from_drive(folder_id, image_code, save_folder, upload_folder):
    try:
        import gdown
        if folder_id not in _drive_folder_cache:
            output_dir = os.path.join(tempfile.gettempdir(), f'kj_drive_{folder_id}')
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            os.makedirs(output_dir, exist_ok=True)
            gdown.download_folder(
                url=f"https://drive.google.com/drive/folders/{folder_id}",
                output=output_dir, quiet=False, use_cookies=False
            )

            file_count = 0
            total_bytes = 0
            for root, dirs, files in os.walk(output_dir):
                for fname in files:
                    file_count += 1
                    total_bytes += os.path.getsize(os.path.join(root, fname))
            if file_count > MAX_DRIVE_FILES or total_bytes > MAX_DRIVE_TOTAL_BYTES:
                shutil.rmtree(output_dir, ignore_errors=True)
                logger.warning(
                    f"Drive folder {folder_id} exceeded import limits "
                    f"({file_count} files, {total_bytes} bytes) - skipped"
                )
                _drive_folder_cache[folder_id] = {}
            else:
                file_index = {}
                for root, dirs, files in os.walk(output_dir):
                    for fname in files:
                        base = fname.rsplit('.', 1)[0].upper()
                        file_index[base] = os.path.join(root, fname)
                _drive_folder_cache[folder_id] = file_index

        file_index = _drive_folder_cache[folder_id]
        found_file = file_index.get(image_code.upper())
        if not found_file:
            return None

        with open(found_file, 'rb') as f:
            file_bytes = f.read()

        return process_and_store_image(file_bytes, image_code, save_folder, upload_folder)
    except Exception as e:
        logger.exception(f"Drive download error: {e}")
        return None
```

Also add `tempfile` and `shutil` to the module-level imports at the top of `tasks.py` (currently
`import threading`, `import uuid`, `from PIL import Image`, `import os, io, json, re`,
`from datetime import datetime`, `from app import logger`) — they were previously imported
locally inside `download_image_from_drive`; Task 3 needs them at module level too:

```python
import threading
import uuid
from PIL import Image
import os, io, json, re, tempfile, shutil, zipfile
from datetime import datetime
from app import logger
```

(The `import zipfile` is for Task 3 — adding it now avoids a second edit to this import line.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_image_processing.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Regression-check the Drive path still works structurally**

```bash
cd backend
python -c "import tasks; print(tasks.download_image_from_drive.__doc__ is None, callable(tasks.process_and_store_image))"
```

Expected: prints `True True` (function exists and is callable; full Drive-network behavior isn't
testable without a real Drive folder, unchanged from before this refactor).

- [ ] **Step 6: Commit**

```bash
git add backend/tasks.py backend/tests/test_image_processing.py
git commit -m "Extract process_and_store_image from download_image_from_drive"
```

---

### Task 3: Add `validate_and_index_zip`

**Files:**
- Modify: `backend/tasks.py`
- Create: `backend/tests/test_zip_import.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `validate_and_index_zip(zip_path: str) -> tuple[dict[str, str], str]` — returns
  `(index, extraction_dir)` where `index` maps `IMAGE_CODE_UPPER -> absolute_file_path` and
  `extraction_dir` is the temp directory the ZIP was extracted into (caller owns cleanup).
  Raises `ValueError` with a human-readable message on any validation failure, before extracting
  anything to disk. Used by Task 5.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_zip_import.py`:

```python
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
    zip_path = tmp_path / 'encrypted.zip'
    with zipfile.ZipFile(zip_path, 'w') as zf:
        info = zipfile.ZipInfo('SECRET.jpg')
        info.flag_bits |= 0x1  # encryption bit, set manually for this test
        zf.writestr(info, b'fake-jpeg-bytes')

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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_zip_import.py -v
```

Expected: FAIL with `ImportError: cannot import name 'validate_and_index_zip' from 'tasks'`.

- [ ] **Step 3: Implement `validate_and_index_zip` in `tasks.py`**

Add near the top of the file, alongside the other module-level constants (after
`MAX_DRIVE_TOTAL_BYTES`):

```python
# Guardrails on the local image ZIP upload — same spirit as the Drive caps
# above, plus zip-specific checks (encryption, path traversal, pathological
# archive structure) since this file comes straight from an admin's machine.
SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMPORT_FILES = 2000
MAX_IMPORT_TOTAL_BYTES = 4 * 1024 * 1024 * 1024  # 4 GB
MAX_IMPORT_PATH_DEPTH = 10
MAX_IMPORT_FILENAME_LENGTH = 255


def validate_and_index_zip(zip_path):
    """Validate an uploaded image ZIP and return (index, extraction_dir).

    index: {IMAGE_CODE_UPPER: absolute_path_on_disk}
    extraction_dir: temp dir the ZIP was extracted into — caller must remove it.

    Raises ValueError with a clear message on any validation failure. Every
    entry in the archive is checked before a single byte is extracted.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Uploaded file is not a valid ZIP archive.")

    with zipfile.ZipFile(zip_path) as zf:
        infolist = zf.infolist()

        for zinfo in infolist:
            if zinfo.flag_bits & 0x1:
                raise ValueError(
                    f"ZIP contains an encrypted entry ('{zinfo.filename}') - "
                    "password-protected archives are not supported."
                )

        file_entries = [z for z in infolist if not z.is_dir()]

        if len(file_entries) > MAX_IMPORT_FILES:
            raise ValueError(
                f"ZIP contains {len(file_entries)} files, exceeding the "
                f"{MAX_IMPORT_FILES}-file import limit."
            )

        total_bytes = sum(z.file_size for z in file_entries)
        if total_bytes > MAX_IMPORT_TOTAL_BYTES:
            raise ValueError(
                f"ZIP's uncompressed contents total {total_bytes} bytes, "
                f"exceeding the {MAX_IMPORT_TOTAL_BYTES}-byte import limit."
            )

        extraction_dir = tempfile.mkdtemp(prefix='kj_import_')
        extraction_dir_real = os.path.realpath(extraction_dir)

        for zinfo in file_entries:
            normalized = os.path.normpath(zinfo.filename)
            if normalized.startswith('..') or os.path.isabs(normalized):
                shutil.rmtree(extraction_dir, ignore_errors=True)
                raise ValueError(
                    f"ZIP entry '{zinfo.filename}' resolves outside the archive "
                    "root - rejected (path traversal guard)."
                )

            depth = normalized.count(os.sep) + 1
            if depth > MAX_IMPORT_PATH_DEPTH:
                shutil.rmtree(extraction_dir, ignore_errors=True)
                raise ValueError(
                    f"ZIP entry '{zinfo.filename}' exceeds the maximum path "
                    f"depth of {MAX_IMPORT_PATH_DEPTH}."
                )

            if len(os.path.basename(normalized)) > MAX_IMPORT_FILENAME_LENGTH:
                shutil.rmtree(extraction_dir, ignore_errors=True)
                raise ValueError(
                    f"ZIP entry '{zinfo.filename}' has a filename longer than "
                    f"{MAX_IMPORT_FILENAME_LENGTH} characters."
                )

            target_path = os.path.realpath(os.path.join(extraction_dir, normalized))
            if not (target_path == extraction_dir_real
                    or target_path.startswith(extraction_dir_real + os.sep)):
                shutil.rmtree(extraction_dir, ignore_errors=True)
                raise ValueError(
                    f"ZIP entry '{zinfo.filename}' resolves outside the "
                    "extraction directory - rejected (path traversal guard)."
                )

        # Every entry passed every check - safe to extract now.
        zf.extractall(extraction_dir)

    index = {}
    duplicates = set()
    skipped_non_image = 0
    for root, dirs, files in os.walk(extraction_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                skipped_non_image += 1
                continue
            code = os.path.splitext(fname)[0].upper()
            path = os.path.join(root, fname)
            if code in index:
                duplicates.add(code)
            else:
                index[code] = path

    if duplicates:
        shutil.rmtree(extraction_dir, ignore_errors=True)
        raise ValueError(
            "ZIP contains duplicate image codes (same code, different files): "
            + ", ".join(sorted(duplicates))
        )

    logger.info(
        f"ZIP import indexed: {len(index)} images, {skipped_non_image} "
        f"non-image files skipped, from {len(file_entries)} archive entries."
    )
    return index, extraction_dir
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_zip_import.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/tasks.py backend/tests/test_zip_import.py
git commit -m "Add validate_and_index_zip: zip-slip, encryption, cap, and duplicate-code guards"
```

---

### Task 4: Add the `resolve_image` dispatcher

**Files:**
- Modify: `backend/tasks.py`
- Create: `backend/tests/test_resolve_image.py`

**Interfaces:**
- Consumes: `process_and_store_image` (Task 2), `download_image_from_drive` (existing, now
  calling `process_and_store_image` internally per Task 2).
- Produces: `resolve_image(image_code, save_folder, upload_folder, local_index, folder_id) -> str | None`. Used by Task 5 to replace every direct `download_image_from_drive(...)` call
  site in `run_import_logic`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_resolve_image.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_resolve_image.py -v
```

Expected: FAIL with `ImportError: cannot import name 'resolve_image' from 'tasks'`.

- [ ] **Step 3: Implement `resolve_image` in `tasks.py`**

Add directly after `download_image_from_drive`:

```python
def resolve_image(image_code, save_folder, upload_folder, local_index, folder_id):
    """Resolve one image code to a saved, processed image path.

    Local ZIP index is checked first and wins if present; Drive is the
    fallback for any code not found locally.
    """
    if not image_code:
        return None
    local_path = local_index.get(image_code.upper()) if local_index else None
    if local_path:
        with open(local_path, 'rb') as f:
            return process_and_store_image(f.read(), image_code, save_folder, upload_folder)
    if folder_id:
        return download_image_from_drive(folder_id, image_code, save_folder, upload_folder)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
pytest tests/test_resolve_image.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Run the full test suite so far**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests from Tasks 2–4 pass (16 total).

- [ ] **Step 6: Commit**

```bash
git add backend/tasks.py backend/tests/test_resolve_image.py
git commit -m "Add resolve_image dispatcher: local ZIP wins, Drive is fallback"
```

---

### Task 5: Wire the ZIP into `run_import_logic`

**Files:**
- Modify: `backend/tasks.py`

**Interfaces:**
- Consumes: `validate_and_index_zip` (Task 3), `resolve_image` (Task 4).
- Produces: `run_import_background(file_bytes, overwrite_images=False, zip_path=None) -> str`
  (task_id) and `run_import_logic(task_id, file_bytes, overwrite_images, zip_path=None)` — new
  optional `zip_path` parameter on both. Used by Task 7 (`routes.py`).

This task has no new unit tests — `run_import_logic` requires a full Flask app context and a
real database to exercise (it already had zero test coverage before this feature; that's a
pre-existing gap, not something this plan is introducing). It's verified manually in Task 9's
end-to-end dry run instead.

**Accepted behavior, stated explicitly so a reviewer doesn't have to infer it:** this import is
**not atomic across the whole run**. It commits per sheet (all Segments, then all Categories,
then Subcategories, then Products), and within a sheet, each row is wrapped in its own
`try/except` that records the error and moves on rather than aborting. So if, say, product row
231 of 250 throws, rows 1–230 (and every earlier sheet) are already committed to the database —
only row 231 is skipped, logged in `results['errors']`, and the import continues to row 232.
This is pre-existing behavior this feature does not change (the zip-level validation in Task 3
is what's new — a bad zip aborts with zero DB writes; a bad *row* inside an otherwise-valid
import has always partially succeeded, and continues to). If fully atomic multi-sheet imports
become a real requirement later, that's a separate change to `run_import_logic`'s commit
structure — out of scope here.

- [ ] **Step 1: Update `run_import_background`'s signature**

Current (lines 107–118):

```python
def run_import_background(file_bytes, overwrite_images=False):
    task_id = str(uuid.uuid4())
    import_tasks_store[task_id] = {'state': 'PENDING', 'progress': 0, 'status': 'Starting...', 'result': None}
    
    def background_worker():
        import_tasks_store[task_id]['state'] = 'PROGRESS'
        run_import_logic(task_id, file_bytes, overwrite_images)
        
    thread = threading.Thread(target=background_worker)
    thread.daemon = True
    thread.start()
    return task_id
```

Replace with:

```python
def run_import_background(file_bytes, overwrite_images=False, zip_path=None):
    task_id = str(uuid.uuid4())
    import_tasks_store[task_id] = {'state': 'PENDING', 'progress': 0, 'status': 'Starting...', 'result': None}

    def background_worker():
        import_tasks_store[task_id]['state'] = 'PROGRESS'
        run_import_logic(task_id, file_bytes, overwrite_images, zip_path=zip_path)

    thread = threading.Thread(target=background_worker)
    thread.daemon = True
    thread.start()
    return task_id
```

- [ ] **Step 2: Update `run_import_logic`'s signature and add ZIP extraction + cleanup**

Current signature and top of function (lines 120–130):

```python
def run_import_logic(task_id, file_bytes, overwrite_images):
    import openpyxl
    from app import app, db
    from models import Segment, Category, Subcategory, Product

    try:
        with app.app_context():
            upload_folder = app.config['UPLOAD_FOLDER']
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
            results = {'segments': 0, 'categories': 0, 'subcategories': 0, 'products': 0, 'errors': []}
```

Replace with:

```python
def run_import_logic(task_id, file_bytes, overwrite_images, zip_path=None):
    import openpyxl
    from app import app, db
    from models import Segment, Category, Subcategory, Product

    extraction_dir = None
    try:
        with app.app_context():
            upload_folder = app.config['UPLOAD_FOLDER']
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
            results = {'segments': 0, 'categories': 0, 'subcategories': 0, 'products': 0, 'errors': []}

            local_index = {}
            if zip_path:
                if task_id in import_tasks_store:
                    import_tasks_store[task_id]['status'] = 'Extracting image ZIP...'
                local_index, extraction_dir = validate_and_index_zip(zip_path)
                if task_id in import_tasks_store:
                    import_tasks_store[task_id]['status'] = f'Indexed {len(local_index)} images from ZIP'
```

- [ ] **Step 3: Wrap the function body in a `finally` that cleans up both temp resources**

At the very bottom of `run_import_logic` (currently lines 389–392):

```python
    except Exception as e:
        if task_id in import_tasks_store:
            import_tasks_store[task_id]['state'] = 'FAILURE'
            import_tasks_store[task_id]['status'] = str(e)
```

Replace with:

```python
    except Exception as e:
        if task_id in import_tasks_store:
            import_tasks_store[task_id]['state'] = 'FAILURE'
            import_tasks_store[task_id]['status'] = str(e)
        logger.exception("Import failed")
    finally:
        if extraction_dir and os.path.isdir(extraction_dir):
            shutil.rmtree(extraction_dir, ignore_errors=True)
        if zip_path and os.path.exists(zip_path):
            os.remove(zip_path)
```

(The `logger.exception("Import failed")` line is new too — the import failure was previously
only visible in the in-memory `import_tasks_store`, never logged, making post-mortem debugging
of a failed import harder than it needed to be.)

- [ ] **Step 4: Replace each of the 6 `download_image_from_drive(...)` call sites with `resolve_image(...)`**

Each of the four sheets currently guards image resolution behind
`if should_download and drive_link and 'PASTE' not in drive_link:` — that guard has to change
so a local-ZIP-only match (no Drive link at all) still resolves. The pattern is identical at all
6 call sites; apply it to each.

**Segments** (currently lines 180–183):

```python
                        if should_download and img_code and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                img_path = download_image_from_drive(folder_id, img_code, 'segments', upload_folder)
```

becomes:

```python
                        if should_download and img_code:
                            folder_id = None
                            if drive_link and 'PASTE' not in drive_link:
                                folder_id = get_drive_file_id(drive_link)
                            img_path = resolve_image(img_code, 'segments', upload_folder, local_index, folder_id)
```

**Categories** (currently lines 231–239):

```python
                        if should_download and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                if img_code:
                                    img_path = download_image_from_drive(folder_id, img_code, 'categories', upload_folder)
                                for gc in gal_codes:
                                    gp = download_image_from_drive(folder_id, gc, 'categories', upload_folder)
                                    if gp:
                                        gallery_paths.append(gp)
```

becomes:

```python
                        if should_download:
                            folder_id = None
                            if drive_link and 'PASTE' not in drive_link:
                                folder_id = get_drive_file_id(drive_link)
                            if img_code:
                                img_path = resolve_image(img_code, 'categories', upload_folder, local_index, folder_id)
                            for gc in gal_codes:
                                gp = resolve_image(gc, 'categories', upload_folder, local_index, folder_id)
                                if gp:
                                    gallery_paths.append(gp)
```

**Subcategories** (currently lines 289–297) — identical pattern, `'subcategories'` instead of
`'categories'`:

```python
                        if should_download:
                            folder_id = None
                            if drive_link and 'PASTE' not in drive_link:
                                folder_id = get_drive_file_id(drive_link)
                            if img_code:
                                img_path = resolve_image(img_code, 'subcategories', upload_folder, local_index, folder_id)
                            for gc in gal_codes:
                                gp = resolve_image(gc, 'subcategories', upload_folder, local_index, folder_id)
                                if gp:
                                    gallery_paths.append(gp)
```

**Products** (currently lines 351–359):

```python
                        if should_download and drive_link and 'PASTE' not in drive_link:
                            folder_id = get_drive_file_id(drive_link)
                            if folder_id:
                                if img_code:
                                    primary_path = download_image_from_drive(folder_id, img_code, 'products/primary', upload_folder)
                                for sc in sec_codes:
                                    sp = download_image_from_drive(folder_id, sc, 'products/gallery', upload_folder)
                                    if sp:
                                        secondary_paths.append(sp)
```

becomes:

```python
                        if should_download:
                            folder_id = None
                            if drive_link and 'PASTE' not in drive_link:
                                folder_id = get_drive_file_id(drive_link)
                            if img_code:
                                primary_path = resolve_image(img_code, 'products/primary', upload_folder, local_index, folder_id)
                            for sc in sec_codes:
                                sp = resolve_image(sc, 'products/gallery', upload_folder, local_index, folder_id)
                                if sp:
                                    secondary_paths.append(sp)
```

- [ ] **Step 5: Add stage-level progress messages and a completion summary log**

The per-row messages (`"Importing segment: X"` etc., already in the existing code) only appear
once a sheet's loop is already running. Add a stage header before each of the 4 sheet blocks so
the admin sees which stage a multi-minute import is in even before the first row of that sheet
completes. Immediately before each `if 'segments' in sheet_map:` / `if 'categories' in
sheet_map:` / `if 'subcategories' in sheet_map:` / `if 'products' in sheet_map:` line, add:

```python
            if task_id in import_tasks_store:
                import_tasks_store[task_id]['status'] = 'Importing Segments...'
```

(substituting `'Importing Categories...'`, `'Importing Subcategories...'`, `'Importing
Products...'` for the other three sheets).

Then, right before the existing success block near the end of the function (currently
`if task_id in import_tasks_store: import_tasks_store[task_id]['state'] = 'SUCCESS'` ...), add a
summary log line covering the whole run:

```python
        logger.info(
            f"Import complete: {results['segments']} segments, {results['categories']} "
            f"categories, {results['subcategories']} subcategories, {results['products']} "
            f"products, {len(local_index)} images available from ZIP, "
            f"{len(results['errors'])} row errors."
        )
```

- [ ] **Step 6: Confirm the module still imports cleanly**

```bash
cd backend
python -c "import tasks; print(callable(tasks.run_import_logic), callable(tasks.run_import_background))"
```

Expected: `True True`, no import errors.

- [ ] **Step 7: Run the full test suite to confirm nothing broke**

```bash
cd backend
pytest tests/ -v
```

Expected: all prior tests still pass (this task added no new tests, but a syntax error or typo
in the edits above would break the import and fail every test).

- [ ] **Step 8: Commit**

```bash
git add backend/tasks.py
git commit -m "Wire local ZIP into run_import_logic: extraction, cleanup, resolve_image at all 6 call sites, progress + summary logging"
```

---

### Task 6: Make `MAX_CONTENT_LENGTH` env-configurable

**Files:**
- Modify: `backend/app.py`
- Modify: `backend/.env.example`

**Interfaces:**
- Produces: `app.config['MAX_CONTENT_LENGTH']` now reads from `MAX_CONTENT_LENGTH_BYTES` env
  var (default unchanged at 100MB). Used by Task 9's local-only `.env` override.

- [ ] **Step 1: Update `app.py`**

Current (line 77):

```python
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
```

Replace with:

```python
# 100MB default is correct for production (public-facing endpoints never need
# more). The local bulk-image-import workflow raises this via
# MAX_CONTENT_LENGTH_BYTES in a *local* .env only — never set this above the
# default in the production .env.
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH_BYTES', 100 * 1024 * 1024))
```

- [ ] **Step 2: Document the new env var in `backend/.env.example`**

Add after the existing `PORT=5000` line:

```
# Maximum request body size in bytes. Default (100MB) is correct for
# production. Only raise this in a LOCAL .env when running the bulk image-ZIP
# import (see README.md) — never in the production .env.
MAX_CONTENT_LENGTH_BYTES=104857600
```

- [ ] **Step 3: Verify the app still starts with the default**

```bash
cd backend
python -c "
import os
os.environ.setdefault('FLASK_ENV', 'development')
from app import app
print(app.config['MAX_CONTENT_LENGTH'])
"
```

Expected: `104857600` (100MB, unchanged default).

- [ ] **Step 4: Verify the override works**

```bash
cd backend
MAX_CONTENT_LENGTH_BYTES=3221225472 python -c "
import os
os.environ.setdefault('FLASK_ENV', 'development')
from app import app
print(app.config['MAX_CONTENT_LENGTH'])
"
```

Expected: `3221225472` (3GB).

(On Windows PowerShell, use `$env:MAX_CONTENT_LENGTH_BYTES = "3221225472"` before the `python`
call instead of the inline `VAR=value` prefix.)

- [ ] **Step 5: Commit**

```bash
git add backend/app.py backend/.env.example
git commit -m "Make MAX_CONTENT_LENGTH env-configurable, default unchanged at 100MB"
```

---

### Task 7: Accept the ZIP upload in `admin_import_excel`

**Files:**
- Modify: `backend/routes.py`

**Interfaces:**
- Consumes: `run_import_background(file_bytes, overwrite_images, zip_path=None)` (Task 5).
- Produces: the route now saves an uploaded `images_zip` file field straight to a temp path
  (never reads it fully into memory) and passes that path through.

- [ ] **Step 1: Update the route**

Current (lines 2093–2137):

```python
@app.route('/admin/import-excel', methods=['GET', 'POST'])
@admin_required
def admin_import_excel():
    if request.method == 'POST':
        try:
            from tasks import run_import_background
            import openpyxl
            
            sheet_url = request.form.get('sheet_url')
            if sheet_url and sheet_url.strip():
                import requests
                import re
                
                # Extract ID from URL
                match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
                if not match:
                    flash('Invalid Google Sheet URL format.', 'error')
                    return redirect(url_for('admin_import_excel'))
                
                sheet_id = match.group(1)
                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                
                try:
                    response = requests.get(export_url, timeout=30)
                    if response.status_code != 200:
                        flash('Failed to fetch Google Sheet. Please make sure the sheet sharing settings are set to "Anyone with the link can view".', 'error')
                        return redirect(url_for('admin_import_excel'))
                    file_bytes = response.content
                except requests.RequestException as e:
                    flash(f'Failed to fetch Google Sheet: {str(e)}', 'error')
                    return redirect(url_for('admin_import_excel'))

            else:
                file = request.files.get('excel_file')
                if not file or not file.filename.endswith('.xlsx'):
                    flash('Please upload a valid .xlsx file or provide a Google Sheets URL', 'error')
                    return redirect(url_for('admin_import_excel'))
                file_bytes = file.read()
                
            overwrite_images = request.form.get('overwrite_images') == 'yes'    
            task_id = run_import_background(file_bytes, overwrite_images=overwrite_images)
            return render_template('admin/import-excel.html', task_id=task_id)
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
            return redirect(url_for('admin_import_excel'))
```

Replace with (adds ZIP handling between reading `file_bytes` and calling
`run_import_background`):

```python
@app.route('/admin/import-excel', methods=['GET', 'POST'])
@admin_required
def admin_import_excel():
    if request.method == 'POST':
        try:
            from tasks import run_import_background
            import openpyxl
            import tempfile

            sheet_url = request.form.get('sheet_url')
            if sheet_url and sheet_url.strip():
                import requests
                import re
                
                # Extract ID from URL
                match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
                if not match:
                    flash('Invalid Google Sheet URL format.', 'error')
                    return redirect(url_for('admin_import_excel'))
                
                sheet_id = match.group(1)
                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
                
                try:
                    response = requests.get(export_url, timeout=30)
                    if response.status_code != 200:
                        flash('Failed to fetch Google Sheet. Please make sure the sheet sharing settings are set to "Anyone with the link can view".', 'error')
                        return redirect(url_for('admin_import_excel'))
                    file_bytes = response.content
                except requests.RequestException as e:
                    flash(f'Failed to fetch Google Sheet: {str(e)}', 'error')
                    return redirect(url_for('admin_import_excel'))

            else:
                file = request.files.get('excel_file')
                if not file or not file.filename.endswith('.xlsx'):
                    flash('Please upload a valid .xlsx file or provide a Google Sheets URL', 'error')
                    return redirect(url_for('admin_import_excel'))
                file_bytes = file.read()

            zip_path = None
            images_zip = request.files.get('images_zip')
            if images_zip and images_zip.filename:
                if not images_zip.filename.lower().endswith('.zip'):
                    flash('Product images file must be a .zip archive.', 'error')
                    return redirect(url_for('admin_import_excel'))
                fd, zip_path = tempfile.mkstemp(suffix='.zip')
                os.close(fd)
                images_zip.save(zip_path)

            overwrite_images = request.form.get('overwrite_images') == 'yes'
            task_id = run_import_background(file_bytes, overwrite_images=overwrite_images, zip_path=zip_path)
            return render_template('admin/import-excel.html', task_id=task_id)
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
            return redirect(url_for('admin_import_excel'))
```

(`images_zip.save(zip_path)` streams the upload to disk via Werkzeug — it does not read the
whole file into a Python `bytes` object first, satisfying the spec's memory-usage requirement.
`os` is already imported at module level in `routes.py` — confirm with
`grep -n "^import os" backend/routes.py` before this edit; if it's imported differently, adjust
the `os.close(fd)` call accordingly.)

- [ ] **Step 2: Confirm the route still compiles**

```bash
cd backend
python -c "
import os
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('SECRET_KEY', 'test')
import routes
print('routes imported OK')
"
```

Expected: `routes imported OK`, no syntax/import errors.

- [ ] **Step 3: Commit**

```bash
git add backend/routes.py
git commit -m "Accept optional images_zip upload in admin_import_excel, streamed to disk"
```

---

### Task 8: Add the ZIP upload field to the import UI

**Files:**
- Modify: `backend/templates/admin/import-excel.html`

**Interfaces:**
- Consumes: nothing new — pure template change, submits to the route from Task 7.

- [ ] **Step 1: Add the upload field**

Insert a new block after the closing `</div>` of the "LINK UPLOAD SECTION" (currently ends at
line 292, right before the `fileDetailBox` div at line 294):

```html
                <div style="background: #F8FAFC; border: 1px dashed var(--lux-border); border-radius: 12px; padding: 25px; margin-bottom: 25px;">
                    <label for="imagesZipInput" style="font-size: 13px; font-weight: 800; color: var(--lux-navy); margin-bottom: 10px; display: block;">
                        <i data-lucide="folder-archive" style="width:14px; margin-right:5px; color:var(--lux-gold)"></i> Product Images (ZIP, optional)
                    </label>
                    <input type="file" id="imagesZipInput" name="images_zip" accept=".zip" style="width: 100%; padding: 14px; border-radius: 8px; border: 1px solid var(--lux-border); font-size: 13px; background: white;">
                    <p style="font-size: 11px; color: var(--lux-text-secondary); margin-top: 12px; line-height: 1.5;">
                        Zip your local photo folders into one file and upload it here. Images are matched to
                        spreadsheet rows by filename (e.g. <code>ABC123.jpg</code> matches image code
                        <code>ABC123</code>) — same matching Google Sheets links use, no need to sort by
                        product/category first. Leave empty to use Google Drive links from the spreadsheet
                        instead.
                    </p>
                </div>
```

- [ ] **Step 2: Manual verification**

```bash
cd backend
python app.py
```

Visit `http://127.0.0.1:5000/admin/import-excel`, log in. Check:
- [ ] The new "Product Images (ZIP, optional)" field renders between the Google Sheets link
      section and the file-detail box
- [ ] Clicking it opens a file picker filtered to `.zip`
- [ ] The rest of the page (tabs, excel upload, overwrite checkbox, submit button) is unchanged

- [ ] **Step 3: Commit**

```bash
git add backend/templates/admin/import-excel.html
git commit -m "Add optional images ZIP upload field to the import UI"
```

---

### Task 9: End-to-end dry run and documentation

**Files:**
- Modify: `backend/README.md` (or wherever deployment/local-setup docs live — confirm exact
  filename with `ls backend/README.md README.md` first)
- Modify: `TODO.md`

**Interfaces:**
- Consumes: the complete feature from Tasks 1–8.

- [ ] **Step 1: Build a small test spreadsheet + zip**

Create a trimmed `.xlsx` with 4 tabs (Segments, Categories, Subcategories, Products), a couple
of rows each, using image codes with no Drive link filled in — and a `.zip` containing matching
tiny JPEG/PNG files named after those codes (e.g. `TESTSEG1.jpg`, `TESTCAT1.jpg`,
`TESTSUB1.jpg`, `TESTPROD1.jpg`, `TESTPROD1B.jpg` for a product gallery image). This can be
built with a short throwaway Python script using `openpyxl` and `PIL` — doesn't need to be
committed to the repo, just used locally for this verification step.

- [ ] **Step 2: Run the import against a scratch copy of the DB**

```bash
cd backend
cp database/jewellery.db /tmp/jewellery-test-backup.db  # or Windows equivalent copy
python app.py
```

Visit `/admin/import-excel`, upload the test `.xlsx` and test `.zip` together, submit. Watch the
progress UI show "Extracting image ZIP..." then "Indexed N images from ZIP" before the normal
per-sheet progress messages.

- [ ] **Step 3: Verify the result**

- [ ] All 4 test rows imported (check `/admin/all-data-view` or the relevant list pages)
- [ ] Each imported record's image renders correctly on its admin edit page and on the public
      site (the image was correctly resized/cropped/converted to WEBP)
- [ ] `backend/tests/` unit tests still pass: `cd backend && pytest tests/ -v`
- [ ] Re-run the same import a second time with `overwrite_images` unchecked — confirm existing
      records aren't re-downloaded/re-processed (matches existing upsert behavior, unaffected by
      this feature)

- [ ] **Step 4: Confirm the Drive-only path still works (regression check)**

If a real Google Drive folder link is available for testing, run one import with no ZIP
uploaded and a spreadsheet row pointing at that Drive link — confirm it still resolves via
`download_image_from_drive` exactly as before this feature existed. If no Drive folder is
available for a live test, this is acceptable to skip with a note — the Task 4 unit tests
already cover the fallback logic path in isolation.

- [ ] **Step 5: Document the local-import workflow**

Add a section to `backend/README.md` (check exact location/heading style first with
`grep -n "^#" backend/README.md`) covering: setting `MAX_CONTENT_LENGTH_BYTES` in the **local**
`.env` only, zipping photo folders into one file, running the import locally against a DB copy,
then manually copying the resulting `jewellery.db` + `uploads/` to the VPS (backing up what's
there first) — matching the workflow described in the design spec's §10.

- [ ] **Step 6: Update `TODO.md`**

Add an entry under the existing "Fixed" history noting the local ZIP import feature is complete,
matching the format of prior entries, and remove/update the older TODO line about "Excel import
Google Drive downloads have no size/count cap" if it's still present (Drive caps were already
added in a prior pass — confirm with `grep -n "Google Drive downloads" TODO.md`).

- [ ] **Step 7: Final commit**

```bash
git add backend/README.md TODO.md
git commit -m "Document local ZIP import workflow, complete feature"
```
