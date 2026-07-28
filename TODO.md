# Khushboo Jewellers — Hardening Punch List

Source of truth for the post-recovery codebase audit and fix pass (2026-07-28).
Full original findings: see conversation history / commit messages. This file tracks
status going forward — update it as items are closed or new ones are found.

## Fixed (this pass)

- [x] `app.py`: `debug=True` + `host='0.0.0.0'` hardcoded → now env-driven, debug off and
      bound to `127.0.0.1` whenever `FLASK_ENV=production`; nginx fronts the public interface.
- [x] `app.py`: `SECRET_KEY` had a hardcoded fallback (`'your-secret-key-change-this'`) →
      now required from env in production (app refuses to start without it); dev-only runs
      get a random ephemeral key with a warning, never a fixed default.
- [x] No CSRF protection anywhere → Flask-WTF `CSRFProtect` wired in; every admin form now
      carries a `csrf_token`; destructive GET-only routes (delete/toggle product, category,
      subcategory, segment, dynamic section, contact inquiry) converted to POST so they can't
      be triggered by a bare link/image tag.
- [x] Hardcoded shared secret `'kjsync2025'` on `/api/sheet-sync` → now reads
      `SHEET_SYNC_SECRET` from env, fails closed (503) if unset, compared with
      `hmac.compare_digest`.
- [x] Session cookies had no security flags → `HttpOnly`, `SameSite=Lax` always;
      `Secure` flag on whenever `FLASK_ENV=production`.
- [x] Admin login had no rate limiting → Flask-Limiter, 5 POST attempts/min per IP (GET to
      view the login page is not throttled). **Note:** in-memory limiter storage — fine for a
      single gunicorn worker; if the VPS ever runs multiple workers, point it at Redis instead
      or the limit won't be shared across workers.
- [x] `.env` admin credential comparison used `==` (timing side-channel) → `hmac.compare_digest`.
- [x] `app.py`'s `catch_all_static` served any `templates/*.html` unauthenticated, including
      raw unrendered admin templates (`/admin/login.html` etc.) → `/admin/*` path blocked from
      that passthrough entirely; admin pages only reachable through their real
      `@login_required` routes.
- [x] Public-facing routes/APIs returned raw exception text (`str(e)`) to end users → replaced
      with a generic message + `logger.exception(...)` server-side. Admin-only `flash()` error
      messages were left as-is (only a logged-in admin sees them).
- [x] `print()` / `traceback.print_exc()` debug statements throughout `routes.py`/`tasks.py` →
      replaced with the `logging` module (`logger.debug/info/warning/exception`).
- [x] Image upload processing had no decompression-bomb guard → `Image.MAX_IMAGE_PIXELS`
      capped at 40MP; `Image.DecompressionBombError` caught explicitly with a clear message.
- [x] `requirements.txt` missing `gunicorn` (needed for the planned prod deployment), added
      along with `Flask-WTF` and `Flask-Limiter`.
- [x] Two business spreadsheet files (`Khushboo_Jewellers_Catalog*.xlsx`) were tracked in git →
      untracked (`git rm --cached`), added to `.gitignore`. Files remain on disk locally.
- [x] `backend/.env.example` added documenting every required env var.
- [x] `README.md` added (setup, structure, deployment flow, security notes).
- [x] Excel import (`tasks.py`) can now index product/category/subcategory/segment images from
      a locally-uploaded `.zip` (matched to spreadsheet rows by filename), as an alternative to
      Google Drive links — for bulk imports where photos live on disk rather than in a shared
      Drive folder. ZIP handling is hardened (path traversal, encrypted entries, file
      count/size caps) and covered by unit tests (`backend/tests/test_zip_import.py`,
      `test_resolve_image.py`). `MAX_CONTENT_LENGTH_BYTES` is now env-configurable so the upload
      limit can be raised locally for large photo ZIPs without touching the production default.
      See `README.md`'s "Local ZIP Image Import" section for the workflow.

## Verified locally (2026-07-28)

- Fresh `venv` + `pip install -r backend/requirements.txt` — clean install, no conflicts.
- Server starts on `127.0.0.1:5000` with `FLASK_ENV=development`, debug reflects env correctly.
- `/admin/login.html` direct access → 404 (was previously serving raw template).
- `/admin/dashboard` without a session → 302 redirect to login (not exposed).
- Login page renders a real per-session CSRF token; POST without a token → 400
  ("The CSRF token is missing"); POST with correct env-admin credentials + token → 302 to
  dashboard, `HttpOnly; SameSite=Lax` session cookie set.
- Rate limiting: GET `/admin/login` unthrottled; 6th+ POST attempt within a minute → 429.
- `/api/sheet-sync` rejects both a missing secret and the old hardcoded `kjsync2025` value
  with 401 — no fallback path left.
- `GET /admin/delete-product/<id>` (old vector) no longer works — route is POST-only now.
- Bad product/category lookups return a generic "not found" page, not a stack trace.
- No product data or images were added/modified during this pass — recovered production
  `jewellery.db` and `uploads/` were left untouched (schema-only `db.create_all()` on startup,
  which is a no-op against existing tables).

## Known pre-existing issue (not fixed — out of scope for security pass)

- [ ] `backend/templates/admin/dynamic-section.html` links to `/admin/dynamic-section/add` and
      `/admin/dynamic-section/delete/<id>`, but no matching routes exist in `routes.py` (only
      an unreferenced `/admin/delete-dynamic-section/<id>`). This looks like a broken/unfinished
      feature predating the recovery — 404s today regardless of auth. Needs product-owner
      input on intended behavior before fixing.

## Still open / recommended next

- [ ] Multi-worker gunicorn note above — move Flask-Limiter (and any other in-process state
      like `tasks.py`'s import-status store) to a shared backend (Redis) before running more
      than one worker process.
- [ ] No automated tests exist for the backend. Recommend at minimum: auth flow, CSRF
      enforcement, CRUD happy-path per entity, Excel import validation.
- [ ] Rotate `SECRET_KEY`, `ADMIN_PASSWORD`, and mint a fresh `SHEET_SYNC_SECRET` for the real
      production `.env` — none of the values used in this local test run should reach prod.
- [ ] Heavy duplication across add/edit/delete/toggle CRUD routes for
      Segment/Category/Subcategory/Product — refactor candidate, not urgent.
- [ ] No structured/rotating log file yet — `logging.basicConfig` currently writes to stdout
      only; wire up a `RotatingFileHandler` (or rely on systemd/gunicorn's log capture) before
      go-live so logs survive restarts.
- [ ] Once the ~250-product spreadsheet import is ready: test the Excel import path fully
      (including Google Drive image pulls) on a copy of the DB before running it against
      production data.

## Deployment readiness

Codebase is ready for a clean VPS deployment once:
1. Real secrets are generated and placed in the VPS's `backend/.env` (never via git).
2. `backend/database/` and `backend/uploads/` are provisioned fresh (or restored from a
   trusted backup) directly on the server.
3. Gunicorn + Nginx are configured per `README.md`'s deployment flow.
4. Product data import (~250 products, 2–3 images each) is done *after* the above, directly
   against the deployed instance or a verified snapshot — not before, per instruction.
