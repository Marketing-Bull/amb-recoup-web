"""BUG-02: the time-entry edit form must show the locked rate, read-only.

Rate is resolved once at save (project override > client rate) and never
recomputed on edit — but until now the edit form gave the user no visibility
into what rate was actually saved on the entry. This renders the template
directly (no Supabase/HTTP dependency) to verify the read-only "Rate: $X/hr
(locked)" field appears on edit and is absent on the "new entry" form.
"""
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))


def _render(entry):
    tpl = env.get_template("time/form.html")
    request = SimpleNamespace(url=SimpleNamespace(path="/time"))
    user = {"email": "test@example.com", "is_superuser": False}
    return tpl.render(entry=entry, clients=[], projects=[], user=user, request=request)


def test_edit_form_shows_locked_rate():
    entry = {
        "id": "abc123",
        "date": "2026-07-20T00:00:00",
        "hours": 2.5,
        "rate": 85.0,
        "billable": True,
        "details": "work",
        "client_id": None,
        "project_id": None,
    }
    html = _render(entry)
    assert "$85.00/hr (locked)" in html
    assert 'readonly' in html
    assert 'disabled' in html


def test_new_entry_form_has_no_rate_field():
    html = _render(None)
    assert "locked" not in html
    assert "/hr" not in html
