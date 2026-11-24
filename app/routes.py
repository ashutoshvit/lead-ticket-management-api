import json

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from redis import Redis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.events import record_event
from app.models import Lead, Product, Ticket
from app.schemas import (LeadCreate, LeadRead, LeadUpdate, ProductCreate, ProductRead,
                         ProductUpdate, TicketCreate, TicketRead, TicketUpdate)

router = APIRouter()
cache = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2,
                       socket_timeout=2)


def invalidate_products() -> None:
    try:
        keys = list(cache.scan_iter(match="products:list:*"))
        if keys:
            cache.delete(*keys)
    except Exception:
        pass


def save_or_conflict(db: Session, message: str) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=message) from exc


def flush_or_conflict(db: Session, message: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=message) from exc


@router.get("/products", response_model=list[ProductRead], tags=["products"])
def list_products(db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500),
                  offset: int = Query(0, ge=0), status_filter: str | None = Query(None, alias="status")):
    cache_key = f"products:list:{limit}:{offset}:{status_filter or '*'}"
    try:
        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass
    query = select(Product).order_by(Product.id).limit(limit).offset(offset)
    if status_filter:
        query = query.where(Product.status == status_filter)
    products = db.scalars(query).all()
    payload = [ProductRead.model_validate(p).model_dump(mode="json") for p in products]
    try:
        cache.setex(cache_key, settings.cache_ttl_seconds, json.dumps(payload))
    except Exception:
        pass
    return products


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED, tags=["products"])
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**data.model_dump())
    db.add(product)
    flush_or_conflict(db, "A product with this SKU already exists")
    record_event(db, "product.created", "product", product.id, data.model_dump(mode="json"))
    save_or_conflict(db, "A product with this SKU already exists")
    invalidate_products()
    db.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductRead, tags=["products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    return product


@router.patch("/products/{product_id}", response_model=ProductRead, tags=["products"])
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(product, key, value)
    flush_or_conflict(db, "A product with this SKU already exists")
    record_event(db, "product.updated", "product", product.id, changes)
    save_or_conflict(db, "A product with this SKU already exists")
    invalidate_products()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["products"])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(404, "Product not found")
    record_event(db, "product.deleted", "product", product.id, {"id": product.id, "sku": product.sku})
    db.delete(product)
    db.commit()
    invalidate_products()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/leads", response_model=list[LeadRead], tags=["leads"])
def list_leads(db: Session = Depends(get_db), limit: int = Query(100, ge=1, le=500),
               offset: int = Query(0, ge=0), status_filter: str | None = Query(None, alias="status")):
    query = select(Lead).order_by(Lead.id).limit(limit).offset(offset)
    if status_filter:
        query = query.where(Lead.status == status_filter)
    return db.scalars(query).all()


@router.post("/leads", response_model=LeadRead, status_code=status.HTTP_201_CREATED, tags=["leads"])
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    lead = Lead(**data.model_dump())
    db.add(lead)
    flush_or_conflict(db, "A lead with this email already exists")
    record_event(db, "lead.created", "lead", lead.id, data.model_dump(mode="json"))
    save_or_conflict(db, "A lead with this email already exists")
    db.refresh(lead)
    return lead


@router.get("/leads/{lead_id}", response_model=LeadRead, tags=["leads"])
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    return lead


@router.patch("/leads/{lead_id}", response_model=LeadRead, tags=["leads"])
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(lead, key, value)
    flush_or_conflict(db, "A lead with this email already exists")
    record_event(db, "lead.updated", "lead", lead.id, changes)
    save_or_conflict(db, "A lead with this email already exists")
    db.refresh(lead)
    return lead


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["leads"])
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(404, "Lead not found")
    record_event(db, "lead.deleted", "lead", lead.id, {"id": lead.id, "email": lead.email})
    db.delete(lead)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/tickets", response_model=list[TicketRead], tags=["tickets"])
def list_tickets(db: Session = Depends(get_db), lead_id: int | None = None,
                 ticket_status: str | None = Query(None, alias="status"),
                 limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    query = select(Ticket).order_by(Ticket.id).limit(limit).offset(offset)
    if lead_id is not None:
        query = query.where(Ticket.lead_id == lead_id)
    if ticket_status:
        query = query.where(Ticket.status == ticket_status)
    return db.scalars(query).all()


@router.post("/tickets", response_model=TicketRead, status_code=status.HTTP_201_CREATED, tags=["tickets"])
def create_ticket(data: TicketCreate, db: Session = Depends(get_db)):
    if db.get(Lead, data.lead_id) is None:
        raise HTTPException(404, "Lead not found")
    if data.product_id is not None and db.get(Product, data.product_id) is None:
        raise HTTPException(404, "Product not found")
    ticket = Ticket(**data.model_dump())
    db.add(ticket)
    db.flush()
    record_event(db, "ticket.created", "ticket", ticket.id, data.model_dump())
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets/{ticket_id}", response_model=TicketRead, tags=["tickets"])
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.patch("/tickets/{ticket_id}", response_model=TicketRead, tags=["tickets"])
def update_ticket(ticket_id: int, data: TicketUpdate, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("lead_id") is not None and db.get(Lead, changes["lead_id"]) is None:
        raise HTTPException(404, "Lead not found")
    if changes.get("product_id") is not None and db.get(Product, changes["product_id"]) is None:
        raise HTTPException(404, "Product not found")
    for key, value in changes.items():
        setattr(ticket, key, value)
    db.flush()
    record_event(db, "ticket.updated", "ticket", ticket.id, changes)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["tickets"])
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    record_event(db, "ticket.deleted", "ticket", ticket.id, {"id": ticket.id})
    db.delete(ticket)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

