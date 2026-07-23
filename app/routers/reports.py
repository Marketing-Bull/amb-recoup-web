from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import csv
import io
from datetime import datetime
from decimal import Decimal
from app.auth import require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def csv_response(filename: str, header: list, rows: list):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/", response_class=HTMLResponse)
async def reports_page(request: Request, user: UserContext = Depends(require_org_member)):
    return templates.TemplateResponse("reports/index.html", {
        "request": request, "user": user
    })


@router.get("/clients.csv")
async def export_clients(user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("clients").select("*").eq("organization_id", user.organization_id).order("name").execute()
    clients = resp.data or []
    header = ["Name", "Hourly Rate", "Contact Name", "Contact Email", "Contact Phone", "Notes", "Archived", "Created At"]
    rows = [
        [
            c["name"], c.get("hourly_rate", ""), c.get("contact_name", ""),
            c.get("contact_email", ""), c.get("contact_phone", ""), c.get("notes", ""),
            "Yes" if c.get("is_archived") else "No", c["created_at"]
        ]
        for c in clients
    ]
    suffix = datetime.now().strftime("%Y%m%d")
    return csv_response(f"recoup-clients-{suffix}.csv", header, rows)


@router.get("/projects.csv")
async def export_projects(user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("projects").select("*, clients(name)").eq("organization_id", user.organization_id).order("name").execute()
    projects = resp.data or []
    header = ["Name", "Client", "Hourly Rate Override", "Status", "Notes", "Archived", "Created At"]
    rows = [
        [
            p["name"], p.get("clients", {}).get("name", "") if p.get("clients") else "",
            p.get("hourly_rate_override", ""), p["status"], p.get("notes", ""),
            "Yes" if p.get("is_archived") else "No", p["created_at"]
        ]
        for p in projects
    ]
    suffix = datetime.now().strftime("%Y%m%d")
    return csv_response(f"recoup-projects-{suffix}.csv", header, rows)


@router.get("/time.csv")
async def export_time(user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("time_entries").select("*, clients(name), projects(name)").eq("organization_id", user.organization_id).order("date", desc=True).execute()
    entries = resp.data or []
    header = ["Date", "Hours", "Rate", "Total", "Billable", "Details", "Client", "Project", "Created At"]
    rows = [
        [
            e["date"][:10], e["hours"], e["rate"], float(e["hours"]) * float(e["rate"]),
            "Yes" if e["billable"] else "No", e.get("details", ""),
            e.get("clients", {}).get("name", "") if e.get("clients") else "",
            e.get("projects", {}).get("name", "") if e.get("projects") else "",
            e["created_at"]
        ]
        for e in entries
    ]
    suffix = datetime.now().strftime("%Y%m%d")
    return csv_response(f"recoup-time-{suffix}.csv", header, rows)


@router.get("/expenses.csv")
async def export_expenses(user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("expenses").select("*, clients(name), projects(name)").eq("organization_id", user.organization_id).order("date", desc=True).execute()
    entries = resp.data or []
    header = ["Date", "Amount", "Category", "Vendor", "Details", "Billable", "Recurring", "Client", "Project", "Created At"]
    rows = [
        [
            e["date"][:10], e["amount"], e["category"], e.get("vendor", ""), e.get("details", ""),
            "Yes" if e["billable"] else "No", e["recurring"],
            e.get("clients", {}).get("name", "") if e.get("clients") else "",
            e.get("projects", {}).get("name", "") if e.get("projects") else "",
            e["created_at"]
        ]
        for e in entries
    ]
    suffix = datetime.now().strftime("%Y%m%d")
    return csv_response(f"recoup-expenses-{suffix}.csv", header, rows)


@router.get("/mileage.csv")
async def export_mileage(user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    settings_resp = supabase.table("organization_settings").select("mileage_rate").eq("organization_id", user.organization_id).single().execute()
    mileage_rate = Decimal(str(settings_resp.data["mileage_rate"])) if settings_resp.data else Decimal("0.67")

    resp = supabase.table("mileage_entries").select("*, clients(name), projects(name)").eq("organization_id", user.organization_id).order("date", desc=True).execute()
    entries = resp.data or []
    header = ["Date", "Start Address", "End Address", "Purpose", "Miles", "Round Trip", "Total Miles", "Value", "Billable", "Client", "Project", "Created At"]
    rows = [
        [
            e["date"][:10], e.get("start_address", ""), e.get("end_address", ""), e.get("purpose", ""),
            e["miles"], "Yes" if e["round_trip"] else "No", e["total_miles"],
            float(e["total_miles"]) * float(mileage_rate),
            "Yes" if e["billable"] else "No",
            e.get("clients", {}).get("name", "") if e.get("clients") else "",
            e.get("projects", {}).get("name", "") if e.get("projects") else "",
            e["created_at"]
        ]
        for e in entries
    ]
    suffix = datetime.now().strftime("%Y%m%d")
    return csv_response(f"recoup-mileage-{suffix}.csv", header, rows)
