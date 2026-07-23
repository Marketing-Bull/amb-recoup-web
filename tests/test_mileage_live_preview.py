r"""UX-01: Mileage form had no round-trip live-preview of total miles/cost
before submit. Native app's `MileageFormView.swift` shows an inline
`Text("\(Formatters.milesString(totalMiles)) \u2248 \(Formatters.currencyString(...))
@ \(Formatters.currencyString(mileageRate))/mi")` under the Miles/Round Trip
fields that updates live as the user types or toggles round trip.

This adds `get_mileage_rate(org_id)` to `app/routers/mileage.py` (reused
pattern from settings.py/dashboard.py: org's configured mileage_rate,
falling back to the 0.67 IRS-standard default), wires it into both
`new_mileage_form` and `edit_mileage_form`, and adds a small vanilla-JS
listener on the `miles` input + `round_trip` checkbox in
`templates/mileage/form.html` that updates a "Total: X mi \u2248 $Y @ $Z/mi"
preview without a page reload -- no server round-trip needed.

Covers the template render (rate is threaded into the JS constant and the
preview markup exists) via the direct-Jinja2-render recipe.
"""
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))


def _render(entry, mileage_rate=0.67, clients=None, projects=None, recent_trips=None):
    tpl = env.get_template("mileage/form.html")
    request = SimpleNamespace(url=SimpleNamespace(path="/mileage/new"))
    user = {"email": "test@example.com", "is_superuser": False}
    return tpl.render(
        entry=entry, mileage_rate=mileage_rate, recent_trips=recent_trips or [],
        clients=clients or [], projects=projects or [],
        user=user, request=request,
    )


def test_new_trip_form_includes_live_preview_markup():
    html = _render(None)
    assert 'id="miles-preview"' in html
    assert 'id="miles-preview-value"' in html
    assert "updateMilesPreview" in html


def test_new_trip_form_threads_org_mileage_rate_into_js():
    html = _render(None, mileage_rate=0.72)
    assert "const MILEAGE_RATE = 0.72;" in html


def test_new_trip_form_defaults_rate_when_missing():
    html = _render(None, mileage_rate=None)
    assert "const MILEAGE_RATE = 0.67;" in html


def test_edit_trip_form_also_includes_live_preview():
    entry = {"id": "m1", "date": "2026-07-20", "start_address": "A", "end_address": "B",
              "purpose": "", "miles": 5.0, "round_trip": False, "billable": True,
              "client_id": None, "project_id": None}
    html = _render(entry, mileage_rate=0.67)
    assert 'id="miles-preview"' in html
    assert "updateMilesPreview" in html


def test_recent_trip_chip_click_updates_preview():
    html = _render(None, recent_trips=[{
        "start_address": "Home", "end_address": "Office", "purpose": "Meeting",
        "miles": 12.5, "round_trip": True, "client_id": None, "project_id": None,
    }])
    assert "updateMilesPreview();" in html
