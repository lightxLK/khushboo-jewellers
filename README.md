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

## Security Notes

- `backend/.env`, `backend/database/`, `backend/uploads/` are gitignored and must never be
  committed.
- CSRF protection is enforced on all state-changing admin routes (Flask-WTF).
- Admin login is rate-limited.
- `/api/sheet-sync` authenticates via `SHEET_SYNC_SECRET` (server-to-server, not session-based)
  — rotate this value if it's ever exposed.
- See `TODO.md` for what's been fixed vs. what's still open.
