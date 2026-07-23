from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from app.auth import require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_mileage_rate(org_id: str) -> float:
    """Org's configured $/mile rate, falling back to the IRS-standard default
    used elsewhere in the app (dashboard.py, reports.py, settings.py)."""
    supabase = get_supabase_admin()
    resp = supabase.table("organization_settings").select("mileage_rate").eq("organization_id", org_id).single().execute()
    return float(resp.data["mileage_rate"]) if resp.data and resp.data.get("mileage_rate") is not None else 0.67


@router.get("/", response_class=HTMLResponse)
async def list_mileage(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("mileage_entries").select("*,clients(name),projects(name)").eq("organization_id", user.organization_id).order("date", desc=True).execute()
    entries = resp.data or []
    return templates.TemplateResponse("mileage/list.html", {
        "request": request, "user": user, "entries": entries
    })


def recent_trips(entries: list[dict], limit: int = 8) -> list[dict]:
    """Distinct recent trips (keyed by addresses + round-trip + miles), most
    recent first. Mirrors the native app's `Recents.recentTrips` (Services/Recents.swift)
    so the web form can offer the same one-tap "repeat a trip" quick-fill."""
    seen = set()
    result = []
    for e in sorted(entries, key=lambda e: e.get("created_at") or "", reverse=True):
        key = (e.get("start_address", ""), e.get("end_address", ""), bool(e.get("round_trip")), e.get("miles"))
        if key in seen:
            continue
        seen.add(key)
        result.append(e)
        if len(result) >= limit:
            break
    return result


@router.get("/new", response_class=HTMLResponse)
async def new_mileage_form(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("id,name,client_id").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    trips_resp = supabase.table("mileage_entries").select("*").eq("organization_id", user.organization_id).order("created_at", desc=True).limit(50).execute()
    return templates.TemplateResponse("mileage/form.html", {
        "request": request, "user": user, "entry": None,
        "clients": clients_resp.data or [], "projects": projects_resp.data or [],
        "recent_trips": recent_trips(trips_resp.data or []),
        "mileage_rate": get_mileage_rate(user.organization_id)
    })


@router.post("/")
async def create_mileage(
    request: Request,
    date: str = Form(...),
    start_address: str = Form(""),
    end_address: str = Form(""),
    purpose: str = Form(""),
    miles: str = Form(...),
    round_trip: str = Form(""),
    billable: str = Form(""),
    client_id: str = Form(""),
    project_id: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    m = float(miles)
    total = m * 2 if round_trip == "on" else m
    data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "date": date,
        "start_address": start_address,
        "end_address": end_address,
        "purpose": purpose,
        "miles": m,
        "round_trip": round_trip == "on",
        "total_miles": total,
        "billable": billable == "on",
        "client_id": client_id or None,
        "project_id": project_id or None,
    }
    supabase.table("mileage_entries").insert(data).execute()
    return RedirectResponse(url="/mileage", status_code=302)


@router.get("/{entry_id}/edit", response_class=HTMLResponse)
async def edit_mileage_form(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("mileage_entries").select("*").eq("id", entry_id).eq("organization_id", user.organization_id).single().execute()
    entry = resp.data
    if not entry:
        return RedirectResponse(url="/mileage", status_code=302)
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("id,name,client_id").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    return templates.TemplateResponse("mileage/form.html", {
        "request": request, "user": user, "entry": entry,
        "clients": clients_resp.data or [], "projects": projects_resp.data or [],
        "mileage_rate": get_mileage_rate(user.organization_id)
    })


@router.post("/{entry_id}")
async def update_mileage(
    request: Request, entry_id: str,
    date: str = Form(...),
    start_address: str = Form(""),
    end_address: str = Form(""),
    purpose: str = Form(""),
    miles: str = Form(...),
    round_trip: str = Form(""),
    billable: str = Form(""),
    client_id: str = Form(""),
    project_id: str = Form(""),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    m = float(miles)
    total = m * 2 if round_trip == "on" else m
    data = {
        "date": date,
        "start_address": start_address,
        "end_address": end_address,
        "purpose": purpose,
        "miles": m,
        "round_trip": round_trip == "on",
        "total_miles": total,
        "billable": billable == "on",
        "client_id": client_id or None,
        "project_id": project_id or None,
    }
    supabase.table("mileage_entries").update(data).eq("id", entry_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/mileage", status_code=302)


@router.post("/{entry_id}/duplicate")
async def duplicate_mileage(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("mileage_entries").select("*").eq("id", entry_id).eq("organization_id", user.organization_id).single().execute()
    entry = resp.data
    if not entry:
        return RedirectResponse(url="/mileage", status_code=302)
    new_data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "date": "now()",
        "start_address": entry["start_address"],
        "end_address": entry["end_address"],
        "purpose": entry["purpose"],
        "miles": entry["miles"],
        "round_trip": entry["round_trip"],
        "total_miles": entry["total_miles"],
        "billable": entry["billable"],
        "client_id": entry.get("client_id"),
        "project_id": entry.get("project_id"),
    }
    supabase.table("mileage_entries").insert(new_data).execute()
    return RedirectResponse(url="/mileage", status_code=302)


@router.post("/{entry_id}/delete")
async def delete_mileage(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    supabase.table("mileage_entries").delete().eq("id", entry_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/mileage", status_code=302)
