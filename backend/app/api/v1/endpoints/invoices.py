from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCheckoutCreate,
    InvoiceCheckoutResponse,
    InvoiceCreate,
    InvoiceNumberRead,
    InvoicePreviewBundleRead,
    InvoicePreviewSessionCreate,
    InvoicePreviewSessionRead,
    InvoiceRead,
)
from app.services.invoice_preview_service import enrich_preview_payloads, get_invoice_preview_by_no
from app.services.invoice_preview_store import create_preview_session, get_preview_session
from app.services.invoice_service import checkout_invoice, create_invoice, get_invoice, get_next_invoice_no

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
InvoicePreviewUser = Annotated[User, Depends(require_permission("reports", "preview_invoice"))]
InvoiceCreateUser = Annotated[User, Depends(require_permission("classes", "continue_payment"))]


@router.get("/next-number", response_model=InvoiceNumberRead)
def read_next_invoice_number(db: DbSession, current_user: InvoiceCreateUser):
    return InvoiceNumberRead(invoice_no=get_next_invoice_no(db))


@router.post("/preview-sessions", response_model=InvoicePreviewSessionRead)
def create_invoice_preview_session(
    payload: InvoicePreviewSessionCreate,
    db: DbSession,
    current_user: InvoicePreviewUser,
):
    raw = [item.model_dump(by_alias=True) for item in payload.invoices]
    enriched = enrich_preview_payloads(db, raw)
    preview_key = create_preview_session(enriched)
    return InvoicePreviewSessionRead(preview_key=preview_key)


@router.get("/preview-sessions/{preview_key}", response_model=InvoicePreviewBundleRead)
def read_invoice_preview_session(
    preview_key: str,
    current_user: InvoicePreviewUser,
):
    invoices = get_preview_session(preview_key)
    if invoices is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preview session not found")
    return InvoicePreviewBundleRead(invoices=invoices, invoice=invoices[0] if len(invoices) == 1 else None)


@router.get("/by-no/{invoice_no}/preview", response_model=InvoicePreviewBundleRead)
def read_invoice_preview_by_no(
    invoice_no: str,
    db: DbSession,
    current_user: InvoicePreviewUser,
):
    preview = get_invoice_preview_by_no(db, invoice_no)
    if not preview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return InvoicePreviewBundleRead(invoices=[preview], invoice=preview)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def read_invoice(invoice_id: int, db: DbSession, current_user: InvoicePreviewUser):
    invoice = get_invoice(db, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice_endpoint(payload: InvoiceCreate, db: DbSession, current_user: InvoiceCreateUser):
    return create_invoice(db, payload, username=current_user.name)


@router.post("/checkout", response_model=dict[str, InvoiceCheckoutResponse], status_code=status.HTTP_201_CREATED)
def checkout_invoice_endpoint(payload: InvoiceCheckoutCreate, db: DbSession, current_user: InvoiceCreateUser):
    checkout = checkout_invoice(db, payload, username=current_user.name)
    return {"data": checkout}
