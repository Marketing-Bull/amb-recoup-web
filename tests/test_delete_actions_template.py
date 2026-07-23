"""BUG-03: mileage and expense entries had no delete action, while time entries
did (`/time/{id}/delete`). Native app allows deleting any entry via swipe —
inconsistent CRUD surface across the three entry types. This adds `/{id}/delete`
routes to `mileage.py` and `expenses.py` (mirroring `time_entries.py`) and a
"Delete" button + confirm() prompt to all three list templates for a consistent
CRUD surface.

Renders the list templates directly (no Supabase/HTTP dependency) to verify the
delete form/button is present and posts to the correct endpoint.
"""
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))


def _render(template_name, entries):
    tpl = env.get_template(template_name)
    request = SimpleNamespace(url=SimpleNamespace(path="/"))
    user = {"email": "test@example.com", "is_superuser": False}
    return tpl.render(entries=entries, user=user, request=request, categories=[])


def test_time_list_has_delete_action():
    entry = {
        "id": "t1", "date": "2026-07-20T00:00:00", "hours": 2.0, "rate": 50.0,
        "billable": True, "details": "", "clients": None, "projects": None,
    }
    html = _render("time/list.html", [entry])
    assert 'action="/time/t1/delete"' in html
    assert "confirm(" in html
    assert "btn-danger" in html


def test_mileage_list_has_delete_action():
    entry = {
        "id": "m1", "date": "2026-07-20T00:00:00", "start_address": "A",
        "end_address": "B", "purpose": "", "miles": 10.0, "total_miles": 10.0,
        "round_trip": False, "billable": True, "clients": None, "projects": None,
    }
    html = _render("mileage/list.html", [entry])
    assert 'action="/mileage/m1/delete"' in html
    assert "confirm(" in html
    assert "btn-danger" in html


def test_expenses_list_has_delete_action():
    entry = {
        "id": "e1", "date": "2026-07-20T00:00:00", "amount": 12.5,
        "category": "software", "vendor": "", "billable": True,
        "recurring": "none", "clients": None, "projects": None,
    }
    html = _render("expenses/list.html", [entry])
    assert 'action="/expenses/e1/delete"' in html
    assert "confirm(" in html
    assert "btn-danger" in html
