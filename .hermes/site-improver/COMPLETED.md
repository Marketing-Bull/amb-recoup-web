# Completed Feature-Parity Items

Log of nightly-improver runs against amb-recoup-web, tracking parity with the
native SwiftUI app (amb-recoup). One entry per shipped PR.

## 2026-07-23 — PR #2

- **BUG-01** — Audit-flip (no code change this run — already fixed in commit
  a21180e the same night the TODO.md was seeded). Malformed Jinja/HTML on
  `templates/time/form.html`'s "New Time Entry" title (`{% if %}` missing
  `{% endif %}` before `</h1>`) was already corrected; the checkbox was never
  flipped to `[x]`. Verified by direct Jinja2 render of both the new-entry and
  edit-entry states.
- **BUG-02** — Added a read-only "Rate: $X/hr (locked)" field to
  `templates/time/form.html`, shown only when editing an existing time entry,
  sourced from `entry.rate`. The rate is resolved once at save (project
  override > client rate, per `RateResolver` parity with the native app) and
  intentionally never recomputed on edit — `update_time` correctly omits
  `rate` from its update payload. This item closes the visibility gap: users
  previously had no way to see what rate was locked on an entry when editing
  it. Covered by a new test, `tests/test_time_form_template.py`, which renders
  the template directly via Jinja2 (no Supabase/HTTP dependency) and asserts
  the rate field appears on edit and is absent on the "new entry" form.
  Files: `templates/time/form.html`, `tests/test_time_form_template.py`.
  CI: ruff clean, bandit clean, pytest 6/6 passed (fresh venv).
- **BUG-03** — Added `POST /{entry_id}/delete` routes to `app/routers/mileage.py`
  and `app/routers/expenses.py`, mirroring the existing `delete_time` handler in
  `time_entries.py` (org-scoped `.eq("organization_id", ...)` delete, redirect to
  the list page). Added a "Delete" button with a `confirm()` prompt to all three
  list templates (`templates/time/list.html`, `templates/mileage/list.html`,
  `templates/expenses/list.html`) so time/mileage/expense entries now have a
  consistent CRUD surface (matching the native app's swipe-to-delete on any
  entry type). No Supabase schema change needed (existing tables already
  support delete). Files: `app/routers/mileage.py`, `app/routers/expenses.py`,
  `templates/time/list.html`, `templates/mileage/list.html`,
  `templates/expenses/list.html`, `tests/test_delete_actions_template.py` (new).
  CI: ruff clean, bandit clean, pytest 9/9 passed (fresh venv).

## 2026-07-23 — PR #2 (cont.)

- **PARITY-01** — Added a "Repeat a Recent Trip" quick-fill to the mileage
  New Trip form, matching the native app's `RecentTripPicker.swift` +
  `Services/Recents.swift`. `recent_trips()` in `app/routers/mileage.py`
  dedupes the org's mileage history by (start_address, end_address,
  round_trip, miles), most-recent-first, capped at 8. `new_mileage_form`
  fetches the org's last 50 entries and passes the distinct trips to the
  template. `templates/mileage/form.html` renders them as clickable chips
  (New Trip form only, hidden on Edit) that JS-fill start/end address,
  purpose, miles, round-trip checkbox, and client/project selects on click —
  no page reload, no new dependency. No Supabase schema change needed
  (reads existing `mileage_entries` columns only). Files:
  `app/routers/mileage.py`, `templates/mileage/form.html`,
  `tests/test_mileage_recent_trips.py` (new — 5 tests covering dedup
  ordering, limit, chip-render-on-New, chip-hidden-on-Edit,
  no-chips-when-no-history). CI: ruff clean, bandit clean, pytest 14/14
  passed (fresh venv).

## 2026-07-23 — PR #2 (cont. 2)

- **PARITY-02** — Added a smart client/project prefill to the New Time Entry
  form, matching the native app's `RecentPairChips.swift`. Added
  `most_recent_client_project(org_id)` to `app/routers/time_entries.py`,
  which looks up the org's most-recently-created `time_entries` row (by
  `created_at`) and returns its `client_id`/`project_id`. Wired into
  `new_time_form` only — the edit form (`edit_time_form`) is unchanged and
  continues to use the entry's own saved values. `templates/time/form.html`'s
  Client/Project `<select>` options now branch on `entry` (edit mode) vs.
  `recent_client_id`/`recent_project_id` (new mode), so a user starting a
  fresh time entry gets the same client+project pre-selected as their last
  entry, instead of always seeing "None". No Supabase schema change needed
  (reads existing `time_entries` columns only). Files:
  `app/routers/time_entries.py`, `templates/time/form.html`,
  `tests/test_time_form_recent_prefill.py` (new — 3 tests covering
  prefill-on-New, default-to-None-with-no-history, and
  edit-form-uses-entry-values-not-recent-prefill). CI: ruff clean, bandit
  clean, pytest 17/17 passed (fresh venv).

## 2026-07-23 — PR #2 (cont. 3)

- **PARITY-03** — Defaulted the Expense form's Category `<select>` to the
  org's last-used category, matching the native app's `CategoryGrid.swift`
  smart-default behavior (minimum-parity scope: only the smart default was
  implemented, not the tappable icon-grid UI itself, per the item's own
  "minimum parity" framing). Added `most_recent_category(org_id)` to
  `app/routers/expenses.py`, which looks up the org's most-recently-created
  `expenses` row (by `created_at`) and returns its `category`. Wired into
  `new_expense_form` only — the edit form (`edit_expense_form`) is unchanged
  and continues to use the entry's own saved category.
  `templates/expenses/form.html`'s category `<select>` options now branch on
  `entry` (edit mode) vs. `recent_category` (new mode, falling back to
  "other" when the org has no expense history yet), so a user starting a
  fresh expense gets their last-used category pre-selected instead of
  always seeing "Other". No Supabase schema change needed (reads existing
  `expenses` columns only). Files: `app/routers/expenses.py`,
  `templates/expenses/form.html`, `tests/test_expense_form_recent_category.py`
  (new — 3 tests covering prefill-on-New, default-to-other-with-no-history,
  and edit-form-uses-entry-category-not-recent-prefill). CI: ruff clean,
  bandit clean, pytest 20/20 passed (fresh venv).
