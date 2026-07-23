from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from decimal import Decimal
from app.auth import require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def resolve_rate(client_id: str | None, project_id: str | None, org_id: str) -> Decimal:
    """Resolve hourly rate: project override > client rate > 0"""
    supabase = get_supabase_admin()
    if project_id:
        p = supabase.table("projects").select("hourly_rate_override,client_id").eq("id", project_id).single().execute()
        if p.data and p.data.get("hourly_rate_override"):
            return Decimal(str(p.data["hourly_rate_override"]))
        client_id = p.data.get("client_id") if p.data else client_id
    if client_id:
        c = supabase.table("clients").select("hourly_rate").eq("id", client_id).single().execute()
        if c.data and c.data.get("hourly_rate"):
            return Decimal(str(c.data["hourly_rate"]))
    return Decimal("0")


@router.get("/", response_class=HTMLResponse)
async def list_time(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("time_entries").select("*,clients(name),projects(name)").eq("organization_id", user.organization_id).order("date", desc=True).execute()
    entries = resp.data or []
    return templates.TemplateResponse("time/list.html", {
        "request": request, "user": user, "entries": entries
    })


@router.get("/new", response_class=HTMLResponse)
async def new_time_form(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("id,name,client_id").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    return templates.TemplateResponse("time/form.html", {
        "request": request, "user": user, "entry": None,
        "clients": clients_resp.data or [], "projects": projects_resp.data or []
    })


@router.post("/")
async def create_time(
    request: Request,
    date: str = Form(...),
    hours: str = Form(...),
    client_id: str = Form(""),
    project_id: str = Form(""),
    billable: str = Form("on"),
    details: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    rate = resolve_rate(client_id or None, project_id or None, user.organization_id)
    data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "date": date,
        "hours": float(hours),
        "rate": float(rate),
        "billable": billable == "on",
        "details": details,
        "client_id": client_id or None,
        "project_id": project_id or None,
    }
    supabase.table("time_entries").insert(data).execute()
    return RedirectResponse(url="/time", status_code=302)


@router.get("/{entry_id}/edit", response_class=HTMLResponse)
async def edit_time_form(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("time_entries").select("*").eq("id", entry_id).eq("organization_id", user.organization_id).single().execute()
    entry = resp.data
    if not entry:
        return RedirectResponse(url="/time", status_code=302)
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("id,name,client_id").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    return templates.TemplateResponse("time/form.html", {
        "request": request, "user": user, "entry": entry,
        "clients": clients_resp.data or [], "projects": projects_resp.data or []
    })


@router.post("/{entry_id}")
async def update_time(
    request: Request, entry_id: str,
    date: str = Form(...),
    hours: str = Form(...),
    client_id: str = Form(""),
    project_id: str = Form(""),
    billable: str = Form("on"),
    details: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "date": date,
        "hours": float(hours),
        "billable": billable == "on",
        "details": details,
        "client_id": client_id or None,
        "project_id": project_id or None,
    }
    supabase.table("time_entries").update(data).eq("id", entry_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/time", status_code=302)


@router.post("/{entry_id}/delete")
async def delete_time(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    supabase.table("time_entries").delete().eq("id", entry_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/time", status_code=302)
