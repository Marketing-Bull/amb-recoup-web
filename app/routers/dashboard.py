from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from decimal import Decimal
from app.auth import get_current_user, require_org_member
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def get_date_range(preset: str):
    today = datetime.now().date()
    if preset == "today":
        return today, today + timedelta(days=1)
    elif preset == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, start + timedelta(days=7)
    elif preset == "this_month":
        start = today.replace(day=1)
        next_month = start + timedelta(days=32)
        return start, next_month.replace(day=1)
    elif preset == "last_month":
        next_month = today.replace(day=1)
        start = (next_month - timedelta(days=1)).replace(day=1)
        return start, next_month
    elif preset == "this_year":
        start = today.replace(month=1, day=1)
        return start, today.replace(month=12, day=31) + timedelta(days=1)
    elif preset == "all":
        return datetime.min.date(), datetime.max.date()
    return today.replace(day=1), today + timedelta(days=1)


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    preset: str = "this_month",
    group_by: str = "client",
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    org_id = user.organization_id

    start, end = get_date_range(preset)
    start_str = start.isoformat()
    end_str = end.isoformat()

    # Fetch settings for mileage rate
    settings_resp = supabase.table("organization_settings").select("mileage_rate").eq("organization_id", org_id).single().execute()
    mileage_rate = Decimal(str(settings_resp.data["mileage_rate"])) if settings_resp.data else Decimal("0.67")

    # Fetch all data for the org
    clients_resp = supabase.table("clients").select("*").eq("organization_id", org_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("*").eq("organization_id", org_id).eq("is_archived", False).execute()
    time_resp = supabase.table("time_entries").select("*").eq("organization_id", org_id).gte("date", start_str).lt("date", end_str).execute()
    mileage_resp = supabase.table("mileage_entries").select("*").eq("organization_id", org_id).gte("date", start_str).lt("date", end_str).execute()
    expenses_resp = supabase.table("expenses").select("*").eq("organization_id", org_id).gte("date", start_str).lt("date", end_str).execute()

    clients = {c["id"]: c for c in (clients_resp.data or [])}
    projects = {p["id"]: p for p in (projects_resp.data or [])}
    time_entries = time_resp.data or []
    mileage_entries = mileage_resp.data or []
    expenses = expenses_resp.data or []

    # Calculate totals
    billable_time_value = sum(
        Decimal(str(t["hours"])) * Decimal(str(t["rate"]))
        for t in time_entries if t["billable"]
    )
    total_hours = sum(t["hours"] for t in time_entries)
    unbilled_hours = sum(t["hours"] for t in time_entries if not t["billable"])
    total_miles = sum(m["total_miles"] for m in mileage_entries)
    mileage_value = Decimal(str(total_miles)) * mileage_rate
    expense_total = sum(Decimal(str(e["amount"])) for e in expenses)
    billable_expenses = sum(Decimal(str(e["amount"])) for e in expenses if e["billable"])

    # Build breakdown
    breakdown = []
    if group_by == "client":
        for cid, client in clients.items():
            c_time = sum(Decimal(str(t["hours"])) * Decimal(str(t["rate"])) for t in time_entries if t.get("client_id") == cid and t["billable"])
            c_miles = sum(m["total_miles"] for m in mileage_entries if m.get("client_id") == cid)
            c_exp = sum(Decimal(str(e["amount"])) for e in expenses if e.get("client_id") == cid)
            if c_time > 0 or c_miles > 0 or c_exp > 0:
                breakdown.append({
                    "name": client["name"],
                    "time_value": c_time,
                    "mileage_value": Decimal(str(c_miles)) * mileage_rate,
                    "expense_value": c_exp,
                    "combined": c_time + Decimal(str(c_miles)) * mileage_rate + c_exp,
                })
        # Unassigned
        u_time = sum(Decimal(str(t["hours"])) * Decimal(str(t["rate"])) for t in time_entries if t["billable"] and not t.get("client_id"))
        u_miles = sum(m["total_miles"] for m in mileage_entries if not m.get("client_id"))
        u_exp = sum(Decimal(str(e["amount"])) for e in expenses if not e.get("client_id"))
        if u_time > 0 or u_miles > 0 or u_exp > 0:
            breakdown.append({
                "name": "Unassigned",
                "time_value": u_time,
                "mileage_value": Decimal(str(u_miles)) * mileage_rate,
                "expense_value": u_exp,
                "combined": u_time + Decimal(str(u_miles)) * mileage_rate + u_exp,
            })
    else:
        for pid, project in projects.items():
            p_time = sum(Decimal(str(t["hours"])) * Decimal(str(t["rate"])) for t in time_entries if t.get("project_id") == pid and t["billable"])
            p_miles = sum(m["total_miles"] for m in mileage_entries if m.get("project_id") == pid)
            p_exp = sum(Decimal(str(e["amount"])) for e in expenses if e.get("project_id") == pid)
            if p_time > 0 or p_miles > 0 or p_exp > 0:
                breakdown.append({
                    "name": project["name"],
                    "time_value": p_time,
                    "mileage_value": Decimal(str(p_miles)) * mileage_rate,
                    "expense_value": p_exp,
                    "combined": p_time + Decimal(str(p_miles)) * mileage_rate + p_exp,
                })
        u_time = sum(Decimal(str(t["hours"])) * Decimal(str(t["rate"])) for t in time_entries if t["billable"] and not t.get("project_id"))
        u_miles = sum(m["total_miles"] for m in mileage_entries if not m.get("project_id"))
        u_exp = sum(Decimal(str(e["amount"])) for e in expenses if not e.get("project_id"))
        if u_time > 0 or u_miles > 0 or u_exp > 0:
            breakdown.append({
                "name": "Unassigned",
                "time_value": u_time,
                "mileage_value": Decimal(str(u_miles)) * mileage_rate,
                "expense_value": u_exp,
                "combined": u_time + Decimal(str(u_miles)) * mileage_rate + u_exp,
            })

    breakdown.sort(key=lambda x: (x["name"] == "Unassigned", -x["combined"]))

    has_data = bool(time_entries or mileage_entries or expenses or clients)

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "user": user,
        "preset": preset,
        "group_by": group_by,
        "billable_time_value": billable_time_value,
        "total_hours": total_hours,
        "unbilled_hours": unbilled_hours,
        "mileage_value": mileage_value,
        "mileage_rate": mileage_rate,
        "total_miles": total_miles,
        "expense_total": expense_total,
        "billable_expenses": billable_expenses,
        "breakdown": breakdown,
        "has_data": has_data,
    })
