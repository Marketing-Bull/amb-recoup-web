from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from uuid import uuid4
from datetime import datetime
from app.auth import get_current_user, require_superuser
from app.models import UserContext
from app.database import get_supabase_admin

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user: UserContext = Depends(require_superuser)):
    supabase = get_supabase_admin()
    orgs_resp = supabase.table("organizations").select("*, profiles!owner_id(email)").order("created_at", desc=True).execute()
    orgs = orgs_resp.data or []
    members_resp = supabase.table("organization_members").select("*").execute()
    members = members_resp.data or []
    users_resp = supabase.table("profiles").select("*").execute()
    users = users_resp.data or []
    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request, "user": user,
        "org_count": len(orgs),
        "member_count": len(members),
        "user_count": len(users),
        "orgs": orgs,
    })


@router.get("/organizations", response_class=HTMLResponse)
async def list_organizations(request: Request, user: UserContext = Depends(require_superuser)):
    supabase = get_supabase_admin()
    resp = supabase.table("organizations").select("*, profiles!owner_id(email)").order("created_at", desc=True).execute()
    orgs = resp.data or []
    return templates.TemplateResponse("admin/organizations.html", {
        "request": request, "user": user, "orgs": orgs
    })


@router.post("/organizations")
async def create_organization(
    request: Request,
    name: str = Form(...),
    owner_email: str = Form(...),
    user: UserContext = Depends(require_superuser),
):
    supabase = get_supabase_admin()
    # Find or create user by email
    auth_resp = supabase.auth.admin.list_users()
    existing_user = next((u for u in auth_resp.users if u.email == owner_email), None)
    if existing_user:
        owner_id = existing_user.id
    else:
        # Create user via admin API
        new_user = supabase.auth.admin.create_user({"email": owner_email, "email_confirm": True})
        owner_id = new_user.user.id

    org_slug = name.lower().replace(" ", "-").replace("_", "-")[:50]
    org = supabase.table("organizations").insert({
        "name": name,
        "slug": org_slug,
        "owner_id": owner_id,
    }).execute()
    org_id = org.data[0]["id"] if org.data else None

    # Ensure profile exists
    profile = supabase.table("profiles").select("*").eq("id", owner_id).single().execute()
    if not profile.data:
        supabase.table("profiles").insert({
            "id": owner_id,
            "email": owner_email,
            "organization_id": org_id,
            "role": "admin",
        }).execute()
    else:
        supabase.table("profiles").update({"organization_id": org_id, "role": "admin"}).eq("id", owner_id).execute()

    # Create membership
    supabase.table("organization_members").insert({
        "organization_id": org_id,
        "user_id": owner_id,
        "role": "admin",
        "email": owner_email,
        "joined_at": "now()",
    }).execute()

    # Create default settings
    supabase.table("organization_settings").insert({
        "organization_id": org_id,
        "mileage_rate": 0.67,
    }).execute()

    return RedirectResponse(url="/admin/organizations", status_code=302)


@router.get("/organizations/{org_id}", response_class=HTMLResponse)
async def org_detail(request: Request, org_id: str, user: UserContext = Depends(require_superuser)):
    supabase = get_supabase_admin()
    org_resp = supabase.table("organizations").select("*, profiles!owner_id(email)").eq("id", org_id).single().execute()
    org = org_resp.data
    if not org:
        return RedirectResponse(url="/admin/organizations", status_code=302)

    members_resp = supabase.table("organization_members").select("*, profiles!user_id(email)").eq("organization_id", org_id).execute()
    members = members_resp.data or []

    clients_resp = supabase.table("clients").select("count").eq("organization_id", org_id).execute()
    projects_resp = supabase.table("projects").select("count").eq("organization_id", org_id).execute()
    time_resp = supabase.table("time_entries").select("count").eq("organization_id", org_id).execute()
    expense_resp = supabase.table("expenses").select("count").eq("organization_id", org_id).execute()
    mileage_resp = supabase.table("mileage_entries").select("count").eq("organization_id", org_id).execute()

    return templates.TemplateResponse("admin/org_detail.html", {
        "request": request, "user": user, "org": org, "members": members,
        "client_count": clients_resp.data[0]["count"] if clients_resp.data else 0,
        "project_count": projects_resp.data[0]["count"] if projects_resp.data else 0,
        "time_count": time_resp.data[0]["count"] if time_resp.data else 0,
        "expense_count": expense_resp.data[0]["count"] if expense_resp.data else 0,
        "mileage_count": mileage_resp.data[0]["count"] if mileage_resp.data else 0,
    })


@router.post("/organizations/{org_id}/invite")
async def invite_member(
    request: Request, org_id: str,
    email: str = Form(...),
    role: str = Form("member"),
    user: UserContext = Depends(require_superuser),
):
    supabase = get_supabase_admin()
    # Find or create user
    auth_resp = supabase.auth.admin.list_users()
    existing_user = next((u for u in auth_resp.users if u.email == email), None)
    if existing_user:
        user_id = existing_user.id
    else:
        new_user = supabase.auth.admin.create_user({"email": email, "email_confirm": True})
        user_id = new_user.user.id

    # Check if already member
    existing = supabase.table("organization_members").select("*").eq("organization_id", org_id).eq("user_id", user_id).execute()
    if existing.data:
        return RedirectResponse(url=f"/admin/organizations/{org_id}?error=Already a member", status_code=302)

    supabase.table("organization_members").insert({
        "organization_id": org_id,
        "user_id": user_id,
        "role": role,
        "email": email,
        "invited_at": "now()",
    }).execute()

    # Update profile
    profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
    if not profile.data:
        supabase.table("profiles").insert({
            "id": user_id,
            "email": email,
            "organization_id": org_id,
            "role": role,
        }).execute()
    else:
        supabase.table("profiles").update({"organization_id": org_id, "role": role}).eq("id", user_id).execute()

    return RedirectResponse(url=f"/admin/organizations/{org_id}?message=Invited", status_code=302)


@router.post("/organizations/{org_id}/members/{member_id}/role")
async def update_member_role(
    request: Request, org_id: str, member_id: str,
    role: str = Form(...),
    user: UserContext = Depends(require_superuser),
):
    supabase = get_supabase_admin()
    member = supabase.table("organization_members").select("user_id").eq("id", member_id).single().execute()
    supabase.table("organization_members").update({"role": role}).eq("id", member_id).execute()
    if member.data:
        supabase.table("profiles").update({"role": role}).eq("id", member.data["user_id"]).execute()
    return RedirectResponse(url=f"/admin/organizations/{org_id}", status_code=302)


@router.post("/organizations/{org_id}/members/{member_id}/remove")
async def remove_member(request: Request, org_id: str, member_id: str, user: UserContext = Depends(require_superuser)):
    supabase = get_supabase_admin()
    member = supabase.table("organization_members").select("user_id").eq("id", member_id).single().execute()
    supabase.table("organization_members").delete().eq("id", member_id).execute()
    if member.data:
        supabase.table("profiles").update({"organization_id": None}).eq("id", member.data["user_id"]).execute()
    return RedirectResponse(url=f"/admin/organizations/{org_id}", status_code=302)
