# Admin Panel UI Polish — Design

Status: Approved (2026-07-28), revised after spec review (2026-07-28)
Scope: all templates under `backend/templates/admin/` — the 17 pages plus the `base.html` shell
they extend. Public storefront (`backend/templates/*.html` outside `admin/`) is explicitly out
of scope for this spec.

## Problem

The admin panel lacks visual consistency and a coherent design system:

- Every page under `backend/templates/admin/` declares its own `<style>` block instead of
  sharing one. Buttons, cards, tables, and badges are each independently redefined per page,
  with small differences.
- Typography lacks a defined hierarchy: `base.html` loads only Inter; `login.html`,
  `user_manual.html`, and `edit-dynamic-section.html` separately pull in Playfair Display for
  headings via their own duplicated Google Fonts `<link>`. The other 14 pages never get it —
  this reads as inconsistent, not as an intentional type system.
- Icons are Lucide (`data-lucide="..."`) everywhere already — the library choice is fine — but
  every icon is sized with an inline `style="width: Npx"`, independently defined with no shared
  scale, and the script tag pulls `lucide@latest` (unpinned, can change appearance/behavior
  without warning).
- Spacing is a set of independently defined inline px values per page, no shared scale.
- No design tokens exist for radius, shadow, transition, or z-index either — each page picks
  its own when it needs one.

## Non-goals

- No palette change — keep `--lux-gold` / `--lux-navy` and the existing CSS custom properties.
- No layout/structure change — sidebar nav, page structure, and route behavior stay as-is.
- No change to the public storefront.
- No new JS dependencies.
- Not a Tailwind-style utility framework — a small, hand-picked utility layer only (~20 classes),
  enough to eliminate repeated CSS, not a full atomic-CSS system.

## Design

### 1. `admin.css` — a small design system, not a dumping ground

New file: `backend/static/css/admin.css`, linked once from `admin/base.html`'s `<head>`.
`base.html` itself keeps almost no CSS after migration (see §5). Organized in this order,
top to bottom in the file:

1. **Tokens** (`:root`)
2. **Reset additions** (box-sizing, focus-visible baseline, etc.)
3. **Typography** (type scale + font utilities)
4. **Layout primitives** (stack/cluster/grid)
5. **Components** (sidebar, topbar, cards, buttons, tables, badges, stat cards)
6. **Forms**
7. **Utilities**
8. **Responsive** (breakpoint overrides, kept near the bottom so they win the cascade)

#### Tokens

```
Color:      existing --lux-gold / --lux-gold-dark / --lux-navy / --lux-bg / --lux-border /
            --lux-text-primary / --lux-text-secondary / --lux-success / --lux-danger
            (moved from base.html's inline <style>, not duplicated)
Spacing:    --space-1 (4px) … --space-8 (48px), 4px base unit — matches the 4/8px steps
            already visible in current inline styles
Radius:     --radius-sm / --radius-md / --radius-lg
Shadow:     --shadow-sm / --shadow-md / --shadow-lg
Transition: --transition-fast / --transition-normal
Z-index:    --z-sidebar / --z-dropdown / --z-modal
Layout:     --content-max-width, --border-light
```

#### Layout primitives

`.stack` (vertical flex + gap), `.cluster` (horizontal flex, wrap + gap), `.grid`, `.grid-2`,
`.grid-3` (CSS grid with a shared gap token) — replace the repeated
`display:flex; gap:16px` / `display:grid; gap:24px` one-offs scattered per page.

#### Components

- **Buttons:** `.btn` base + `.btn-primary` / `.btn-danger` / `.btn-ghost` for intent,
  `.btn-sm` / `.btn-md` / `.btn-lg` for size, `.btn-icon` for icon-only buttons.
- **Cards:** `.card`, plus `.stat-card` / `.stat-value` / `.stat-label` / `.stat-icon` as a
  formalized version of the dashboard's stat tiles (currently bespoke to `dashboard.html`).
- **Tables:** `.table` with `thead`/`tbody`/`th`/`td` rules, `.table-actions` (the per-row
  action-button cluster), `.table-empty` (empty-state row).
- **Badges:** `.badge` base + `.badge-success` / `.badge-warning` / `.badge-danger` /
  `.badge-info` / `.badge-neutral`.
- **Icons:** `.icon-sm` (16px) / `.icon-md` (18px) / `.icon-lg` (22px), each with
  `display:inline-flex; align-items:center; justify-content:center` so sizing and vertical
  alignment are both fixed by the same class.
- **Typography:** `.font-display` (Playfair Display 700 — see §2), `.heading-xl` /
  `.heading-lg` / `.heading-md`, `.text-muted`, `.text-small` — pages style headings/labels
  through these instead of raw `h1`/`h2`/inline styles.

#### Forms

`.form-group`, `.form-label`, `.form-input`, `.form-select`, `.form-textarea`,
`.form-checkbox`, `.form-help`, `.form-error`, `.form-row` (label+input pairs laid out
horizontally where a page needs it).

#### Utilities

A small hand-picked set (~20 classes) covering what's actually repeated today:
spacing (`.mt-2`, `.mt-4`, `.mb-2`, `.mb-4`, `.gap-2`, `.gap-4`), layout (`.flex`,
`.flex-between`, `.hidden`, `.w-full`), text (`.text-center`). Not a general-purpose
utility framework — only what removes real, observed duplication.

### 2. Typography

- `admin/base.html` keeps the single Google Fonts `<link>`, extended to include Playfair
  Display alongside Inter: `family=Playfair+Display:wght@700&family=Inter:wght@400;500;600;700;800`.
- The 3 pages currently loading their own duplicate Google Fonts `<link>` (`login.html`,
  `user_manual.html`, `edit-dynamic-section.html`) drop their local `<link>` — inherited from
  `base.html` now.
- `.font-display` (Playfair Display, 700) applies to exactly two places: each page's main
  `<h1>` page title (rendered by `base.html`'s shared page-header block), and the login
  screen's brand wordmark. Everywhere else stays Inter — the one deliberate use of the serif,
  not sprinkled elsewhere.

### 3. Icons

- `base.html`'s `<script src="https://unpkg.com/lucide@latest">` pinned to the
  currently-resolved version (checked at implementation time) so the icon set can't change out
  from under the admin panel silently.
- Every `<i data-lucide="...">` across all pages gets `.icon-sm` / `.icon-md` / `.icon-lg`
  instead of an inline `style="width:Npx"`. Mapping: sidebar nav icons → `.icon-md` (18px,
  matches current), topbar/small inline icons → `.icon-sm` (16px), any larger decorative icon →
  `.icon-lg`.

### 4. Accessibility

No behavior changes in this pass, but the shared system bakes in a floor:

- Visible keyboard focus via `:focus-visible` on all interactive elements (buttons, links,
  form inputs) — currently inconsistent/absent per page.
- Icon-only buttons (`.btn-icon`) carry an accessible label (`aria-label` or visually-hidden
  text), not just the bare icon.
- Form controls keep their `<label for>` association (audit during migration — some pages may
  be missing this today).
- Color contrast preserved at current `--lux-*` values (no palette change, so no regression
  risk here).
- Minimum ~44×44px click target on primary actions where practical.

### 5. Responsive behavior

Unchanged in substance, documented explicitly so future edits know what's intentional:

- Sidebar collapse behavior stays as currently implemented.
- `.grid-2` / `.grid-3` / card layouts stack to a single column below 1024px.
- Tables scroll horizontally on narrow viewports rather than compressing columns.
- Forms remain single-column below tablet width.

### 6. Rollout

1. Build `admin.css` in the section order above (tokens → reset → typography → layout →
   components → forms → utilities → responsive), wire into `base.html`, add Playfair Display,
   pin the Lucide version.
2. Migrate `base.html` itself (sidebar, topbar, page-header) to the new classes — after this
   step `base.html` carries almost no page-level CSS of its own.
3. Migrate the remaining 17 templates one at a time, each a self-contained diff: replace
   duplicated `<style>` rules with shared classes/utilities, replace inline icon sizing, then
   run the visual regression checklist (§Testing) against that page before moving to the next.
4. Delete now-dead per-page CSS once its page is migrated — no lingering duplicate rules.

Going forward: **no new inline styles are permitted unless the style is truly page-specific and
cannot reasonably be represented by an existing component, primitive, or utility.** This is the
rule that keeps the drift from recurring.

No database, route, or JS-behavior changes anywhere in this pass — purely template/CSS.

## Testing / Verification

Per-page visual regression checklist, run after migrating each page (logged in as admin):

- [ ] Sidebar renders correctly, active-state highlighting intact
- [ ] Breadcrumbs (where present) render correctly
- [ ] Page title uses `.font-display`, rest of page uses Inter
- [ ] Tables render with consistent row/column spacing, `.table-actions` aligned
- [ ] Forms render with consistent label/input spacing
- [ ] Buttons show correct intent color + consistent sizing
- [ ] Alerts/flash messages render correctly
- [ ] Icons render at consistent sizes, no layout shift vs. before
- [ ] Keyboard-tab through the page shows visible focus on every interactive element

Repo-wide, after all pages migrated:

- `grep -n "font-family:\|style=\"width:.*px" backend/templates/admin/*.html` returns nothing
  outside the legitimate page-specific one-offs identified during migration.
- No console errors from the pinned Lucide version (icons still render).

## Risks

- Pinning Lucide to a specific version means future icon additions need the pin bumped
  deliberately — acceptable tradeoff for stability.
- Trimming per-page `<style>` blocks risks missing a page-specific rule that looked generic but
  wasn't — mitigated by migrating one page at a time with the visual regression checklist before
  moving to the next, not a single big-bang sweep.
- A larger token/component set (vs. a minimal one) costs more upfront build time — accepted
  because this is a CMS that will keep growing pages, and the alternative is repeating this
  audit again in a year.
