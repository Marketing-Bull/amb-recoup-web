from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer
from app.database import get_supabase_admin
from app.models import UserContext
from app.config import get_settings
import jwt

security = HTTPBearer(auto_error=False)


def get_token_from_request(request: Request) -> str | None:
    # Check cookie first
    token = request.cookies.get("access_token")
    if token:
        return token
    # Then Authorization header
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:]
    return None


async def get_current_user(request: Request) -> UserContext:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    settings = get_settings()
    if not settings.supabase_jwt_secret:
        # Fail closed: without a secret we cannot verify the token's signature,
        # and accepting unverified claims allows full account impersonation.
        raise HTTPException(status_code=500, detail="Server auth misconfigured")
    try:
        # Verify signature + expiry against the Supabase project's JWT secret.
        # Supabase issues tokens with aud="authenticated".
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        email = payload.get("email", "")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Look up user profile + org membership
        supabase = get_supabase_admin()

        # Check if superuser (first user / admin_email)
        is_superuser = email.lower() == settings.admin_email.lower()

        # Get user's organization membership
        profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        org_id = profile.data.get("organization_id") if profile.data else None
        role = profile.data.get("role") if profile.data else None

        return UserContext(
            id=user_id,
            email=email,
            organization_id=org_id,
            role=role,
            is_admin=role == "admin" or is_superuser,
            is_superuser=is_superuser,
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication failed")


async def require_org_member(user: UserContext = Depends(get_current_user)):
    if not user.organization_id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Not associated with any organization")
    return user


async def require_admin(user: UserContext = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_superuser(user: UserContext = Depends(get_current_user)):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    return user
