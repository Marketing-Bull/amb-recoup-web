"""PARITY-01: no "repeat a recent trip" quick-fill on the mileage New Trip form.
Native app's `RecentTripPicker.swift` + `Services/Recents.swift` let a user
one-tap-recreate their last N distinct trips (start/end address, purpose,
miles, round-trip) without retyping. This adds `recent_trips()` (mirrors
`Recents.recentTrips`) to `app/routers/mileage.py`, wires it into
`new_mileage_form`, and renders distinct trips as clickable chips on
`templates/mileage/form.html` that JS-fill the form on click.

Covers both the dedup/ordering logic (recent_trips()) and the template
render (chips appear on the New form, not on the Edit form).
"""
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

from app.routers.mileage import recent_trips

env = Environment(loader=FileSystemLoader("templates"))


def _render(entry, recent_trips_list, clients=None, projects=None):
    tpl = env.get_template("mileage/form.html")
    request = SimpleNamespace(url=SimpleNamespace(path="/mileage/new"))
    user = {"email": "test@example.com", "is_superuser": False}
    return tpl.render(
        entry=entry, recent_trips=recent_trips_list,
        clients=clients or [], projects=projects or [],
        user=user, request=request,
    )


def test_recent_trips_dedupes_by_route_and_keeps_most_recent_first():
    entries = [
        {"start_address": "A", "end_address": "B", "purpose": "Site visit",
         "miles": 10.0, "round_trip": False, "created_at": "2026-07-01T00:00:00"},
        {"start_address": "C", "end_address": "D", "purpose": "Client meeting",
         "miles": 5.0, "round_trip": True, "created_at": "2026-07-10T00:00:00"},
        # duplicate of the first trip (same start/end/round_trip/miles), older usage skipped
        {"start_address": "A", "end_address": "B", "purpose": "Site visit",
         "miles": 10.0, "round_trip": False, "created_at": "2026-06-01T00:00:00"},
    ]
    result = recent_trips(entries)
    assert len(result) == 2
    # most recent distinct trip first
    assert result[0]["start_address"] == "C"
    assert result[1]["start_address"] == "A"


def test_recent_trips_respects_limit():
    entries = [
        {"start_address": f"S{i}", "end_address": "E", "purpose": "", "miles": 1.0,
         "round_trip": False, "created_at": f"2026-07-{i:02d}T00:00:00"}
        for i in range(1, 11)
    ]
    result = recent_trips(entries, limit=3)
    assert len(result) == 3


def test_new_trip_form_shows_recent_trip_chips():
    trips = [{"start_address": "Home", "end_address": "Client Office",
              "purpose": "Meeting", "miles": 12.5, "round_trip": True,
              "client_id": "c1", "project_id": None}]
    html = _render(None, trips)
    assert "Repeat a Recent Trip" in html
    assert "recent-trip-chip" in html
    assert 'data-start="Home"' in html
    assert 'data-end="Client Office"' in html
    assert 'data-round-trip="true"' in html


def test_edit_trip_form_hides_recent_trip_chips():
    entry = {"id": "m1", "date": "2026-07-20", "start_address": "A", "end_address": "B",
              "purpose": "", "miles": 5.0, "round_trip": False, "billable": True,
              "client_id": None, "project_id": None}
    trips = [{"start_address": "Home", "end_address": "Office", "purpose": "",
              "miles": 3.0, "round_trip": False, "client_id": None, "project_id": None}]
    html = _render(entry, trips)
    assert "Repeat a Recent Trip" not in html


def test_new_trip_form_no_chips_when_no_history():
    html = _render(None, [])
    assert "Repeat a Recent Trip" not in html
