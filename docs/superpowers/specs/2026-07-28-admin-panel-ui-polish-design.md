# Admin Panel UI Polish — Design

Status: Approved (2026-07-28)
Scope: `backend/templates/admin/*` only. Public storefront (`backend/templates/*.html` outside
`admin/`) is explicitly out of scope for this spec.

## Problem

The admin panel (12 pages, all extending `admin/base.html`) reads as dated and inconsistent:

- Every page (`dashboard.html`, `add-product.html`, `edit-product.html`, `add-category.html`,
  `edit-category.html`, `add-subcategory.html`, `edit-subcategory.html`, `add-segment.html`,
  `edit-segment.html`, `dynamic-section.html`, `edit-dynamic-section.html`,
  `user-management.html`, `contact-inquiries.html`, `all-data-view.html`, `import-excel.html`,
  `user_manual.html`, `login.html`) declares its own `<style>` block instead of sharing one.
  Buttons, cards, tables, and badges are redefined slightly differently per page.
- Typography is split: `base.html` loads only Inter; `login.html`, `user_manual.html`, and
  `edit-dynamic-section.html` separately pull in Playfair Display for headings via their own
  duplicated Google Fonts `<link>`. The other 9 pages never get it. This reads as inconsistent,
  not as an intentional type system.
- Icons are Lucide (`data-lucide="..."`) everywhere already — the library choice is fine — but
  every icon is sized with an inline `style="width: Npx"` with no shared scale, and the script
  tag pulls `lucide@latest` (unpinned, can change appearance/behavior without warning).
- Spacing is ad hoc inline px values per page (margins/paddings/gaps), no shared scale.

## Non-goals

- No palette change — keep `--lux-gold` / `--lux-navy` and the existing CSS custom properties
  in `base.html`.
- No layout/structure change — sidebar nav, page structure, and route behavior stay as-is.
- No change to the public storefront.
- No new JS dependencies.

## Design

### 1. Shared stylesheet

New file: `backend/static/css/admin.css`, linked once from `admin/base.html`'s `<head>`.
Carries:
- The existing `--lux-*` custom properties (moved from `base.html`'s inline `<style>`, not
  duplicated).
- New spacing scale: `--space-1: 4px` through `--space-8: 48px` (4px base unit, matches the
  `4px`/`8px` steps already visible in the current inline styles).
- New icon-size classes: `.icon-sm { width: 16px; height: 16px }`, `.icon-md` (18px), `.icon-lg`
  (22px) — chosen to match the three sizes already in use today (14/16/18/20px cluster down to
  three consistent steps).
- Canonical component classes: `.btn` (+ `.btn-primary`/`.btn-danger`/`.btn-ghost`), `.card`,
  `.table`, `.badge` (+ status variants), `.form-group`/`.form-input`/`.form-label` — one
  definition each, replacing the near-duplicate versions currently redefined per page.

Each of the 12 admin templates has its per-page `<style>` block trimmed to only what's
genuinely page-specific (e.g. a one-off layout grid for `dashboard.html`'s stat tiles); anything
that duplicates a canonical component moves to using the shared class instead.

### 2. Typography

- `admin/base.html` keeps the single Google Fonts `<link>`, extended to include Playfair
  Display alongside Inter: `family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700;800`.
- The 3 pages currently loading their own duplicate Google Fonts `<link>` (`login.html`,
  `user_manual.html`, `edit-dynamic-section.html`) drop their local `<link>` — it's inherited
  from `base.html` now.
- New utility class `.font-display` (Playfair Display, 700) applied to: each page's main `<h1>`
  page title (rendered by `base.html`'s shared page-header block), and the login screen's brand
  wordmark. Everywhere else stays Inter. This is the one deliberate use of the serif — not
  sprinkled elsewhere.

### 3. Icons

- `base.html`'s `<script src="https://unpkg.com/lucide@latest">` pinned to the currently-resolved
  version (checked at implementation time, e.g. `lucide@0.4xx.0`) so the icon set can't change
  out from under the admin panel silently.
- Every `<i data-lucide="...">` across the 12 templates gets one of `.icon-sm`/`.icon-md`/`.icon-lg`
  instead of an inline `style="width:Npx"`. Mapping: sidebar nav icons → `.icon-md` (18px, matches
  current), topbar/small inline icons → `.icon-sm` (14–16px cluster → 16px), any larger
  decorative icon → `.icon-lg`.

### 4. Rollout

Work page-by-page against the shared sheet:
1. Build `admin.css` with tokens + canonical components, wire into `base.html`, add Playfair
   Display, pin Lucide version.
2. Migrate `base.html` itself (sidebar, topbar, page-header) to use the new classes.
3. Migrate the 15 remaining templates one at a time, each a self-contained diff: replace
   duplicated `<style>` rules with shared classes, replace inline icon sizing, verify page still
   renders correctly (visual check per page).
4. Delete now-dead per-page CSS once its page is migrated (no lingering duplicate rules).

No database, route, or JS-behavior changes anywhere in this pass — purely template/CSS.

## Testing / Verification

- Visual pass on each of the 12 pages after migration (loaded in a browser, logged in as admin):
  layout not broken, spacing looks consistent, icons render at consistent sizes, Playfair Display
  shows only on page titles + login wordmark.
- Confirm no page references a Google Font or icon size that bypasses the shared system
  (`grep -n "font-family:\|style=\"width:.*px" backend/templates/admin/*.html` should return
  nothing outside legitimate page-specific one-offs called out in step 3 above).
- No console errors from the pinned Lucide version (icons still render).

## Risks

- Pinning Lucide to a specific version means future icon additions need the pin bumped
  deliberately — acceptable tradeoff for stability.
- Trimming per-page `<style>` blocks risks missing a page-specific rule that looked generic but
  wasn't — mitigated by migrating one page at a time with a visual check before moving to the
  next, not a single big-bang sweep.
