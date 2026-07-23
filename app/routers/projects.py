from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from app.auth import get_current_user, require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def list_projects(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("projects").select("*, clients(name)").eq("organization_id", user.organization_id).order("name").execute()
    projects = resp.data or []
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    clients = clients_resp.data or []
    return templates.TemplateResponse("projects/list.html", {
        "request": request, "user": user, "projects": projects, "clients": clients
    })


@router.get("/new", response_class=HTMLResponse)
async def new_project_form(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    clients = clients_resp.data or []
    return templates.TemplateResponse("projects/form.html", {
        "request": request, "user": user, "project": None, "clients": clients, "error": ""
    })


@router.post("/")
async def create_project(
    request: Request,
    name: str = Form(...),
    client_id: str = Form(""),
    hourly_rate_override: str = Form(""),
    status: str = Form("active"),
    notes: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "name": name,
        "client_id": client_id or None,
        "status": status,
        "notes": notes,
    }
    if hourly_rate_override:
        try:
            data["hourly_rate_override"] = float(hourly_rate_override)
        except:
            pass
    supabase.table("projects").insert(data).execute()
    return RedirectResponse(url="/projects", status_code=302)


@router.get("/{project_id}/edit", response_class=HTMLResponse)
async def edit_project_form(request: Request, project_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("projects").select("*").eq("id", project_id).eq("organization_id", user.organization_id).single().execute()
    project = resp.data
    if not project:
        return RedirectResponse(url="/projects", status_code=302)
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    clients = clients_resp.data or []
    return templates.TemplateResponse("projects/form.html", {
        "request": request, "user": user, "project": project, "clients": clients, "error": ""
    })


@router.post("/{project_id}")
async def update_project(
    request: Request, project_id: str,
    name: str = Form(...),
    client_id: str = Form(""),
    hourly_rate_override: str = Form(""),
    status: str = Form("active"),
    notes: str = Form(""),
    is_archived: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "name": name,
        "client_id": client_id or None,
        "status": status,
        "notes": notes,
        "is_archived": is_archived == "on",
    }
    if hourly_rate_override:
        try:
            data["hourly_rate_override"] = float(hourly_rate_override)
        except:
            pass
    supabase.table("projects").update(data).eq("id", project_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/projects", status_code=302)
