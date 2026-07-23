from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from datetime import datetime
from decimal import Decimal
from app.auth import get_current_user, require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def list_clients(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("clients").select("*").eq("organization_id", user.organization_id).order("name").execute()
    clients = resp.data or []
    return templates.TemplateResponse("clients/list.html", {
        "request": request, "user": user, "clients": clients
    })


@router.get("/new", response_class=HTMLResponse)
async def new_client_form(request: Request, user: UserContext = Depends(require_org_member)):
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "user": user, "client": None, "error": ""
    })


@router.post("/")
async def create_client(
    request: Request,
    name: str = Form(...),
    hourly_rate: str = Form(""),
    contact_name: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    notes: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "name": name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "notes": notes,
    }
    if hourly_rate:
        try:
            data["hourly_rate"] = float(Decimal(hourly_rate))
        except:
            pass
    supabase.table("clients").insert(data).execute()
    return RedirectResponse(url="/clients", status_code=302)


@router.get("/{client_id}/edit", response_class=HTMLResponse)
async def edit_client_form(request: Request, client_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("clients").select("*").eq("id", client_id).eq("organization_id", user.organization_id).single().execute()
    client = resp.data
    if not client:
        return RedirectResponse(url="/clients", status_code=302)
    return templates.TemplateResponse("clients/form.html", {
        "request": request, "user": user, "client": client, "error": ""
    })


@router.post("/{client_id}")
async def update_client(
    request: Request, client_id: str,
    name: str = Form(...),
    hourly_rate: str = Form(""),
    contact_name: str = Form(""),
    contact_email: str = Form(""),
    contact_phone: str = Form(""),
    notes: str = Form(""),
    is_archived: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "name": name,
        "contact_name": contact_name,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "notes": notes,
        "is_archived": is_archived == "on",
    }
    if hourly_rate:
        try:
            data["hourly_rate"] = float(Decimal(hourly_rate))
        except:
            pass
    supabase.table("clients").update(data).eq("id", client_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/clients", status_code=302)
