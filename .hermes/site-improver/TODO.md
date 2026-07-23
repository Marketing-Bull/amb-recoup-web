# Feature Parity TODO — amb-recoup-web vs. amb-recoup (native SwiftUI app)

Reference app: https://github.com/Marketing-Bull/amb-recoup (SwiftUI/SwiftData/CloudKit,
iOS/iPad/Mac). This file tracks parity gaps found by diffing the two codebases on
2026-07-23. One item per night, PR per item, smallest viable change. See the
`nightly-site-improver` skill for workflow rules.

Priority order: Bug fixes > Data integrity > Core feature parity > UX parity > Nice-to-have.

## 🔴 Bugs found during audit (fix first)
- [x] **BUG-01** — `templates/time/form.html` line 5: malformed Jinja/HTML —
      `{% if entry %}Edit Time Entry{% else %}Log Time</h1>` is missing the closing
      `{% endif %}` before `</h1>`, and the opening `<h1 class="page-title">` tag has
      no matching close on the "else" branch. Renders broken HTML on the "new time
      entry" page. Compare with the correct pattern in `templates/expenses/form.html`
      line 5 and `templates/mileage/form.html` line 5.
      ✅ DONE 2026-07-23 (audit-flip) — already fixed in commit a21180e (same night
      this TODO.md was seeded); the checkbox was never flipped. Re-verified
      2026-07-23 by rendering `time/form.html` directly via Jinja2 for both the
      new-entry and edit-entry states: `<h1 class="page-title">Log Time</h1>`
      renders correctly, no unterminated `{% if %}` block, no broken HTML.
- [x] **BUG-02** — Rate is NOT locked at save for time entries. Native app resolves
      the rate once via `RateResolver` and stores it on the entry permanently
      (`RateResolver.swift`: "Resolved once at save and locked on the entry; never
      recomputed"). Web app's `create_time` resolves the rate correctly, but
      `update_time` in `app/routers/time_entries.py` does NOT include `rate` in the
      update payload — meaning if a client's hourly_rate changes after entries exist,
      editing an old entry's date/hours will silently keep the stale rate (fine) BUT
      there's no way to see what rate was used at edit time, and the edit form
      (`templates/time/form.html`) doesn't display the locked rate at all. Add a
      read-only "Rate: $X/hr (locked)" display to the edit form, sourced from
      `entry.rate` — currently invisible to the user.
      ✅ DONE 2026-07-23 — added a read-only "Rate: $X/hr (locked)" field to
      `templates/time/form.html`, shown only when editing an existing entry,
      sourced from `entry.rate`. `update_time`'s payload correctly still excludes
      `rate` (confirms the lock — this item was about visibility, not behavior).
      Covered by `tests/test_time_form_template.py` (direct Jinja2 render test).
- [x] **BUG-03** — No delete action for mileage or expense entries (time entries have
      `/time/{id}/delete` in `time_entries.py` but `mileage.py` and `expenses.py` have
      no equivalent route or UI button). Native app allows deleting any entry via swipe.
      Inconsistent CRUD surface across the three entry types.
      ✅ DONE 2026-07-23 — added `POST /{entry_id}/delete` to `mileage.py` and
      `expenses.py` (mirroring the existing `delete_time` handler: org-scoped
      `.eq("organization_id", ...)` delete, redirect to the list page), plus a
      "Delete" button with a `confirm()` prompt on all three list templates
      (`time/list.html`, `mileage/list.html`, `expenses/list.html`) so CRUD is
      now consistent across time/mileage/expenses. Covered by new template
      render tests in `tests/test_delete_actions_template.py`.

## 🟡 Core feature parity gaps
- [ ] **PARITY-01** — Mileage: no "repeat a recent trip" quick-fill. Native app's
      `RecentTripPicker.swift` + `Services/Recents.swift` let a user one-tap-recreate
      their last N trips (start/end address, purpose) without retyping. Web app has
      `/mileage/{id}/duplicate` (creates today's copy server-side) but no UI surfacing
      "recent trips" as tappable chips on the New Trip form — parity requires exposing
      the last 5 distinct (start,end,purpose) combos as clickable pills that fill the form.
- [ ] **PARITY-02** — Time: no "recent client/project pair" quick-fill and no smart
      default prefill. Native app's `RecentPairChips.swift` + form-prefill behavior
      auto-selects the last-used client + project on the New Time Entry form. Web
      app always defaults both dropdowns to "None". Add: prefill last-used
      client_id/project_id (session or most-recent-entry lookup) as the default
      selected `<option>` on `time/form.html`'s New form.
- [ ] **PARITY-03** — Expenses: no category quick-grid. Native app's
      `CategoryGrid.swift` gives a tappable icon grid instead of a `<select>` dropdown,
      and defaults to the last-used category. Web app's `expenses/form.html` uses a
      plain `<select>` with no smart default. Minimum parity: default the category
      `<select>` to the last-used category for the org (not always "other").
- [ ] **PARITY-04** — Dashboard: date-range picker parity is otherwise solid
      (today/this_week/this_month/last_month/this_year/all — matches
      `DateRangePreset` in the native app) — no action needed here, confirmed parity.
- [ ] **PARITY-05** — No CRUD delete UI for Clients or Projects (only archive).
      This actually MATCHES the native app's "archive instead of delete" design
      intent (README: "archive instead of delete") — NOT a gap, do not implement.
      Documented here so a future run doesn't mistakenly "fix" this.

## 🟢 UX parity (lower priority, larger effort)
- [ ] **UX-01** — Mileage: no round-trip live-preview of total miles before submit
      (native app likely shows doubled total inline; verify against `MileageFormView.swift`
      before implementing — needs a small JS listener on the round_trip checkbox +
      miles input to show "Total: X mi" without a page reload).
- [ ] **UX-02** — No empty-state icons/copy matching native app's
      `EmptyStateView` tone across all list pages — audit `templates/*/list.html`
      empty states for consistency (some have icons, verify all do).

## Notes
- Web app is intentionally multi-tenant SaaS (native app is single-user local +
  CloudKit) — org/multi-tenancy has NO native-app equivalent and is NOT a gap to
  reconcile; it's additive scope specific to the web product.
- Native app has no auth/login (local device app) — web app's auth system also has
  no parity target; not tracked here.
- CSV export parity: web app's `reports.py` exports clients/projects/time/expenses/
  mileage — matches native app's per-feature `CSVExporter.swift` — CONFIRMED PARITY,
  no gap.
