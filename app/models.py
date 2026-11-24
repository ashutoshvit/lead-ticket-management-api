from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Product(TimestampMixin, Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(160), index=True)
    sku = Column(String(80), unique=True, index=True)
    description = Column(Text, default=None)
    price = Column(Numeric(12, 2))
    status = Column(String(20), default="active", index=True)


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255), unique=True, index=True)
    phone = Column(String(40), default=None)
    company = Column(String(160), default=None)
    source = Column(String(80), default=None)
    status = Column(String(30), default="new", index=True)
    tickets = relationship("Ticket", back_populates="lead", cascade="all, delete-orphan")


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), default=None, index=True)
    subject = Column(String(200))
    description = Column(Text, default=None)
    status = Column(String(30), default="open", index=True)
    priority = Column(String(20), default="normal")
    lead = relationship("Lead", back_populates="tickets")
    product = relationship("Product")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True)
    topic = Column(String(200), index=True)
    event_type = Column(String(120))
    aggregate_type = Column(String(80))
    aggregate_id = Column(Integer, index=True)
    payload = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), default=None, index=True)

