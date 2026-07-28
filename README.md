# Khushboo Jewellers — Catalogue & Admin CMS

Flask-based wholesale silver jewellery catalogue with an admin CMS (products, categories,
subcategories, segments, dynamic homepage sections, Excel/Google Sheet import).

Recovered from production VPS on 2026-07-28 (`git tag recovery-vps-2026-07-28`) after the
prior developer never committed the backend to git. See `TODO.md` for the post-recovery
hardening pass.

## Tech Stack

- Flask 3.0 + Flask-SQLAlchemy (SQLite)
- Flask-WTF (CSRF), Flask-Limiter (login rate limiting)
- Pillow (image processing — auto-converts uploads to WebP, 1080x1080)
- Jinja2 server-rendered templates, vanilla JS/CSS on the frontend
- Gunicorn + Nginx in production

## Project Structure

```
khushboo jewellers/
├── backend/
│   ├── app.py              Flask app factory, config, logging
│   ├── routes.py           All routes (public site + admin CMS + JSON APIs)
│   ├── models.py           SQLAlchemy models
│   ├── tasks.py            Excel/Google Drive import logic
│   ├── requirements.txt
│   ├── templates/          Public site templates + templates/admin/ (CMS)
│   ├── images/             Static marketing images (committed)
│   ├── database/           SQLite DB — gitignored, not in repo
│   └── uploads/             User-uploaded product/category images — gitignored, not in repo
├── css/, index.html         Standalone marketing landing page (separate from backend/templates)
├── scripts/                 One-off maintenance scripts
├── TODO.md                  Hardening punch list (source of truth for remaining work)
└── vps-recovery-summary.txt Recovery process log
```

## Local Setup

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r backend/requirements.txt

cp backend/.env.example backend/.env
# edit backend/.env — set SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD, SHEET_SYNC_SECRET

python backend/app.py
```

First run auto-creates `backend/database/jewellery.db` and the `backend/uploads/` folder
structure — no runtime files need restoring for a **fresh** local setup with no product data
yet. If you're restoring a production snapshot instead, place these (never through git):

```
backend/.env
backend/database/jewellery.db
backend/uploads/
```

Then verify:

- `http://127.0.0.1:5000/` — public site loads
- `http://127.0.0.1:5000/admin/login` — admin login works
- Product/category/segment CRUD in the admin CMS
- Search
- Excel import (`/admin/import-excel`)

## Environment Variables

See `backend/.env.example` for the full list with descriptions. `FLASK_ENV=production`
enforces: `SECRET_KEY` required (app refuses to start without it), secure session cookies,
debug mode off, host bound to localhost only (nginx fronts it).

## Deployment

```
GitHub (main)
      ↓ git pull
Python venv + pip install -r backend/requirements.txt
      ↓
Restore backend/.env, backend/database/, backend/uploads/ (never via git)
      ↓
Gunicorn (binds 127.0.0.1, app.py never runs with debug/0.0.0.0 in production)
      ↓
Nginx (public-facing, TLS termination)
```

Do not edit application code directly on the VPS — all changes go through GitHub.

## Local ZIP Image Import

For bulk-importing product/category/subcategory/segment data with local photo files instead of
(or in addition to) Google Drive links, `/admin/import-excel` accepts an optional `.zip` of
images alongside the `.xlsx` spreadsheet. Images inside the ZIP are matched to spreadsheet rows
by filename (e.g. `ABC123.jpg` matches image code `ABC123`), the same matching Google Drive
links use — no folder structure inside the ZIP required.

**1. Raise the upload size limit — local `.env` only.**

The default `MAX_CONTENT_LENGTH_BYTES` (100MB) is sized for normal admin use and must stay as-is
in production. If your photo ZIP is larger than that, raise the limit in your **local**
`backend/.env` only:

```
MAX_CONTENT_LENGTH_BYTES=1073741824   # e.g. 1GB, local machine only
```

Never set a raised value in the production `backend/.env` — the default is intentional there as
a DoS guard on a public-facing admin upload endpoint.

**2. Zip your photo folders.**

Gather all product/category/subcategory/segment photos into one `.zip`, with each file named
after its image code from the spreadsheet (subfolders inside the zip are fine — only the
filename is used for matching).

**3. Run the import locally, against a copy of the database.**

```bash
cd backend
cp database/jewellery.db database/jewellery-import-test.db   # work on a copy, not the live file
python app.py
```

Visit `http://127.0.0.1:5000/admin/import-excel`, upload the spreadsheet and the images ZIP
together, and submit. The progress UI shows `Extracting image ZIP...` and
`Indexed N images from ZIP` before the normal per-sheet import progress. Re-running the same
import with "Overwrite existing images" unchecked will not re-process images for records that
already have one — consistent with the existing Drive-link upsert behavior.

**4. Copy the result to the VPS.**

Once you're satisfied with the local import (`backend/database/jewellery.db` and
`backend/uploads/` reflect the imported data), copy both to the VPS manually:

1. On the VPS, back up what's currently there (`backend/database/jewellery.db`,
   `backend/uploads/`) before overwriting anything.
2. Copy your local `backend/database/jewellery.db` and `backend/uploads/` to the same paths on
   the VPS (scp/rsync/sftp — not git; both are gitignored).
3. Restart the gunicorn service so the app picks up the new database file.

## Security Notes

- `backend/.env`, `backend/database/`, `backend/uploads/` are gitignored and must never be
  committed.
- CSRF protection is enforced on all state-changing admin routes (Flask-WTF).
- Admin login is rate-limited.
- `/api/sheet-sync` authenticates via `SHEET_SYNC_SECRET` (server-to-server, not session-based)
  — rotate this value if it's ever exposed.
- See `TODO.md` for what's been fixed vs. what's still open.
