from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.auth import require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    org_resp = supabase.table("organizations").select("*").eq("id", user.organization_id).single().execute()
    org = org_resp.data or {}

    settings_resp = supabase.table("organization_settings").select("*").eq("organization_id", user.organization_id).single().execute()
    settings = settings_resp.data or {"mileage_rate": 0.67}

    return templates.TemplateResponse("settings/index.html", {
        "request": request, "user": user, "org": org, "settings": settings
    })


@router.post("/")
async def update_settings(
    request: Request,
    mileage_rate: str = Form("0.67"),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    try:
        rate = float(mileage_rate)
    except ValueError:
        rate = 0.67

    existing = supabase.table("organization_settings").select("id").eq("organization_id", user.organization_id).execute()
    if existing.data:
        supabase.table("organization_settings").update({"mileage_rate": rate}).eq("organization_id", user.organization_id).execute()
    else:
        supabase.table("organization_settings").insert({
            "organization_id": user.organization_id,
            "mileage_rate": rate,
        }).execute()

    return RedirectResponse(url="/settings", status_code=302)
