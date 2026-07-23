from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import time

from app.routers import auth, dashboard, clients, projects, time_entries, mileage, expenses, reports, admin, settings

app = FastAPI(title="AMB Recoup", version="0.1.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
app.include_router(clients.router, prefix="/clients", tags=["clients"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(time_entries.router, prefix="/time", tags=["time"])
app.include_router(mileage.router, prefix="/mileage", tags=["mileage"])
app.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
app.include_router(reports.router, prefix="/reports", tags=["reports"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])


@app.get("/")
async def root(request: Request):
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    # nosec B104: intentional container bind-all (Docker/Railway/Render/Fly.io)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)  # noqa: S104
