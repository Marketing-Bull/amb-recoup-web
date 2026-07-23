from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.database import get_supabase, get_supabase_admin
from app.config import get_settings
import httpx

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = "", message: str = ""):
    return templates.TemplateResponse(
        "auth/login.html",
        {"request": request, "error": error, "message": message}
    )


@router.post("/login")
async def login_password(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        supabase = get_supabase()
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.session:
            resp = RedirectResponse(url="/dashboard", status_code=302)
            resp.set_cookie("access_token", response.session.access_token, httponly=True, secure=True, samesite="lax")
            return resp
    except Exception as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": str(e), "message": ""}
        )
    return RedirectResponse(url="/auth/login?error=Invalid credentials", status_code=302)


@router.post("/magic-link")
async def login_magic_link(request: Request, email: str = Form(...)):
    settings = get_settings()
    try:
        supabase = get_supabase()
        supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {"email_redirect_to": f"{settings.supabase_url}/auth/callback"}
        })
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "", "message": "Magic link sent! Check your email."}
        )
    except Exception as e:
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": str(e), "message": ""}
        )


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, error: str = ""):
    return templates.TemplateResponse(
        "auth/signup.html",
        {"request": request, "error": error}
    )


@router.post("/signup")
async def signup(request: Request, email: str = Form(...), password: str = Form(...), org_name: str = Form(...)):
    try:
        supabase = get_supabase()
        # Sign up the user
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {"data": {"full_name": email}}
        })
        user_id = auth_response.user.id if auth_response.user else None
        if not user_id:
            return RedirectResponse(url="/auth/signup?error=Signup failed", status_code=302)

        # Create organization
        admin = get_supabase_admin()
        org_slug = org_name.lower().replace(" ", "-").replace("_", "-")[:50]
        org = admin.table("organizations").insert({
            "name": org_name,
            "slug": org_slug,
            "owner_id": user_id,
        }).execute()

        org_id = org.data[0]["id"] if org.data else None

        # Create profile
        admin.table("profiles").insert({
            "id": user_id,
            "email": email,
            "organization_id": org_id,
            "role": "admin",
        }).execute()

        # Create org membership
        admin.table("organization_members").insert({
            "organization_id": org_id,
            "user_id": user_id,
            "role": "admin",
            "email": email,
            "joined_at": "now()",
        }).execute()

        # Create default settings
        admin.table("organization_settings").insert({
            "organization_id": org_id,
            "mileage_rate": 0.67,
        }).execute()

        # Set session
        resp = RedirectResponse(url="/dashboard", status_code=302)
        resp.set_cookie("access_token", auth_response.session.access_token, httponly=True, secure=True, samesite="lax")
        return resp

    except Exception as e:
        return RedirectResponse(url=f"/auth/signup?error={str(e)[:200]}", status_code=302)


@router.get("/callback")
async def auth_callback(request: Request, access_token: str = "", refresh_token: str = ""):
    if access_token:
        resp = RedirectResponse(url="/dashboard", status_code=302)
        resp.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax")
        return resp
    return RedirectResponse(url="/auth/login?error=Authentication failed", status_code=302)


@router.post("/logout")
async def logout():
    resp = RedirectResponse(url="/auth/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp


@router.get("/logout")
async def logout_get():
    resp = RedirectResponse(url="/auth/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp
