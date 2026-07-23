"""PARITY-03: the New Expense form should default the Category select to
the org's most-recently-used expense category, mirroring the native app's
CategoryGrid smart-default behavior (native app defaults the category grid
selection to the last-used category rather than always falling back to
"other"). This renders the template directly (no Supabase/HTTP dependency)
to verify the prefill behavior, and confirms the Edit form is unaffected
(locked to entry values).
"""
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))

CATEGORIES = ["travel", "meals", "supplies", "software", "other"]


def _render(entry, recent_category=None):
    tpl = env.get_template("expenses/form.html")
    request = SimpleNamespace(url=SimpleNamespace(path="/expenses"))
    user = {"email": "test@example.com", "is_superuser": False}
    return tpl.render(
        entry=entry, clients=[], projects=[], categories=CATEGORIES,
        user=user, request=request, recent_category=recent_category,
    )


def test_new_expense_form_prefills_recent_category():
    html = _render(None, recent_category="software")
    assert '<option value="software" selected%>Software</option>' in html
    assert '<option value="other" selected%>Other</option>' not in html
    assert '<option value="travel" selected%>Travel</option>' not in html


def test_new_expense_form_defaults_to_other_when_no_recent_history():
    html = _render(None, recent_category=None)
    assert '<option value="other" selected%>Other</option>' in html
    assert '<option value="travel" selected%>Travel</option>' not in html


def test_edit_form_ignores_recent_prefill_uses_entry_category():
    entry = {
        "id": "abc123",
        "date": "2026-07-20T00:00:00",
        "amount": 42.0,
        "category": "meals",
        "vendor": "Cafe",
        "details": "",
        "billable": False,
        "recurring": "none",
        "client_id": None,
        "project_id": None,
        "receipt_url": None,
    }
    # Even if recent_category is passed, the entry's own category wins.
    html = _render(entry, recent_category="software")
    assert '<option value="meals" selected%>Meals</option>' in html
    assert '<option value="software" selected%>Software</option>' not in html
    assert '<option value="other" selected%>Other</option>' not in html
