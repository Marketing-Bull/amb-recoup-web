from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict


class ProjectStatus(str, Enum):
    active = "active"
    on_hold = "on_hold"
    completed = "completed"


class ExpenseCategory(str, Enum):
    software = "software"
    meals = "meals"
    travel = "travel"
    advertising = "advertising"
    office = "office"
    contractors = "contractors"
    other = "other"


class RecurringType(str, Enum):
    none = "none"
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


class Organization(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    name: str
    slug: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True


class OrganizationMember(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    user_id: str
    role: str  # admin, member, viewer
    email: str
    invited_at: Optional[datetime] = None
    joined_at: Optional[datetime] = None
    created_at: datetime


class Client(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    name: str
    hourly_rate: Optional[Decimal] = None
    contact_name: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    notes: str = ""
    is_archived: bool = False
    created_at: datetime


class Project(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    client_id: Optional[str] = None
    name: str
    hourly_rate_override: Optional[Decimal] = None
    status: str = "active"
    notes: str = ""
    is_archived: bool = False
    created_at: datetime


class TimeEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    date: datetime
    hours: float = 0
    rate: Decimal = Decimal("0")
    billable: bool = True
    details: str = ""
    created_at: datetime


class Expense(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    date: datetime
    amount: Decimal = Decimal("0")
    category: str = "other"
    vendor: str = ""
    details: str = ""
    billable: bool = False
    recurring: str = "none"
    receipt_url: Optional[str] = None
    created_at: datetime

    @property
    def is_recurring(self) -> bool:
        return self.recurring != "none"

    @property
    def annualized_amount(self) -> Optional[Decimal]:
        multipliers = {"weekly": Decimal("52"), "monthly": Decimal("12"), "yearly": Decimal("1")}
        if self.recurring in multipliers:
            return self.amount * multipliers[self.recurring]
        return None


class MileageEntry(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    date: datetime
    start_address: str = ""
    end_address: str = ""
    purpose: str = ""
    miles: float = 0
    round_trip: bool = False
    total_miles: float = 0
    billable: bool = False
    created_at: datetime


class OrganizationSetting(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    organization_id: str
    mileage_rate: Decimal = Decimal("0.67")
    created_at: datetime
    updated_at: datetime


class UserContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    email: str
    organization_id: Optional[str] = None
    role: Optional[str] = None
    is_admin: bool = False
    is_superuser: bool = False
