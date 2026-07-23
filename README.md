# AMB Recoup Web

A SaaS web application for freelancers and small agencies to track time, mileage, expenses, and projects. Built with **FastAPI**, **Jinja2 templates**, **HTMX**, and **Supabase**.

## Features

- **Dashboard** — Overview of billable time, hours, mileage value, total miles, expenses, and breakdown by client or project.
- **Time Tracking** — Log hours by date, client, and project with automatic rate resolution (project override > client rate).
- **Mileage** — Track trips with start/end addresses, purpose, round-trip support, and billable flag.
- **Expenses** — Record costs by category (software, meals, travel, advertising, office, contractors, other) with receipt uploads, vendor, recurring schedules, and billable flag.
- **Clients** — Manage client contact info, hourly rates, and archive status.
- **Projects** — Link projects to clients with rate overrides and status (active / on hold / completed).
- **CSV Export** — Download clients, projects, time entries, expenses, and mileage as CSV.
- **Multi-tenancy** — Organizations with members, roles (admin, member, viewer), and owner management.
- **Admin Panel** — Superuser admin to manage organizations, members, invites, and view org stats.
- **Organization Settings** — Configurable mileage rate per org.

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Templates | Jinja2 + HTMX (minimal JS) |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (JWT via cookie) |
| Storage | Supabase Storage (receipts bucket) |
| CSS | Vanilla CSS with CSS variables |

## Setup

### 1. Clone & install dependencies

```bash
git clone <repo-url>
cd amb-recoup-web
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env`

```
RECOUP_SUPABASE_URL=https://your-project.supabase.co
RECOUP_SUPABASE_KEY=eyJ...
RECOUP_SUPABASE_SERVICE_KEY=eyJ...
RECOUP_SUPABASE_JWT_SECRET=your-jwt-secret
RECOUP_APP_SECRET=change-me-in-production
```

> Get `RECOUP_SUPABASE_KEY` (anon/public) and `RECOUP_SUPABASE_SERVICE_KEY` (service role) from your Supabase project settings > API. `RECOUP_SUPABASE_JWT_SECRET` is the JWT Secret in the same section — **required**: session cookies are signature-verified against it, so the app refuses to authenticate requests if it's unset. All variables must use the `RECOUP_` prefix (see `.env.example` for the full list — names map directly to `app/config.py` settings fields).

### 3. Run Supabase migrations

Apply the schema in Supabase SQL Editor or via Supabase CLI:

```bash
supabase db push
# or run SQL manually from supabase/migrations/001_initial_schema.sql
```

> Ensure you create the `receipts` storage bucket in Supabase Studio and set it to public.

### 4. Start the app

```bash
uvicorn app.main:app --reload --port 8000
```

Visit [http://localhost:8000](http://localhost:8000)

## Deployment

### Railway

1. Push code to GitHub.
2. Create a new Railway project from your repo.
3. Add environment variables from `.env`.
4. Railway will auto-detect `Dockerfile` and deploy.

### Render

1. Create a new Web Service on Render.
2. Connect your GitHub repo.
3. Set build command to `docker build -t amb-recoup .` or let Render auto-detect `Dockerfile`.
4. Add environment variables.
5. Set start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.

### Fly.io

```bash
fly launch --dockerfile Dockerfile
fly secrets set SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... JWT_SECRET=... APP_SECRET_KEY=...
fly deploy
```

## Supabase Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Go to **Database > SQL Editor** and run `001_initial_schema.sql`.
3. Go to **Storage > New Bucket** and create a public bucket named `receipts`.
4. In **Authentication > Policies**, add RLS policies for your tables or rely on service role from the backend.
5. Copy **Project URL** and **Service Role Key** into your `.env`.

## Project Structure

```
amb-recoup-web/
├── app/
│   ├── main.py              # FastAPI app, router registration
│   ├── config.py            # Settings / env loader
│   ├── database.py          # Supabase client
│   ├── models.py            # Pydantic models
│   ├── auth.py              # Auth dependency / JWT cookie logic
│   └── routers/
│       ├── auth.py          # Login, signup, logout
│       ├── dashboard.py     # Dashboard with date range filters
│       ├── clients.py       # CRUD clients
│       ├── projects.py      # CRUD projects
│       ├── time_entries.py  # CRUD time entries
│       ├── mileage.py       # CRUD mileage + duplicate
│       ├── expenses.py      # CRUD expenses + duplicate + receipt upload
│       ├── reports.py       # CSV exports
│       ├── admin.py         # Superuser admin panel
│       └── settings.py      # Org settings
├── templates/
│   ├── base.html
│   ├── auth/
│   ├── dashboard/
│   ├── clients/
│   ├── projects/
│   ├── time/
│   ├── mileage/
│   ├── expenses/
│   ├── reports/
│   ├── admin/
│   └── settings/
├── static/css/main.css
├── supabase/migrations/001_initial_schema.sql
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env
```

## License

MIT
