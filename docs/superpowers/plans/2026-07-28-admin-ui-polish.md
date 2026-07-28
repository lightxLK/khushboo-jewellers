# Admin Panel UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace 17 independently-styled admin templates' duplicated inline `<style>` blocks
with one shared design system (`backend/static/css/admin.css`), fixing the inconsistent
typography, spacing, and icon sizing the client flagged as "dated and cluttered" — with no
palette, layout, or route/behavior changes.

**Architecture:** One new stylesheet (`admin.css`) holds all design tokens and shared component
classes. `base.html` (the layout shell every page but `login.html` extends) migrates first, then
each of the 17 page templates migrates independently — each migration is its own task with its
own visual-regression check, so a reviewer can approve or reject any single page without
touching the others.

**Tech Stack:** Flask/Jinja2 templates, plain CSS (no preprocessor, no build step — file is
served as a static asset), Lucide icons (pinned CDN version), Google Fonts (Inter + Playfair
Display).

## Global Constraints

- No palette change — `--lux-gold` (#C9A961), `--lux-gold-dark` (#A68A45), `--lux-navy`
  (#0B1739), `--lux-bg` (#F8FAFC), `--lux-border` (#E2E8F0), `--lux-text-primary` (#1E293B),
  `--lux-text-secondary` (#64748B), `--lux-success` (#10B981), `--lux-danger` (#EF4444) carry
  over verbatim.
- No layout/structure change — sidebar nav, page structure, and route behavior stay as-is.
- No change to the public storefront (`backend/templates/*.html` outside `admin/`).
- No new JS dependencies.
- Playfair Display applies to exactly two places sitewide: each page's `<h1>` page title, and
  the login screen's `<h1>`. Nowhere else.
- Lucide pinned to `1.27.0` (resolved from `unpkg.com/lucide@latest` on 2026-07-28). Use this
  exact version everywhere in this plan — don't re-resolve `@latest` mid-implementation, so
  every task lands on the same icon set.
- Going forward: new shared styling belongs in `admin.css`; inline styles are permitted only for
  genuinely page-specific values that cannot reasonably be represented by an existing token,
  primitive, component, or utility.
- No automated CSS/visual test suite exists in this repo. Verification throughout this plan is
  manual: run the local dev server (`cd backend && python app.py`, `FLASK_ENV=development`),
  log into `/admin/login`, and visually check each page per its task's checklist.

---

### Task 1A: Create `admin.css` — tokens, reset, typography, layout primitives

Split from a single large stylesheet task into three (1A/1B/1C) so each is independently
reviewable — a reviewer can approve the foundational tokens without having to also read every
component definition in the same diff.

**Files:**
- Create: `backend/static/css/admin.css`

**Interfaces:**
- Produces: every CSS custom property, the typography scale, and the layout primitives
  referenced by later tasks. Tasks 1B and 1C append to this same file — do not create it again.

- [ ] **Step 1: Create the directory and file**

```bash
mkdir -p backend/static/css
```

- [ ] **Step 2: Write `backend/static/css/admin.css`** (file header + Tokens + Reset +
  Typography + Layout primitives)

```css
/* ====================================================================
   ADMIN DESIGN SYSTEM
   Section order: Tokens -> Reset -> Typography -> Layout primitives ->
   Buttons -> Forms -> Cards -> Tables -> Badges -> Navigation ->
   Utilities -> Responsive
   ==================================================================== */

/* ==================== TOKENS ==================== */
:root {
    /* Color */
    --lux-bg: #F8FAFC;
    --lux-border: #E2E8F0;
    --lux-danger: #EF4444;
    --lux-gold: #C9A961;
    --lux-gold-dark: #A68A45;
    --lux-navy: #0B1739;
    --lux-success: #10B981;
    --lux-text-primary: #1E293B;
    --lux-text-secondary: #64748B;

    /* Spacing (4px base unit) */
    --space-1: 4px;
    --space-2: 8px;
    --space-3: 12px;
    --space-4: 16px;
    --space-5: 24px;
    --space-6: 32px;
    --space-7: 40px;
    --space-8: 48px;

    /* Radius */
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;

    /* Shadow */
    --shadow-sm: 0 1px 3px rgba(11, 23, 57, 0.06);
    --shadow-md: 0 4px 12px rgba(11, 23, 57, 0.08);
    --shadow-lg: 0 12px 32px rgba(11, 23, 57, 0.14);

    /* Motion: one deliberate pair so no page invents its own timing.
       --transition-normal matches the 0.2s used throughout the current
       inline styles (nav hover, buttons, inputs) — chosen so migrating
       to it causes zero visual change. --transition-fast is new, used
       only for the focus-visible outline. */
    --transition-fast: 120ms ease;
    --transition-normal: 200ms ease;

    /* Z-index */
    --z-topbar: 500;
    --z-sidebar: 1000;
    --z-dropdown: 1100;
    --z-modal: 1200;

    /* Layout */
    --border-light: 1px solid var(--lux-border);
    --content-max-width: 1440px;
    --sidebar-width: 260px;

    /* Breakpoint (reference only). CSS custom properties cannot be used
       inside @media conditions in plain CSS, so every @media rule in the
       Responsive section below hardcodes 1024px directly. If you change
       this value, also update every @media (max-width: 1024px) below. */
    --bp-tablet: 1024px;
}

/* ==================== RESET ==================== */
*,
*::before,
*::after {
    box-sizing: border-box;
}

body {
    margin: 0;
    padding: 0;
    font-family: 'Inter', sans-serif;
    background: var(--lux-bg);
    color: var(--lux-text-primary);
}

a {
    color: inherit;
}

button,
input,
select,
textarea {
    font-family: inherit;
}

:focus-visible {
    outline: 2px solid var(--lux-gold);
    outline-offset: 2px;
    transition: outline-offset var(--transition-fast);
}

/* ==================== TYPOGRAPHY ==================== */
.font-display {
    font-family: 'Playfair Display', serif;
    font-weight: 700;
}

.heading-xl {
    font-size: 28px;
    font-weight: 800;
    color: var(--lux-navy);
    line-height: 1.2;
}

.heading-lg {
    font-size: 22px;
    font-weight: 800;
    color: var(--lux-navy);
    line-height: 1.25;
}

.heading-md {
    font-size: 16px;
    font-weight: 700;
    color: var(--lux-text-primary);
}

.text-muted {
    color: var(--lux-text-secondary);
}

.text-small {
    font-size: 12px;
}

.icon-sm,
.icon-md,
.icon-lg {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.icon-sm {
    width: 16px;
    height: 16px;
}

.icon-md {
    width: 18px;
    height: 18px;
}

.icon-lg {
    width: 22px;
    height: 22px;
}

/* ==================== LAYOUT PRIMITIVES ==================== */
.stack {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
}

.cluster {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-3);
}

.grid {
    display: grid;
    gap: var(--space-5);
}

.grid-2 {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-5);
}

.grid-3 {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-5);
}
```

- [ ] **Step 3: Verify brace balance so far**

```bash
python -c "s=open('backend/static/css/admin.css').read(); print('OPEN', s.count('{'), 'CLOSE', s.count('}'))"
```

Expected: both numbers equal.

- [ ] **Step 4: Commit**

```bash
git add backend/static/css/admin.css
git commit -m "Add admin.css: tokens, reset, typography, layout primitives"
```

---

### Task 1B: Append buttons, forms, cards, tables, badges to `admin.css`

**Files:**
- Modify: `backend/static/css/admin.css` (created in Task 1A — append to it, don't recreate it)

**Interfaces:**
- Consumes: tokens from Task 1A (`--space-*`, `--radius-*`, `--border-light`,
  `--transition-normal`, `--lux-*`).
- Produces: `.btn`/`.btn-sm`/`.btn-md`/`.btn-lg`/`.btn-primary`/`.btn-danger`/`.btn-ghost`/
  `.btn-icon`, `.form-*`, `.card`/`.stat-*`, `.table*`, `.badge*` — referenced by every
  per-page migration task (3–18).

- [ ] **Step 1: Append to `backend/static/css/admin.css`**

Add the following at the end of the file (after the Layout primitives section from Task 1A):

```css
/* ==================== BUTTONS ==================== */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    border: none;
    border-radius: var(--radius-md);
    font-weight: 700;
    cursor: pointer;
    text-decoration: none;
    transition: background var(--transition-normal), opacity var(--transition-normal);
}

.btn-sm {
    padding: 6px 12px;
    font-size: 12px;
}

.btn-md {
    padding: 10px 20px;
    font-size: 13px;
}

.btn-lg {
    padding: 12px 28px;
    font-size: 14px;
}

.btn-primary {
    background: var(--lux-gold);
    color: white;
}

.btn-primary:hover {
    background: var(--lux-gold-dark);
}

.btn-danger {
    background: var(--lux-danger);
    color: white;
}

.btn-danger:hover {
    opacity: 0.9;
}

.btn-ghost {
    background: transparent;
    color: var(--lux-text-primary);
    border: var(--border-light);
}

.btn-ghost:hover {
    background: #F1F5F9;
}

.btn-icon {
    width: 36px;
    height: 36px;
    padding: 0;
    border-radius: var(--radius-md);
}

.btn:disabled,
.btn[disabled] {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
}

/* ==================== FORMS ==================== */
.form-group {
    margin-bottom: var(--space-4);
}

.form-label {
    display: block;
    font-size: 13px;
    font-weight: 700;
    color: var(--lux-text-primary);
    margin-bottom: var(--space-2);
}

.form-input,
.form-select,
.form-textarea {
    width: 100%;
    padding: 10px 14px;
    border: var(--border-light);
    border-radius: var(--radius-md);
    font-size: 14px;
    background: white;
    outline: none;
    transition: border-color var(--transition-normal), box-shadow var(--transition-normal);
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
    border-color: var(--lux-gold);
    box-shadow: 0 0 0 3px rgba(201, 169, 97, 0.15);
}

.form-textarea {
    resize: vertical;
    min-height: 100px;
}

.form-checkbox {
    width: 16px;
    height: 16px;
    accent-color: var(--lux-gold);
}

.form-help {
    font-size: 12px;
    color: var(--lux-text-secondary);
    margin-top: var(--space-1);
}

.form-error {
    font-size: 12px;
    color: var(--lux-danger);
    margin-top: var(--space-1);
}

.form-row {
    display: flex;
    gap: var(--space-4);
    align-items: flex-end;
}

.form-row .form-group {
    flex: 1;
    margin-bottom: 0;
}

/* ==================== CARDS ==================== */
.card {
    background: white;
    border: var(--border-light);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-5);
    margin-bottom: var(--space-5);
}

.stat-card {
    background: white;
    border: var(--border-light);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    padding: var(--space-5);
    display: flex;
    align-items: center;
    gap: var(--space-4);
}

.stat-icon {
    width: 44px;
    height: 44px;
    border-radius: var(--radius-md);
    background: rgba(201, 169, 97, 0.12);
    color: var(--lux-gold);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.stat-value {
    font-size: 24px;
    font-weight: 800;
    color: var(--lux-navy);
    line-height: 1.2;
}

.stat-label {
    font-size: 12px;
    color: var(--lux-text-secondary);
    font-weight: 600;
}

/* ==================== TABLES ==================== */
.table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border: var(--border-light);
    border-radius: var(--radius-lg);
    overflow: hidden;
}

.table th {
    text-align: left;
    padding: var(--space-3) var(--space-4);
    background: #F8FAFC;
    font-size: 11px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--lux-text-secondary);
    border-bottom: var(--border-light);
}

.table td {
    padding: var(--space-3) var(--space-4);
    border-bottom: var(--border-light);
    font-size: 13px;
    vertical-align: middle;
}

.table tbody tr:last-child td {
    border-bottom: none;
}

.table tbody tr:hover {
    background: #F8FAFC;
}

.table-actions {
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

.table-empty {
    text-align: center;
    padding: var(--space-8);
    color: var(--lux-text-secondary);
    font-size: 13px;
}

.table-wrap {
    overflow-x: auto;
}

/* ==================== BADGES ==================== */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.badge-success {
    background: rgba(16, 185, 129, 0.12);
    color: var(--lux-success);
}

.badge-warning {
    background: rgba(201, 169, 97, 0.15);
    color: var(--lux-gold-dark);
}

.badge-danger {
    background: rgba(239, 68, 68, 0.12);
    color: var(--lux-danger);
}

.badge-info {
    background: rgba(59, 130, 246, 0.12);
    color: #3B82F6;
}

.badge-neutral {
    background: #F1F5F9;
    color: var(--lux-text-secondary);
}
```

- [ ] **Step 2: Verify brace balance so far**

```bash
python -c "s=open('backend/static/css/admin.css').read(); print('OPEN', s.count('{'), 'CLOSE', s.count('}'))"
```

Expected: both numbers equal.

- [ ] **Step 3: Commit**

```bash
git add backend/static/css/admin.css
git commit -m "Append buttons, forms, cards, tables, badges to admin.css"
```

---

### Task 1C: Append navigation, utilities, responsive to `admin.css`

**Files:**
- Modify: `backend/static/css/admin.css` (created in 1A, extended in 1B — append, don't
  recreate).

**Interfaces:**
- Consumes: tokens from Task 1A.
- Produces: `.admin-container`/`.sidebar*`/`.nav-*`/`.top-bar*`/`.logout-btn`/`.content-area`
  (consumed by Task 2's `base.html` migration) and the utility classes/responsive rules
  consumed by every later per-page task.

- [ ] **Step 1: Append to `backend/static/css/admin.css`**

Add the following at the end of the file (after the Badges section from Task 1B):

```css
/* ==================== NAVIGATION ====================
   Sidebar/topbar/page-header, relocated from base.html's old inline
   <style> block. Values are kept numerically identical to the original
   (not forced onto the --space-* scale) specifically to avoid visual
   regression during this migration — see Task 2. Rule of thumb for this
   whole section and every per-page migration task: this pass moves and
   renames CSS, it does not redesign it — don't change a spacing, size,
   or color value while migrating a rule to a shared class unless a task
   explicitly calls out the change (as Task 2 does for the two icon
   rounding adjustments). If it looks like it should be tweaked, that's a
   separate follow-up, not part of this migration. */
.admin-container {
    display: flex;
    min-height: 100vh;
}

.sidebar {
    width: var(--sidebar-width);
    background: var(--lux-navy);
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    display: flex;
    flex-direction: column;
    z-index: var(--z-sidebar);
    transition: all 0.3s ease;
}

.sidebar.hidden {
    transform: translateX(-100%);
}

.sidebar-header {
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
    color: white;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo-box {
    width: 32px;
    height: 32px;
    background: var(--lux-gold);
    border-radius: var(--radius-md);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
}

.sidebar-header h2 {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

.sidebar-nav {
    flex: 1;
    padding: 16px 0;
    overflow-y: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
}

.sidebar-nav::-webkit-scrollbar {
    display: none;
}

.nav-section-title {
    padding: 20px 24px 8px;
    font-size: 10px;
    font-weight: 800;
    color: #4B5563;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 24px;
    color: #94A3B8;
    text-decoration: none;
    font-size: 13px;
    font-weight: 500;
    transition: all var(--transition-normal);
}

.nav-item:hover {
    color: white;
    background: rgba(255, 255, 255, 0.05);
}

.nav-item.active {
    background: var(--lux-gold);
    color: white;
    border-radius: var(--radius-md);
    margin: 0 16px 4px;
    padding: 10px 20px;
}

.nav-badge {
    background: var(--lux-gold);
    color: white;
    border-radius: 12px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 800;
    margin-left: auto;
}

.sidebar-footer {
    padding: 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.view-website-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 40px;
    background: var(--lux-gold);
    border-radius: var(--radius-md);
    color: white;
    text-decoration: none;
    font-size: 13px;
    font-weight: 700;
}

.main-content {
    margin-left: var(--sidebar-width);
    flex: 1;
    min-height: 100vh;
    transition: all 0.3s ease;
    position: relative;
}

.main-content.expanded {
    margin-left: 0;
}

.top-bar {
    background: white;
    padding: 0 24px;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: var(--border-light);
    position: sticky;
    top: 0;
    z-index: var(--z-topbar);
}

.top-bar-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.menu-toggle {
    cursor: pointer;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-sm);
    color: var(--lux-text-primary);
    transition: background var(--transition-normal);
}

.menu-toggle:hover {
    background: #F1F5F9;
}

.top-bar-title {
    font-size: 15px;
    font-weight: 700;
    color: var(--lux-text-primary);
}

.user-controls {
    display: flex;
    align-items: center;
    gap: 12px;
}

.user-avatar {
    width: 34px;
    height: 34px;
    background: var(--lux-gold);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 700;
    font-size: 12px;
}

.logout-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--lux-danger);
    color: white;
    padding: 8px 16px;
    border-radius: var(--radius-sm);
    text-decoration: none;
    font-size: 12px;
    font-weight: 700;
    transition: opacity var(--transition-normal);
}

.logout-btn:hover {
    opacity: 0.9;
}

.content-area {
    padding: 24px 30px;
}

/* ==================== UTILITIES ==================== */
.mt-2 { margin-top: var(--space-2); }
.mt-4 { margin-top: var(--space-4); }
.mb-2 { margin-bottom: var(--space-2); }
.mb-4 { margin-bottom: var(--space-4); }
.gap-2 { gap: var(--space-2); }
.gap-4 { gap: var(--space-4); }
.flex { display: flex; }
.flex-between { display: flex; align-items: center; justify-content: space-between; }
.hidden { display: none; }
.w-full { width: 100%; }
.text-center { text-align: center; }

/* ==================== RESPONSIVE ==================== */
@media (max-width: 1024px) {
    .grid-2,
    .grid-3 {
        grid-template-columns: 1fr;
    }

    .form-row {
        flex-direction: column;
        align-items: stretch;
    }
}
```

- [ ] **Step 2: Verify the complete file has no syntax errors**

There's no CSS test runner in this repo. Verify by brace-balance (every `{` has a matching `}`)
across the now-complete file:

```bash
python -c "s=open('backend/static/css/admin.css').read(); print('OPEN', s.count('{'), 'CLOSE', s.count('}'))"
```

Expected: both numbers equal. Full functional verification happens in Task 2, when the file is
actually linked into a rendered page.

- [ ] **Step 3: Commit**

```bash
git add backend/static/css/admin.css
git commit -m "Append navigation, utilities, responsive to admin.css — admin.css complete"
```

---

### Task 2: Migrate `base.html` to the shared stylesheet

Line numbers below are as of the current file (432 lines) and are navigational aids only — if
the file has drifted since this plan was written, match on the literal original code shown in
each step (reproduced verbatim below), not the line number.

**Files:**
- Modify: `backend/templates/admin/base.html` (currently 432 lines; full content read and
  reproduced below)

**Interfaces:**
- Consumes: every class name and token from Tasks 1A–1C's `admin.css`.
- Produces: the page-header pattern (`<h1 class="font-display heading-xl">...`) and
  `.nav-badge` class that later per-page tasks rely on for their own titles.

- [ ] **Step 1: Replace `base.html`'s `<head>` and inline `<style>` block**

Current `<head>` (lines 4–308) loads Inter only and defines the entire inline stylesheet.
Replace lines 4–308 with:

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Admin Panel{% endblock %}</title>

    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/admin.css') }}">
</head>
```

(This drops the entire old `:root`/reset/layout/sidebar/topbar/`.lux-*` CSS block — it all now
lives in `admin.css` from Tasks 1A–1C. `--sidebar-width` was the only token not prefixed `--lux-`;
it's defined in `admin.css`'s Tokens section already.)

- [ ] **Step 2: Update icon markup to use the new size classes**

In the `<body>` (originally lines 310–408), make these exact replacements:

```
Line 316: <i data-lucide="gem" style="color: white; width: 16px;"></i>
      ->  <i data-lucide="gem" class="icon-sm"></i>
```
(`.logo-box` in admin.css already sets `color: white` on the parent, and lucide icons use
`currentColor` by default, so the explicit inline color is no longer needed.)

```
Lines 324, 330, 334, 338, 342, 348, 352, 356, 366, 370 (all `style="width:18px"` sidebar nav icons):
      <i data-lucide="..." style="width:18px"></i>
  ->  <i data-lucide="..." class="icon-md"></i>
```

```
Line 377: <i data-lucide="globe" style="width:16px"></i>
      ->  <i data-lucide="globe" class="icon-sm"></i>
```

```
Line 388: <i data-lucide="menu" style="width: 20px;"></i>
      ->  <i data-lucide="menu" class="icon-lg"></i>
```
(20px rounds up to the 22px `.icon-lg` step — a deliberate, spec-anticipated 2px adjustment,
not a bug.)

```
Line 398: <i data-lucide="log-out" style="width: 14px;"></i>
      ->  <i data-lucide="log-out" class="icon-sm"></i>
```
(14px rounds up to the 16px `.icon-sm` step — same rationale.)

- [ ] **Step 3: Replace the unread-inquiries inline-styled badge**

```
Lines 358-363:
    {% if unread_inquiries_count > 0 %}
    <span
        style="background: var(--lux-gold); color: white; border-radius: 12px; padding: 2px 8px; font-size: 10px; font-weight: 800; margin-left: auto;">
        {{ unread_inquiries_count }} New
    </span>
    {% endif %}

Becomes:
    {% if unread_inquiries_count > 0 %}
    <span class="nav-badge">{{ unread_inquiries_count }} New</span>
    {% endif %}
```

- [ ] **Step 4: Pin the Lucide script version**

```
Line 410: <script src="https://unpkg.com/lucide@latest"></script>
      ->  <script src="https://unpkg.com/lucide@1.27.0"></script>
```

- [ ] **Step 5: Leave the rest of `base.html` unchanged**

The `<title>`/`topbar_title` block, `{% block content %}`, and the `<script>` block (sidebar
toggle + active-link JS, originally lines 411–430) are untouched — no behavior change.

- [ ] **Step 6: Manual verification**

Start the dev server and log in:

```bash
cd backend
python app.py
```

Visit `http://127.0.0.1:5000/admin/dashboard`, log in. Check:
- [ ] Sidebar renders (navy background, gold logo box, nav items, active-page highlighting)
- [ ] Topbar renders (menu toggle, title, avatar initial, logout button)
- [ ] Sidebar collapse/expand still works (click the menu icon)
- [ ] Icons all render (no missing/broken icon glyphs — confirms the Lucide pin didn't break
      anything)
- [ ] Browser console has no errors
- [ ] Tab through the topbar/sidebar — visible gold focus ring appears on each link/button

- [ ] **Step 7: Commit**

```bash
git add backend/templates/admin/base.html
git commit -m "Migrate base.html to shared admin.css, pin Lucide, drop inline styles"
```

---

### Task 3: Migration procedure + worked example (`login.html`)

Line numbers below are as of the current 247-line file and are navigational aids only — match
on the literal original code shown in each step, not the line number, if the file has drifted.

`login.html` does **not** extend `base.html`** — it's a standalone document (its own `<head>`,
no sidebar/topbar). It cannot "inherit" `admin.css` or fonts from `base.html` the way the other
16 pages do; it needs its own `<link>` tags. This is a correction to the original design spec,
which assumed all 3 duplicate-font pages extended `base.html` — `login.html` doesn't. The other
2 (`user_manual.html`, `edit-dynamic-section.html`) do extend `base.html` and follow the normal
procedure in Tasks 5+.

**Files:**
- Modify: `backend/templates/admin/login.html` (full 247 lines read and reproduced below)

**Interfaces:**
- Consumes: `admin.css` tokens/reset from Tasks 1A–1C (values only — no shared components; the login
  card is a deliberate bespoke design, called out as such in the spec).
- Produces: the migration procedure every later per-page task (4, 6–19) follows:
  1. `grep -n "style=" backend/templates/admin/<file>` — list every inline `style=` attribute.
  2. `grep -n "<style>\|font-family\|fonts.googleapis" backend/templates/admin/<file>` — find the
     page's own `<style>` block and any duplicate font `<link>`.
  3. For each inline icon `style="width:Npx"`: replace with `class="icon-sm"` (≤16px),
     `class="icon-md"` (17–19px), or `class="icon-lg"` (20px+) per Tasks 1A–1C's scale.
  4. For each inline style that duplicates a Tasks 1A–1C component (buttons, `.card`, `.table`,
     `.badge-*`, `.form-*`, spacing) — replace with the shared class instead of the inline style.
  5. For each inline style that's genuinely page-specific (a one-off gradient, a specific
     shadow only this page uses) — leave it inline; that's the allowed exception per the
     governance rule.
  6. If the page extends `base.html`: delete its local `<style>` block and duplicate Google
     Fonts `<link>` entirely (inherited from `base.html`, migrated in Task 2). If the page is
     standalone (only `login.html`): keep a `<link>` to Google Fonts and `admin.css`, but delete
     any `:root` token block / `*{margin:0;padding:0;box-sizing:border-box}` reset from its own
     `<style>` — those are now provided by `admin.css`.
  7. Run the manual verification checklist (Task 2 Step 6, adapted per page) before committing.

- [ ] **Step 1: Update `login.html`'s `<head>`**

Replace lines 4–198 (`<head>` through the closing `</style></head>`) with:

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - Khushboo Jewellers</title>
    <link
        href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700&display=swap"
        rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/admin.css') }}">
    <script src="https://unpkg.com/lucide@1.27.0"></script>
    <style>
        .login-container {
            background: white;
            padding: 50px 40px;
            border-radius: 24px;
            border: 1px solid rgba(226, 232, 240, 0.8);
            max-width: 440px;
            width: 100%;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.05);
            text-align: center;
            position: relative;
            overflow: hidden;
        }

        body {
            background-image:
                radial-gradient(at 0% 0%, rgba(201, 169, 97, 0.05) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(30, 41, 59, 0.05) 0px, transparent 50%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .login-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--lux-gold) 0%, var(--lux-gold-dark) 100%);
        }

        .login-container .logo-box {
            width: 64px;
            height: 64px;
            border-radius: 16px;
            margin: 0 auto 24px;
            box-shadow: 0 8px 16px rgba(201, 169, 97, 0.3);
        }

        .login-container h1 {
            font-family: 'Playfair Display', serif;
            font-size: 28px;
            color: var(--lux-text-primary);
            margin-bottom: 8px;
            font-weight: 700;
        }

        .login-container p {
            color: var(--lux-text-secondary);
            font-size: 14px;
            margin-bottom: 35px;
        }

        .login-container .form-group {
            text-align: left;
            position: relative;
        }

        .login-container .form-group label {
            display: block;
            margin-bottom: 8px;
            color: var(--lux-text-primary);
            font-weight: 700;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .input-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }

        .input-wrapper i {
            position: absolute;
            left: 14px;
            color: var(--lux-gold);
        }

        .login-container .form-group input {
            width: 100%;
            padding: 13px 14px 13px 44px;
            border: var(--border-light);
            border-radius: var(--radius-lg);
            font-size: 14px;
            transition: all var(--transition-normal);
            background: var(--lux-bg);
        }

        .login-container .form-group input:focus {
            outline: none;
            border-color: var(--lux-gold);
            background: white;
            box-shadow: 0 0 0 4px rgba(201, 169, 97, 0.1);
        }

        .btn-login {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, var(--lux-gold) 0%, var(--lux-gold-dark) 100%);
            color: white;
            border: none;
            border-radius: var(--radius-lg);
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 10px;
            box-shadow: 0 4px 12px rgba(201, 169, 97, 0.2);
        }

        .btn-login:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(201, 169, 97, 0.4);
        }

        .error {
            background: #FFF1F2;
            color: #BE123C;
            padding: 12px;
            margin-bottom: 20px;
            font-size: 13px;
            border: 1px solid rgba(190, 18, 60, 0.1);
            border-radius: 10px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .back-home {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #F1F5F9;
        }

        .back-home a {
            color: #94A3B8;
            text-decoration: none;
            font-size: 13px;
            font-weight: 600;
            transition: all var(--transition-normal);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        .back-home a:hover {
            color: var(--lux-gold-dark);
        }

        @media (max-width: 480px) {
            .login-container {
                padding: 40px 25px;
            }
        }
    </style>
</head>
```

Notes on what changed vs. the original: the `:root` token block and `*{margin:0;padding:0;
box-sizing:border-box}` reset are gone (now from `admin.css`); `.logo-box` no longer redefines
`background`/`display`/`align-items`/`justify-content`/`color` (inherited from `admin.css`'s
shared `.logo-box` rule, only login-specific size/radius/shadow stay local); `var(--lux-slate)`
references become `var(--lux-text-primary)` (same color, correct token name — `--lux-slate`
never existed in the shared token set, it was this page's own naming); the `.form-group` (base
layout: `margin-bottom: 20px`) rule is intentionally **not** removed even though `admin.css` now
has a `.form-group` too — this page's version is scoped under `.login-container .form-group` so
it doesn't collide, and its `text-align: left` + no-bottom-margin-conflict behavior is
login-specific.

- [ ] **Step 2: Update icon markup**

```
Line 203: <i data-lucide="shield-check" style="width: 32px; height: 32px;"></i>
Stays inline — 32px doesn't match any of the 3 icon-scale steps and is a genuine one-off
(the login screen's oversized brand icon). No change needed.

Line 210: <i data-lucide="alert-circle" style="width: 16px;"></i>
      ->  <i data-lucide="alert-circle" class="icon-sm"></i>

Line 220: <i data-lucide="user"></i>  (sized via .input-wrapper i { width: 18px } rule — leave as-is,
          it's a page-specific positioned-icon pattern, not the shared icon-size system)

Line 228: <i data-lucide="lock"></i>  (same — leave as-is)

Line 238: <i data-lucide="arrow-left" style="width: 14px;"></i>
      ->  <i data-lucide="arrow-left" class="icon-sm"></i>
```

- [ ] **Step 3: Manual verification**

```bash
cd backend
python app.py
```

Visit `http://127.0.0.1:5000/admin/login`. Check:
- [ ] Card renders identically to before (gradient top border, gold logo box, form fields,
      gradient button with hover-lift)
- [ ] "Secured Access" heading renders in Playfair Display
- [ ] Icons render correctly (shield-check large, user/lock in inputs, arrow-left in footer link)
- [ ] Submitting wrong credentials shows the error banner correctly styled
- [ ] Tab through the form — visible gold focus ring on inputs/button/link
- [ ] Browser console has no errors

- [ ] **Step 4: Commit**

```bash
git add backend/templates/admin/login.html
git commit -m "Migrate login.html to shared admin.css tokens, pin Lucide, standalone page"
```

---

### Task 4: Migrate `user_manual.html` and `edit-dynamic-section.html` (the other 2 duplicate-font pages)

**Files:**
- Modify: `backend/templates/admin/user_manual.html` (404 lines)
- Modify: `backend/templates/admin/edit-dynamic-section.html` (338 lines)

**Interfaces:**
- Consumes: Tasks 1A–1C's `admin.css` classes/tokens, Task 3's migration procedure.
- Produces: nothing new — these follow the standard `extends base.html` procedure (unlike
  `login.html` in Task 3, both of these **do** extend `base.html`, confirmed via
  `grep -n "extends" backend/templates/admin/user_manual.html backend/templates/admin/edit-dynamic-section.html`).

- [ ] **Step 1: For each file, run the discovery commands from Task 3's procedure**

```bash
grep -n "style=" backend/templates/admin/user_manual.html
grep -n "<style>\|font-family\|fonts.googleapis" backend/templates/admin/user_manual.html
grep -n "style=" backend/templates/admin/edit-dynamic-section.html
grep -n "<style>\|font-family\|fonts.googleapis" backend/templates/admin/edit-dynamic-section.html
```

- [ ] **Step 2: Apply the migration procedure to `user_manual.html`**

Since it extends `base.html`: delete its local Google Fonts `<link>` (the duplicate found via
the grep above) and its local `<style>` block's `font-family: 'Playfair Display', serif` rules
that only restate what `.font-display` now provides — replace those elements' classes with
`font-display` (combined with `heading-xl`/`heading-lg`/`heading-md` per the element's role, per
Tasks 1A–1C's typography scale) instead of a bespoke inline/`<style>`-block font-family rule. Replace
every inline `style="width:Npx"` icon sizing with `.icon-sm`/`.icon-md`/`.icon-lg` per the
Task 3 size mapping. Any remaining page-specific layout CSS specific to the manual's content
(step-by-step callouts, table-of-contents grid) stays in a trimmed local `<style>` block — this
page has genuinely unique content layout that isn't a duplicate of a shared component.

- [ ] **Step 3: Apply the migration procedure to `edit-dynamic-section.html`**

Same approach: delete the duplicate font `<link>`, replace `font-family: 'Playfair Display'`
usage with `.font-display`, replace inline icon sizing with the icon classes, replace any
`<style>`-block button/card/form/table definitions that duplicate Tasks 1A–1C's components with the
shared classes, leave genuinely page-specific rules (e.g. the section-preview grid unique to
this page) in a trimmed local block.

- [ ] **Step 4: Manual verification (both pages)**

```bash
cd backend
python app.py
```

Visit `/admin/manual` and `/admin/edit-dynamic-section/<id>` (pick any existing section id from
`/admin/dynamic-section`, or skip this page's live check if no sections exist yet and note that
in the commit). Check each against the Task 2 Step 6 checklist adapted per page: page renders
correctly, Playfair Display shows only on the page's `<h1>`/heading elements that had it before,
icons consistent, no console errors, visible focus ring on interactive elements.

- [ ] **Step 5: Commit**

```bash
git add backend/templates/admin/user_manual.html backend/templates/admin/edit-dynamic-section.html
git commit -m "Migrate user_manual.html and edit-dynamic-section.html to shared admin.css"
```

---

### Tasks 5–18: Migrate the remaining 14 admin templates

Each of the following pages extends `base.html` and did **not** have its own duplicate font
`<link>` — apply the Task 3 migration procedure (discovery greps -> icon class replacement ->
replace shared-component inline/`<style>`-block CSS with Tasks 1A–1C's classes -> delete the local
`<style>` block entirely once nothing page-specific remains, or trim it to only genuine one-offs
-> manual verification -> commit). One task per file so each is independently reviewable; work
them in this order (smallest file first):

- **Task 5:** `backend/templates/admin/edit-segment.html` (256 lines) — verify at
  `/admin/edit-segment/<id>`
- **Task 6:** `backend/templates/admin/all-data-view.html` (281 lines) — verify at
  `/admin/all-data-view`
- **Task 7:** `backend/templates/admin/user-management.html` (311 lines) — verify at
  `/admin/users`
- **Task 8:** `backend/templates/admin/edit-category.html` (334 lines) — verify at
  `/admin/edit-category/<id>`
- **Task 9:** `backend/templates/admin/contact-inquiries.html` (336 lines) — verify at
  `/admin/contact-inquiries`
- **Task 10:** `backend/templates/admin/edit-subcategory.html` (336 lines) — verify at
  `/admin/edit-subcategory/<id>`
- **Task 11:** `backend/templates/admin/dashboard.html` (342 lines) — verify at
  `/admin/dashboard`; this page's stat tiles should migrate to `.stat-card`/`.stat-value`/
  `.stat-label`/`.stat-icon` from Tasks 1A–1C specifically (the spec calls this out as formalizing
  what's currently bespoke to this page)
- **Task 12:** `backend/templates/admin/add-subcategory.html` (365 lines) — verify at
  `/admin/add-subcategory`
- **Task 13:** `backend/templates/admin/add-segment.html` (393 lines) — verify at
  `/admin/add-segment`
- **Task 14:** `backend/templates/admin/edit-product.html` (402 lines) — verify at
  `/admin/edit-product/<id>`
- **Task 15:** `backend/templates/admin/add-product.html` (496 lines) — verify at
  `/admin/add-product`
- **Task 16:** `backend/templates/admin/import-excel.html` (517 lines) — verify at
  `/admin/import-excel`
- **Task 17:** `backend/templates/admin/add-category.html` (522 lines) — verify at
  `/admin/add-category`
- **Task 18:** `backend/templates/admin/dynamic-section.html` (555 lines) — verify at
  `/admin/dynamic-section`

**Files (per task):**
- Modify: the one template listed for that task.

**Interfaces:**
- Consumes: Tasks 1A–1C's `admin.css` classes/tokens, Task 3's migration procedure.
- Produces: nothing new — these are leaf tasks.

For each task:

- [ ] **Step 1:** Run the discovery greps from Task 3's procedure against the file.
- [ ] **Step 2:** Apply the 7-point migration procedure from Task 3.
- [ ] **Step 3:** Start the dev server, log in, visit the page listed above, run the Task 2
  Step 6 checklist (adapted: sidebar/topbar checks already covered by Task 2, focus on this
  page's own content — tables use `.table`/`.table-actions`/`.table-empty` where applicable,
  forms use `.form-group`/`.form-input`/etc., buttons use `.btn` + intent/size classes, badges
  use `.badge-*`, icons consistent, no console errors, visible focus ring).
- [ ] **Step 4:** Repo-wide check after this page: `grep -n "style=" backend/templates/admin/<file>`
  — confirm every remaining hit is a genuine page-specific one-off (per the governance rule),
  not something that should have used a Tasks 1A–1C class.
- [ ] **Step 5:** Commit with a message naming the file, e.g.:

```bash
git add backend/templates/admin/dashboard.html
git commit -m "Migrate dashboard.html to shared admin.css, formalize stat tiles"
```

---

### Task 19: Repo-wide final verification

**Files:**
- None modified — verification only.

**Interfaces:**
- Consumes: the fully migrated state from Tasks 1–19.

- [ ] **Step 1: Confirm no page bypasses the shared system**

```bash
grep -rn "fonts.googleapis" backend/templates/admin/*.html
```

Expected: only `base.html` and `login.html` (the one standalone page) have a Google Fonts
`<link>`. Every other page should have zero matches.

```bash
grep -rln "lucide@latest" backend/templates/admin/*.html
```

Expected: no matches (both `base.html` and `login.html` now pin `1.27.0`).

- [ ] **Step 2: Visual sweep at 125% browser zoom**

Pick 4 representative pages (dashboard, a form page like add-product, a table page like
all-data-view, and login) and reload each at 125% browser zoom. Confirm no overlapping text,
no cut-off buttons, no broken card layouts.

- [ ] **Step 3: Full keyboard-navigation pass**

On `/admin/dashboard`, tab through the entire page (sidebar links, topbar controls, page
content) without touching the mouse. Confirm every interactive element shows the gold
focus-visible ring and nothing is unreachable.

- [ ] **Step 4: Update `TODO.md`**

Add a line under the existing "Fixed" history noting the admin UI polish pass is complete,
following the same format as prior entries in that file.

- [ ] **Step 5: Final commit**

```bash
git add TODO.md
git commit -m "Complete admin panel UI polish pass — shared design system across all 18 templates"
```
