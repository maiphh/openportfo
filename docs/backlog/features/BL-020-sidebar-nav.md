# BL-020 — Collapsible sidebar navigation

| Field | Value |
|-------|--------|
| **ID** | `BL-020` |
| **Title** | Replace top navbar with a redesigned, collapsible sidebar; user avatar pinned bottom-left |
| **Priority** | `P0` |
| **Status** | `done` |
| **Owner (BA)** | Orchestrator |
| **Owner (Eng)** | Luna implementer |
| **Requested by** | Product |
| **Related PRD / sprint** | sprint-05; depends on BL-019 (brand), BL-022 (avatar) |
| **Created** | 2026-08-23 |
| **Ready date** | 2026-08-23 |
| **Done date** | 2026-08-23 |

---

## 1. Problem / user value

The app currently uses a sticky top header (BrandLogo + NavItems + Currency/Language selects + UserMenu). Product wants an app-shell with a **left sidebar** — the standard layout for dashboards — that is **collapsible** to an icon rail, with the **user avatar pinned at the bottom-left**.

---

## 2. User story

As a **user**, I want **a collapsible sidebar with my avatar at the bottom**, so that **navigation stays accessible while maximizing content space and my account is always one click away**.

---

## 3. Scope

### In scope

- New `Sidebar` component replacing `Header` in the app shell (`app/layout.tsx`): brand at top, nav items, search trigger, avatar + user chip pinned at bottom.
- **Redesigned** visuals (not a straight port of navbar styling): active-item treatment, hover states, icon+label rows, collapse affordance (chevron button).
- **Collapsible**: expanded ↔ icon-only rail; collapse state persisted in localStorage; tooltip or `title` on rail icons.
- Avatar at bottom-left opens the **user settings modal** (BL-021) when clicked; sign-in/sign-out still reachable from the avatar area.
- Mobile (< `sm`): sidebar becomes an overlay drawer with a hamburger trigger; content untouched.
- SearchDialog (Cmd/Ctrl+K global listener) still works; trigger moved into sidebar.
- `NavItems` reuse/adaptation: Market submenu becomes expandable group (or flyout) in sidebar.

### Out of scope

- Backend changes; page content layout beyond the shell; ChatWidget (stays floating, must not overlap sidebar).

---

## 4. Behaviour

### Happy path

1. User loads app → sidebar expanded (or last-saved state) on desktop; content shifted right.
2. Click collapse chevron → rail collapses to icons; state persists across reloads.
3. Click avatar (bottom-left) → user settings modal opens (BL-021).
4. On mobile, hamburger opens overlay drawer; selecting a link navigates and closes the drawer.

### Edge cases / errors

- No stored preference → default expanded on desktop, closed on mobile.
- Signed-out state → avatar shows guest treatment; click still opens settings modal (theme/language/currency) with sign-in action available.
- Keyboard: sidebar links focusable; collapse button has `aria-expanded`; drawer closes on Escape.

### UX notes

- Screens / routes: all (shell-level change).
- Sidebar width: expanded ~240px, rail ~64px (SA to finalize).

---

## 5. Acceptance criteria

- [ ] No top navbar on desktop; navigation lives in a left sidebar with avatar bottom-left.
- [ ] Collapse/expand works, persists across reloads, and rail shows icons with accessible labels.
- [ ] Mobile drawer works and closes on navigate/Escape.
- [ ] Cmd/Ctrl+K still opens SearchDialog.
- [ ] Unit tests: sidebar renders nav items, collapse toggling + persistence, avatar opens settings modal, drawer behavior.
- [ ] All existing NavItems/UserMenu tests updated or replaced, whole suite green.

---

## 6. Data & integrations

| Concern | Decision |
|---------|----------|
| Source of truth | localStorage `openportfo.sidebar.collapsed` |
| New / changed APIs | none |
| Auth required? | no |

---

## 7. Affected surfaces

| Layer | Paths / components |
|-------|--------------------|
| Frontend | `app/layout.tsx`, new `components/Sidebar.tsx` (+ subcomponents), `Header.tsx` removed/retired, `NavItems.tsx` adapted, `BrandLogo.tsx`, `globals.css` shell styles |
| Backend API | none |
| Docs / tests | sidebar tests, updated NavItems/UserMenu tests |

---

## 8. Dependencies & risks

- Depends on: BL-019 (brand text), BL-022 (avatar), BL-021 (modal target).
- Risks: static export (`output: "export"`) — no server features; SSR-safe localStorage handling (hydration mismatch) must use mounted-guards.

---

## 9. Open questions

| # | Question | Status | Answer |
|---|----------|--------|--------|
| 1 | Keep `Header.tsx` for anything? | open | SA decision — likely delete, mobile drawer replaces its role. |

---

## 10. Clarification log

| Date | Question / decision | Outcome |
|------|---------------------|---------|
| 2026-08-23 | Batch created | — |
