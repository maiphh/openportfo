# BL-017 — Global draggable chat bubble

| Field | Value |
|-------|-------|
| **ID** | `BL-017` |
| **Title** | Accessible floating bubble and responsive chat panel |
| **Priority** | `P1` |
| **Status** | `done` |
| **Owner (Eng)** | Eng |
| **Related** | `BL-016` |

## Scope

- Mount the widget from the root layout so it is available on every page.
- Clicking or keyboard activation toggles an accessible dialog panel.
- Pointer dragging starts only after a small threshold, clamps to the viewport,
  survives resize without leaving the viewport, and persists locally.
- The panel adapts to narrow viewports and supports Escape-to-close.

## Verification

- Manual keyboard/pointer/resize checks in the root layout.
- Position is kept in a versioned local-storage key with safe failure handling.
