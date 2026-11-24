from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=80)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    status: Literal["active", "inactive", "discontinued"] = "active"


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: Literal["active", "inactive", "discontinued"] | None = None


class ProductRead(ORMModel):
    id: int
    name: str
    sku: str
    description: str | None
    price: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    company: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=80)
    status: Literal["new", "contacted", "qualified", "converted", "lost"] = "new"


class LeadUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    company: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=80)
    status: Literal["new", "contacted", "qualified", "converted", "lost"] | None = None


class LeadRead(ORMModel):
    id: int
    first_name: str
    last_name: str
    email: EmailStr
    phone: str | None
    company: str | None
    source: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class TicketCreate(BaseModel):
    lead_id: int
    product_id: int | None = None
    subject: str = Field(min_length=1, max_length=200)
    description: str | None = None
    status: Literal["open", "in_progress", "waiting", "resolved", "closed"] = "open"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"


class TicketUpdate(BaseModel):
    lead_id: int | None = None
    product_id: int | None = None
    subject: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: Literal["open", "in_progress", "waiting", "resolved", "closed"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None


class TicketRead(ORMModel):
    id: int
    lead_id: int
    product_id: int | None
    subject: str
    description: str | None
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

