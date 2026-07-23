"""PARITY-02: the New Time Entry form should default the Client/Project
selects to the org's most-recently-used client/project pair, mirroring the
native app's RecentPairChips smart-default behavior. This renders the
template directly (no Supabase/HTTP dependency) to verify the prefill
behavior, and confirms the Edit form is unaffected (locked to entry values).
"""
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))

CLIENTS = [{"id": "c1", "name": "Acme Co"}, {"id": "c2", "name": "Beta LLC"}]
PROJECTS = [
    {"id": "p1", "name": "Website Redesign", "client_id": "c1"},
    {"id": "p2", "name": "Mobile App", "client_id": "c2"},
]


def _render(entry, recent_client_id=None, recent_project_id=None):
    tpl = env.get_template("time/form.html")
    request = SimpleNamespace(url=SimpleNamespace(path="/time"))
    user = {"email": "test@example.com", "is_superuser": False}
    return tpl.render(
        entry=entry, clients=CLIENTS, projects=PROJECTS, user=user, request=request,
        recent_client_id=recent_client_id, recent_project_id=recent_project_id,
    )


def test_new_entry_form_prefills_recent_client_and_project():
    html = _render(None, recent_client_id="c2", recent_project_id="p2")
    # Beta LLC (c2) and Mobile App (p2) should be pre-selected.
    assert '<option value="c2" selected%>Beta LLC</option>' in html
    assert '<option value="p2" data-client="c2" selected%>Mobile App</option>' in html
    # The other client/project should NOT be selected.
    assert '<option value="c1" selected%>Acme Co</option>' not in html
    assert '<option value="p1" data-client="c1" selected%>Website Redesign</option>' not in html


def test_new_entry_form_defaults_to_none_when_no_recent_history():
    html = _render(None, recent_client_id=None, recent_project_id=None)
    assert '<option value="" selected%>None</option>' in html
    assert '<option value="c1" selected%>Acme Co</option>' not in html
    assert '<option value="c2" selected%>Beta LLC</option>' not in html


def test_edit_form_ignores_recent_prefill_uses_entry_values():
    entry = {
        "id": "abc123",
        "date": "2026-07-20T00:00:00",
        "hours": 2.5,
        "rate": 85.0,
        "billable": True,
        "details": "work",
        "client_id": "c1",
        "project_id": "p1",
    }
    # Even if recent_* is passed (edit route never passes it), entry values win.
    html = _render(entry, recent_client_id="c2", recent_project_id="p2")
    assert '<option value="c1" selected%>Acme Co</option>' in html
    assert '<option value="p1" data-client="c1" selected%>Website Redesign</option>' in html
    assert '<option value="c2" selected%>Beta LLC</option>' not in html
