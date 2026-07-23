-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations table (top-level tenant)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    owner_id UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Profiles table (extends Supabase Auth users)
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    role TEXT DEFAULT 'member', -- admin, member, viewer
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organization members (many-to-many with role tracking)
CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member', -- admin, member, viewer
    email TEXT NOT NULL,
    invited_at TIMESTAMPTZ,
    joined_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, user_id)
);

-- Organization settings
CREATE TABLE organization_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE,
    mileage_rate DECIMAL(10,4) DEFAULT 0.67,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Clients
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    hourly_rate DECIMAL(10,2),
    contact_name TEXT DEFAULT '',
    contact_email TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    hourly_rate_override DECIMAL(10,2),
    status TEXT DEFAULT 'active', -- active, on_hold, completed
    notes TEXT DEFAULT '',
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Time entries
CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    hours DECIMAL(10,2) DEFAULT 0,
    rate DECIMAL(10,2) DEFAULT 0,
    billable BOOLEAN DEFAULT TRUE,
    details TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Mileage entries
CREATE TABLE mileage_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_address TEXT DEFAULT '',
    end_address TEXT DEFAULT '',
    purpose TEXT DEFAULT '',
    miles DECIMAL(10,2) DEFAULT 0,
    round_trip BOOLEAN DEFAULT FALSE,
    total_miles DECIMAL(10,2) DEFAULT 0,
    billable BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Expenses
CREATE TABLE expenses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    amount DECIMAL(10,2) DEFAULT 0,
    category TEXT DEFAULT 'other', -- software, meals, travel, advertising, office, contractors, other
    vendor TEXT DEFAULT '',
    details TEXT DEFAULT '',
    billable BOOLEAN DEFAULT FALSE,
    recurring TEXT DEFAULT 'none', -- none, weekly, monthly, yearly
    receipt_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Receipts storage bucket (run via Supabase Dashboard or Storage API)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('receipts', 'receipts', true);

-- RLS Policies for multi-tenancy
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE time_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE mileage_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;

-- Organizations: owners can manage their org, superusers can see all
CREATE POLICY org_owner ON organizations FOR ALL USING (owner_id = auth.uid());

-- Profiles: users can read/update their own, org admins can read org members
CREATE POLICY profile_self ON profiles FOR ALL USING (id = auth.uid());

-- Org members: members can read their org
CREATE POLICY org_member_read ON organization_members FOR SELECT USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Clients: org-scoped
CREATE POLICY clients_org ON clients FOR ALL USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Projects: org-scoped
CREATE POLICY projects_org ON projects FOR ALL USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Time entries: org-scoped
CREATE POLICY time_entries_org ON time_entries FOR ALL USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Mileage entries: org-scoped
CREATE POLICY mileage_entries_org ON mileage_entries FOR ALL USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Expenses: org-scoped
CREATE POLICY expenses_org ON expenses FOR ALL USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Settings: org-scoped
CREATE POLICY settings_org ON organization_settings FOR ALL USING (
    organization_id IN (SELECT organization_id FROM profiles WHERE id = auth.uid())
);

-- Indexes for performance
CREATE INDEX idx_clients_org ON clients(organization_id);
CREATE INDEX idx_projects_org ON projects(organization_id);
CREATE INDEX idx_projects_client ON projects(client_id);
CREATE INDEX idx_time_entries_org ON time_entries(organization_id);
CREATE INDEX idx_time_entries_date ON time_entries(date);
CREATE INDEX idx_mileage_entries_org ON mileage_entries(organization_id);
CREATE INDEX idx_mileage_entries_date ON mileage_entries(date);
CREATE INDEX idx_expenses_org ON expenses(organization_id);
CREATE INDEX idx_expenses_date ON expenses(date);
CREATE INDEX idx_profiles_org ON profiles(organization_id);
CREATE INDEX idx_org_members_org ON organization_members(organization_id);
