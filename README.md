# Khushboo Jewellers — Catalogue & Admin CMS

![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Jinja2](https://img.shields.io/badge/Jinja2-3.1-B41717?style=flat&logo=jinja&logoColor=white)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-7952B3?style=flat&logo=bootstrap&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-21-499848?style=flat&logo=gunicorn&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-reverse%20proxy-009639?style=flat&logo=nginx&logoColor=white)
![License](https://img.shields.io/badge/license-Proprietary-lightgrey?style=flat)

Flask-based wholesale silver jewellery catalogue with an admin CMS — products, categories,
subcategories, segments, dynamic homepage sections, and bulk Excel/ZIP or Google Sheet import.
Public-facing site is server-rendered (Jinja2 + Bootstrap), backed by a SQLite catalogue of
362 products across 38 categories and 44 subcategories.

## Table of Contents

- [Motivation](#motivation)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Available Scripts](#available-scripts)
- [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Local ZIP Image Import](#local-zip-image-import)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [Security Notes](#security-notes)
- [Credits](#credits)
- [License](#license)

## Motivation

Recovered from the production VPS on 2026-07-28 (`git tag recovery-vps-2026-07-28`) after the
prior developer never committed the backend to git — every change up to that point existed only
on the server. This repo is the hardened, git-tracked continuation: security pass, real catalogue
import (362 products from the client's raw product spreadsheet + photography), and a full
frontend rebuild on a licensed UI template wired to live data instead of placeholders.

There is no online checkout — this is a B2B wholesale catalogue. Product pages carry no price and
no cart; every "Enquire" action routes to a real contact form that lands in the admin CMS.

## Tech Stack

| Concern | Choice |
|---|---|
| Backend framework | Flask 3.0 + Flask-SQLAlchemy (SQLite) |
| Security | Flask-WTF (CSRF), Flask-Limiter (login rate limiting), `hmac.compare_digest` on all credential checks |
| Images | Pillow — uploads auto-convert to WebP, 1080×1080 |
| Frontend | Jinja2 server-rendered templates, Bootstrap 5, vanilla JS (no build step) |
| Import | openpyxl (Excel), gdown (Google Drive image pulls) |
| Production serving | Gunicorn (app) + Nginx (reverse proxy, TLS) |

## Features

- **Public catalogue** — segment → category → subcategory → product drill-down, all driven by
  live DB data (no hardcoded nav).
- **Product detail pages** — real spec text, image gallery, related products, wholesale enquiry
  CTA (no price/cart — matches the B2B model).
- **Search** — matches product name, product code, and spec text.
- **Wholesale enquiry form** — posts to `/api/contact`, lands in the admin CMS's Contact
  Inquiries list.
- **Admin CMS** — full CRUD for segments/categories/subcategories/products, dynamic homepage
  sections, user management, contact inquiry inbox.
- **Bulk catalogue import** — `.xlsx` spreadsheet + optional local image `.zip` (or Google Drive
  folder links), with a live progress tracker (upload → ZIP index → per-sheet import →
  verification) and incremental DB commits so a mid-import restart doesn't lose completed work.

## Project Structure

```
khushboo jewellers/
├── backend/
│   ├── app.py              Flask app factory, config, logging
│   ├── routes.py           All routes — public site + admin CMS + JSON APIs
│   ├── models.py           SQLAlchemy models
│   ├── tasks.py            Excel/ZIP/Google Drive import logic
│   ├── requirements.txt
│   ├── templates/          Public site templates (base.html + pages) + templates/admin/ (CMS)
│   ├── images/             Static marketing/UI images (committed)
│   ├── database/           SQLite DB — gitignored, not in repo
│   └── uploads/             Product/category images — gitignored, not in repo
├── new-ui/                  Licensed Jovenca UI template (design source for backend/templates)
├── scripts/                 One-off maintenance scripts (see Available Scripts)
├── TODO.md                  Hardening punch list (source of truth for remaining work)
└── vps-recovery-summary.txt Recovery process log
```

## Getting Started

**Prerequisites:** Python 3.13, pip.

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

## Available Scripts

| Script | Description |
|---|---|
| `scripts/convert_catalog.py` | Converts the raw wide-format product spreadsheet (one block per category, side-by-side) into the CMS's 4-sheet import template (Segments/Categories/Subcategories/Products), pulling per-product spec text from Excel cell comments. |
| `scripts/update_mega_menu.py` | One-off maintenance script for the public nav's mega-menu data. |

## Environment Variables

See `backend/.env.example` for the full list with descriptions. Key variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask session signing. Required in production — app refuses to start without it. |
| `FLASK_ENV` | `production` enforces debug off, secure cookies, localhost-only bind. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `.env`-based admin login (checked before the DB-backed `AdminUser` table). |
| `SHEET_SYNC_SECRET` | Shared secret for `/api/sheet-sync` (server-to-server, not session-based). |
| `MAX_CONTENT_LENGTH_BYTES` | Upload size cap. Keep at the production default (100MB) — only raise locally for large photo-ZIP imports. |
| `MAX_IMPORT_FILES` / `MAX_IMPORT_TOTAL_BYTES` | Local image-ZIP import guardrails, env-overridable for large local imports. |
| `LOG_DIR` | Rotating log file location (defaults to `backend/logs/`). |
| `PORT` | Local dev server port (defaults to 5000). |

## Testing

No automated test suite exists yet — see `TODO.md`. Manual verification checklist lives in
[Getting Started](#getting-started) above; before a deploy, also confirm the full route sweep
(every product/category/subcategory page) returns 200, not just the happy-path pages.

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

**3. Back up the database first, then run the import locally.**

`backend/app.py` hardcodes the DB path to `database/jewellery.db` with no override — there is no
"copy" mode. Running `python app.py` always reads from and writes to that exact file, so back it
up before you start in case you need to undo the import:

```bash
cd backend
cp database/jewellery.db database/jewellery.db.backup   # backup first — restore from this if something goes wrong
python app.py
```

Visit `http://127.0.0.1:5000/admin/import-excel`, upload the spreadsheet and the images ZIP
together, and submit. The progress UI walks through upload → ZIP indexing → per-sheet import →
verification. Re-running the same import with "Overwrite existing images" unchecked will not
re-process images for records that already have one — consistent with the existing Drive-link
upsert behavior.

**4. Copy the result to the VPS.**

Once you're satisfied with the local import (`backend/database/jewellery.db` and
`backend/uploads/` reflect the imported data), copy both to the VPS manually — see
[Deployment](#deployment).

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
Nginx (public-facing, TLS termination) — khushboojewellers.com
```

Do not edit application code directly on the VPS — all changes go through GitHub. `main` is the
single deployment branch; feature branches merge in via PR.

## Contributing

- Branch per change (`feature/...`), PR into `main` — no direct commits to `main` for anything
  beyond trivial fixes.
- Commit messages: plain, no `Co-Authored-By` trailer, explain the *why* when it isn't obvious
  from the diff.
- Keep `TODO.md` current — it's the source of truth for open hardening/feature work.

## Security Notes

- `backend/.env`, `backend/database/`, `backend/uploads/` are gitignored and must never be
  committed.
- CSRF protection is enforced on all state-changing admin routes (Flask-WTF).
- Admin login is rate-limited (5 attempts/min).
- `/api/sheet-sync` authenticates via `SHEET_SYNC_SECRET` (server-to-server, not session-based)
  — rotate this value if it's ever exposed.
- All credential comparisons use `hmac.compare_digest` (no timing side-channels).
- See `TODO.md` for what's been fixed vs. what's still open.

## Credits

Built and maintained by [Lokesh Patra](https://github.com/lightxLK).

## License

Proprietary — all rights reserved. Not licensed for reuse or redistribution.
