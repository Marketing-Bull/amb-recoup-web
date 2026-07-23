from fastapi import APIRouter, Request, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from app.auth import get_current_user, require_org_member
from app.models import UserContext, ExpenseCategory
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def list_expenses(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("expenses").select("*,clients(name),projects(name)").eq("organization_id", user.organization_id).order("date", desc=True).execute()
    entries = resp.data or []
    return templates.TemplateResponse("expenses/list.html", {
        "request": request, "user": user, "entries": entries, "categories": [c.value for c in ExpenseCategory]
    })


@router.get("/new", response_class=HTMLResponse)
async def new_expense_form(request: Request, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("id,name,client_id").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    return templates.TemplateResponse("expenses/form.html", {
        "request": request, "user": user, "entry": None,
        "clients": clients_resp.data or [], "projects": projects_resp.data or [],
        "categories": [c.value for c in ExpenseCategory]
    })


@router.post("/")
async def create_expense(
    request: Request,
    date: str = Form(...),
    amount: str = Form(...),
    category: str = Form("other"),
    vendor: str = Form(""),
    details: str = Form(""),
    billable: str = Form(""),
    recurring: str = Form("none"),
    client_id: str = Form(""),
    project_id: str = Form(""),
    receipt: UploadFile = File(None),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "date": date,
        "amount": float(amount),
        "category": category,
        "vendor": vendor,
        "details": details,
        "billable": billable == "on",
        "recurring": recurring,
        "client_id": client_id or None,
        "project_id": project_id or None,
    }
    if receipt and receipt.filename:
        file_path = f"{user.organization_id}/{data['id']}/{receipt.filename}"
        content = await receipt.read()
        supabase.storage.from_("receipts").upload(file_path, content)
        data["receipt_url"] = supabase.storage.from_("receipts").get_public_url(file_path)
    supabase.table("expenses").insert(data).execute()
    return RedirectResponse(url="/expenses", status_code=302)


@router.get("/{entry_id}/edit", response_class=HTMLResponse)
async def edit_expense_form(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("expenses").select("*").eq("id", entry_id).eq("organization_id", user.organization_id).single().execute()
    entry = resp.data
    if not entry:
        return RedirectResponse(url="/expenses", status_code=302)
    clients_resp = supabase.table("clients").select("id,name").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    projects_resp = supabase.table("projects").select("id,name,client_id").eq("organization_id", user.organization_id).eq("is_archived", False).execute()
    return templates.TemplateResponse("expenses/form.html", {
        "request": request, "user": user, "entry": entry,
        "clients": clients_resp.data or [], "projects": projects_resp.data or [],
        "categories": [c.value for c in ExpenseCategory]
    })


@router.post("/{entry_id}")
async def update_expense(
    request: Request, entry_id: str,
    date: str = Form(...),
    amount: str = Form(...),
    category: str = Form("other"),
    vendor: str = Form(""),
    details: str = Form(""),
    billable: str = Form(""),
    recurring: str = Form("none"),
    client_id: str = Form(""),
    project_id: str = Form(""),
    receipt: UploadFile = File(None),
    user: UserContext = Depends(require_org_member),
):
    supabase = get_supabase_admin()
    data = {
        "date": date,
        "amount": float(amount),
        "category": category,
        "vendor": vendor,
        "details": details,
        "billable": billable == "on",
        "recurring": recurring,
        "client_id": client_id or None,
        "project_id": project_id or None,
    }
    if receipt and receipt.filename:
        file_path = f"{user.organization_id}/{entry_id}/{receipt.filename}"
        content = await receipt.read()
        supabase.storage.from_("receipts").upload(file_path, content, {"upsert": True})
        data["receipt_url"] = supabase.storage.from_("receipts").get_public_url(file_path)
    supabase.table("expenses").update(data).eq("id", entry_id).eq("organization_id", user.organization_id).execute()
    return RedirectResponse(url="/expenses", status_code=302)


@router.post("/{entry_id}/duplicate")
async def duplicate_expense(request: Request, entry_id: str, user: UserContext = Depends(require_org_member)):
    supabase = get_supabase_admin()
    resp = supabase.table("expenses").select("*").eq("id", entry_id).eq("organization_id", user.organization_id).single().execute()
    entry = resp.data
    if not entry:
        return RedirectResponse(url="/expenses", status_code=302)
    new_data = {
        "id": str(uuid4()),
        "organization_id": user.organization_id,
        "date": "now()",
        "amount": entry["amount"],
        "category": entry["category"],
        "vendor": entry["vendor"],
        "details": entry["details"],
        "billable": entry["billable"],
        "recurring": entry["recurring"],
        "client_id": entry.get("client_id"),
        "project_id": entry.get("project_id"),
    }
    supabase.table("expenses").insert(new_data).execute()
    return RedirectResponse(url="/expenses", status_code=302)
