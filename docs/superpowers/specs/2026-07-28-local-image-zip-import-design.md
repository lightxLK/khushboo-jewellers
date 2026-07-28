# Local Image ZIP Import — Design

Status: Draft — pending user approval (revised after spec review, 2026-07-28)
Scope: `backend/routes.py` (`admin_import_excel`), `backend/tasks.py` (`run_import_logic` and
image-resolution helpers), `backend/templates/admin/import-excel.html`. No DB schema changes.

## Problem

The bulk-import flow (`/admin/import-excel`) already does exactly what's needed structurally —
4 sheet tabs (Segments/Categories/Subcategories/Products), each row carrying an image code and
a folder-link column, images matched by filename to the code. But today that folder-link column
only supports a **Google Drive folder URL** — `download_image_from_drive()` uses `gdown` to
scrape a public Drive folder listing.

The real import (~250 products, 700+ images) has images sitting locally on disk, not on Drive,
and pulling 700+ files through unauthenticated Drive folder scraping at that volume is slow and
prone to breaking mid-import (gdown has no real retry/resume story). The images aren't split by
entity type either — they're just two folders from two photo-shoot days; any given image could
belong to a product, category, subcategory, or segment, and can be combined into one flat pool
before upload.

## Approach

Add a local ZIP upload path as an alternative image source, used instead of (or alongside)
Google Drive links. The admin zips both photo folders into one `.zip`, uploads it next to the
spreadsheet on the same import screen. All images extracted from the zip are indexed by
filename (same case-insensitive, extension-stripped matching Drive already uses) into one flat
pool; every row's image-code lookup checks this pool first, and only falls back to a Drive link
if the row has one and the code wasn't found locally. **The local ZIP is treated as the primary
image source; it intentionally overrides a Drive link when both exist for the same code.** This
keeps the existing Drive path working unmodified for anyone who still fills in Drive links — the
ZIP is additive, not a replacement.

**The import runs locally**, against a copy of the recovered production DB, not through the live
site — see §6.

## Non-goals

- No change to the spreadsheet column layout — image-code columns work exactly as they do today.
- No change to how Categories/Subcategories/Segments/Products are matched to their parents.
- No new image processing beyond re-sourcing it — same resize-to-1080/crop/webp pipeline.
- Not building a resumable/chunked upload — a single multipart POST, matching how the Excel
  file itself is already uploaded.
- Not redesigning the importer's existing commit granularity (see §7, Transaction semantics) —
  that behavior predates this feature and is called out, not changed.

## Design

### 1. Upload limit — scoped, not global-production

`MAX_CONTENT_LENGTH` is currently a hardcoded 100MB in `app.py`. Two changes:

- Make it read from an env var with the current value as default:
  `MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH_BYTES', 100 * 1024 * 1024))`.
- For the local import session only, set `MAX_CONTENT_LENGTH_BYTES` in the **local** `backend/.env`
  to 3GB (`3221225472`). This value is explicitly **not** carried into the production `.env` —
  documented in `README.md` as a local-import-only setting, since production's public-facing
  endpoint should keep the conservative 100MB default (no legitimate public request needs more).

### 2. Don't buffer the whole ZIP in memory

Reading a 500MB–2GB upload into a Python `bytes` object (`file.read()`) risks doubling memory
pressure (Werkzeug's own buffering + the Python bytes copy + zip decompression on top). Instead:

- `request.files['images_zip'].save(temp_path)` streams the upload straight to disk — Werkzeug
  already spools large uploads to a temp file internally, so `.save()` is a filesystem copy, not
  a full in-memory read.
- Everything downstream (validation, extraction) operates on the **path**, not bytes.

### 3. Route (`admin_import_excel`)

- Excel file: unchanged, still read as bytes (small file, no concern there).
- If `request.files.get('images_zip')` is present: save it to
  `tempfile.mkstemp(suffix='.zip')`, pass the resulting **path** (not bytes) to
  `run_import_background`.
- `run_import_background(excel_bytes, overwrite_images, zip_path=None)` — `zip_path` threaded
  through to `run_import_logic`, and to the extraction step described below. If the whole import
  fails before extraction ever runs (e.g. bad Excel), the saved temp zip is still cleaned up in a
  `finally`.

### 4. Validating ZIP upload (`tasks.py`)

New function, replacing the "extract everything, then check" approach with **validate-while-
scanning, before writing a single file to disk**:

```
def validate_and_index_zip(zip_path) -> dict[str, str]:
    # returns {IMAGE_CODE_UPPER: absolute_path_on_disk} after full extraction+validation passes
```

Steps, in order, aborting immediately (no partial extraction, no DB writes have happened yet
regardless — see §7) on the first failure:

1. **Reject encrypted archives.** `zipfile.ZipFile(zip_path)` then check
   `zinfo.flag_bits & 0x1` per entry — any encrypted entry aborts the whole import with a clear
   error before extraction starts.
2. **Scan the central directory first** (`zf.infolist()`) before extracting anything:
   - Entry count ≤ `MAX_IMPORT_FILES` (2000).
   - Sum of `file_size` (uncompressed) ≤ `MAX_IMPORT_TOTAL_BYTES` (4GB).
   - Max path depth per entry ≤ 10 segments; max filename length ≤ 255 chars — cheap additional
     zip-bomb/pathological-archive guards.
   - **Zip-slip check on every entry's normalized path** — must resolve inside the target
     extraction dir. Any entry failing this aborts the whole import; nothing is extracted.
   - Any check failing here means zero bytes have been written to disk yet.
3. Only after every entry in the central directory passes all checks: extract to a fresh
   `tempfile.mkdtemp(prefix='kj_import_')` directory.
4. **Supported image extensions only**: `.jpg`, `.jpeg`, `.png`, `.webp`. Any other file in the
   zip (PSD, RAW/CR2/NEF, `.DS_Store`, etc.) is skipped during indexing (not an error — camera
   folders routinely carry junk files) but logged at debug level with a count in the final
   summary.
5. **Duplicate image codes are an error, not a silent overwrite.** While building the flat
   `{basename_upper: path}` index, if a code is seen twice (e.g. `ABC123.jpg` and `ABC123.png`,
   or the same filename present in both source folders with different content), collect it into
   a `duplicates` list instead of overwriting the index entry. If `duplicates` is non-empty after
   indexing, abort the import with an explicit error listing every duplicated code — before any
   DB writes happen. This forces the admin to fix the zip (rename or remove one) rather than
   silently getting whichever file happened to be indexed last.

### 5. Shared image-processing helper

The resize/crop/webp-encode logic currently lives inside `download_image_from_drive`, coupled
to the Drive download. Extract it into a shared, public helper (no leading underscore — it's a
shared component now, not a private implementation detail of the Drive path):

```
def process_and_store_image(file_bytes, image_code, save_folder, upload_folder) -> str | None
```

Both the Drive path and the new local-zip path call this after obtaining raw bytes, so there is
one image-processing implementation, not two. `download_image_from_drive` becomes "get bytes
from Drive, hand to `process_and_store_image`"; the new local path becomes "get bytes from the
extracted zip, hand to `process_and_store_image`".

### 6. Resolution order per row

New dispatcher replacing the direct `download_image_from_drive(...)` calls at each of the four
sheet-processing call sites:

```
def resolve_image(image_code, save_folder, upload_folder, local_index, folder_id) -> str | None:
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

`local_index` values are filesystem paths (strings); the index itself only ever holds validated,
duplicate-free entries per §4 — resolution logic doesn't need to re-check for duplicates.

### 7. Transaction semantics (explicit, not left implicit)

Two separate guarantees, not one:

- **Zip-level:** §4's validate-before-extract approach means a bad zip (encrypted, oversized,
  path-traversal attempt, duplicate codes) aborts before extraction and therefore before the
  import even starts touching the database. Zero DB writes happen if zip validation fails.
- **Row-level (unchanged, pre-existing behavior):** `run_import_logic` already commits per sheet
  (all Segments commit, then all Categories, then Subcategories, then Products) and already
  wraps each row in its own `try/except` that appends to `results['errors']` and continues on
  failure rather than aborting the sheet. A single row's image failure does not roll back
  already-committed rows in that sheet or earlier sheets — this is existing behavior, not
  something this feature changes, and it's called out here explicitly rather than left as an
  unstated assumption. Making the whole 4-sheet import a single atomic transaction would be a
  larger behavioral change to code this feature doesn't otherwise touch — out of scope for this
  spec (worth its own future pass if partial imports become a real operational problem).

### 8. Progress reporting + logging

The existing `import_tasks_store` progress mechanism (used for the admin's live progress UI)
gets two new stages surfaced before the existing per-sheet progress begins:
`"Extracting image ZIP..."` → `"Indexing N images..."`, so a multi-minute zip-extraction step
isn't silently invisible to the admin watching the import screen.

On completion (success or failure), log one summary line via the existing `logger`:
zip file count, indexed count, skipped-non-image count, duplicate count (if aborted for this
reason), Drive-fallback count, total elapsed time.

### 9. Cleanup

Both the saved temp zip (`zip_path` from §3) and the extraction directory (`tempfile.mkdtemp`
from §4) are removed in a `finally` block wrapping the whole import — covering the normal
success path, any caught exception, and an uncaught one (Python's `finally` still runs on
`KeyboardInterrupt` and most exception types propagating out of the background thread). This
prevents temp disk usage from accumulating across repeated import attempts — already a
pre-existing consideration for the Drive path's per-folder-id temp dirs, extended here.

### 10. Where the import runs

The import runs locally, against a copy of the production DB, not through the live site:

1. Copy the recovered production `backend/database/jewellery.db` to a working copy; point the
   local dev server at it (or just run locally — `database/` is already the app's default path).
2. Run the Excel + ZIP import through the local admin panel (`127.0.0.1:5000/admin/import-excel`).
   The importer already **upserts by code** (`product_code`/`category_code`/`subcategory_code`/
   `segment_code` — see existing `run_import_logic`), so running against a copy of the real data
   updates matching rows and inserts new ones without wiping anything.
3. Verify the result locally (browse the site, check the admin dashboard counts).
4. Deploy: back up the VPS's current `jewellery.db` + `uploads/`, then copy the verified local
   `jewellery.db` + `uploads/` over to the VPS, restart the service.

Because the import runs locally, there's no nginx in front of it — the raised
`MAX_CONTENT_LENGTH_BYTES` only needs to work against the local Flask dev server, and is
explicitly not part of the production config (§1).

## Testing / Verification

- Small dry run first: a trimmed spreadsheet (a handful of segments/categories/products) +
  matching small zip, confirm images land correctly and match the right entities.
- Zip-slip guard: construct a malicious test zip with a `../../` path entry, confirm the import
  rejects it before writing anything outside the temp dir.
- Encrypted zip: confirm a password-protected zip is rejected with a clear error, nothing
  extracted.
- Cap guards: confirm a zip exceeding `MAX_IMPORT_FILES`/`MAX_IMPORT_TOTAL_BYTES`/depth/filename-
  length aborts cleanly with a clear error, no partial DB writes.
- **Duplicate image codes:** a zip containing `ABC123.jpg` and `ABC123.png` — confirm the import
  is rejected with both paths named in the error, not silently resolved to one.
- **Mixed source:** a spreadsheet where some rows have local-zip matches and others only have a
  Drive link (zip doesn't contain that code) — confirm local rows use the zip, Drive-only rows
  correctly fall back, and a code present in both resolves to the local file.
- Non-image files in the zip (a stray `.DS_Store`, a `.psd`) — confirm they're skipped, not
  treated as errors.
- Full run: the real ~250-product spreadsheet + real ~700-image zip, on the local DB copy per
  §10, not directly against production data.
- Confirm existing Drive-link-only imports (no zip uploaded) still behave exactly as before —
  regression check on the additive change.

## Risks

- Row-level import behavior (per-sheet commit, continue-on-row-error) is pre-existing and
  unchanged by this feature — a mid-import crash after some rows commit is a known, existing
  characteristic of the importer, not newly introduced. Documented in §7 rather than silently
  inherited.
- Duplicate-code detection adds a hard stop that didn't exist before — if the real 700-image set
  turns out to have legitimate near-duplicates (e.g. a retake with the same code), the admin will
  need to resolve the naming before the import proceeds, rather than getting a silent "last one
  wins" result. This is the intended tradeoff (explicit failure over silent data ambiguity).
- `MAX_CONTENT_LENGTH_BYTES` becoming env-configurable is a small surface change to `app.py`'s
  startup config — low risk, but worth a note in `README.md`'s env var table so it isn't
  forgotten as a knob that exists.
