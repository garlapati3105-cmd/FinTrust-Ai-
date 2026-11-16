from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .ai_extractor import extract_invoice_fields
from .database import initialize_database
from .document_extractor import extract_document_text
from .document_security import (
    MAX_UPLOAD_SIZE_BYTES,
    detect_file_type,
    scan_for_suspicious_content,
)
from .repository import (
    list_audit_events,
    list_invoices,
    list_purchase_orders,
    list_vendors,
)
from .schemas import (
    AuditEventRead,
    DocumentExtractionResponse,
    DocumentPage,
    InvoiceRead,
    InvoiceVerificationRequest,
    InvoiceVerificationResponse,
    PurchaseOrderRead,
    VendorRead,
)
from .seed import seed_database
from .verification import verify_and_record_invoice


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    seed_database()
    yield


app = FastAPI(title="FinTrust AI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_dashboard_payload() -> dict[str, Any]:
    vendors = list_vendors()
    pos = list_purchase_orders()
    invoices = list_invoices()
    audit_events = list_audit_events()

    vendors_count = len(vendors)
    pos_count = len(pos)
    invoices_count = len(invoices)
    pending_count = len([i for i in invoices if i.get("decision") == "HOLD"])

    vendor_map = {v["id"]: v["name"] for v in vendors}

    recent_cases = []
    for inv in reversed(invoices[-10:]):
        v_name = vendor_map.get(inv.get("vendor_id"), f"Vendor #{inv.get('vendor_id')}")
        status = (
            "Approved"
            if inv.get("decision") == "APPROVE"
            else "Needs review"
            if inv.get("decision") == "HOLD"
            else (inv.get("decision") or "Pending")
        )
        risk = (inv.get("risk_level") or "Low").capitalize()
        recent_cases.append({
            "id": inv["invoice_number"],
            "vendor": v_name,
            "status": status,
            "risk": risk,
            "decision": inv.get("decision"),
            "amount_paise": inv.get("invoice_total_paise", 0),
        })

    recent_audit = []
    for ev in reversed(audit_events[-10:]):
        recent_audit.append({
            "action": ev.get("reason") or ev.get("event_type", "Event logged"),
            "time": ev.get("created_at", ""),
            "decision": ev.get("decision"),
            "id": ev.get("id"),
        })

    return {
        "connected": True,
        "status": "healthy",
        "source": "database-backed",
        "workspace": "MSME / 001",
        "summary": [
            {
                "label": "Registered vendors",
                "value": f"{vendors_count:02d}",
                "note": "Trusted database entities",
                "tone": "slate",
            },
            {
                "label": "Approved purchase orders",
                "value": f"{pos_count:02d}",
                "note": "Active PO baselines",
                "tone": "green",
            },
            {
                "label": "Invoices processed",
                "value": f"{invoices_count:02d}",
                "note": "Stored verification records",
                "tone": "amber" if invoices_count > 0 else "slate",
            },
            {
                "label": "Pending reviews",
                "value": f"{pending_count:02d}",
                "note": "Held for investigation",
                "tone": "red" if pending_count > 0 else "slate",
            },
        ],
        "cases": recent_cases,
        "audit_entries": recent_audit,
    }


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Welcome to the FinTrust AI API"}


@app.get("/health")
@app.get("/api/health")
def read_health() -> dict[str, Any]:
    return {
        "status": "healthy",
        "application": "FinTrust AI",
        "version": "0.1.0",
        "backend": "connected",
        "source": "local-fastapi",
    }


@app.get("/api/dashboard")
def get_dashboard() -> dict[str, Any]:
    return build_dashboard_payload()


@app.get("/api/vendors", response_model=list[VendorRead])
def get_vendors() -> list[VendorRead]:
    return [VendorRead(**vendor) for vendor in list_vendors()]


@app.get("/api/purchase-orders", response_model=list[PurchaseOrderRead])
def get_purchase_orders() -> list[PurchaseOrderRead]:
    return [PurchaseOrderRead(**order) for order in list_purchase_orders()]


@app.get("/api/invoices", response_model=list[InvoiceRead])
def get_invoices() -> list[InvoiceRead]:
    return [InvoiceRead(**invoice) for invoice in list_invoices()]


@app.get("/api/audit-events", response_model=list[AuditEventRead])
def get_audit_events() -> list[AuditEventRead]:
    return [AuditEventRead(**event) for event in list_audit_events()]


@app.post("/api/verify-invoice")
def verify_invoice_endpoint(
    payload: InvoiceVerificationRequest,
) -> InvoiceVerificationResponse:
    return InvoiceVerificationResponse(**verify_and_record_invoice(payload))


@app.post("/api/documents/extract", response_model=DocumentExtractionResponse)
async def extract_document_endpoint(
    file: UploadFile = File(...),
) -> DocumentExtractionResponse:
    # 1. Sanitize filename: never use user-supplied path components
    safe_filename = Path(file.filename or "uploaded_document").name

    # 2. Read file content safely in memory and validate file size
    try:
        content = await file.read()
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {err}")

    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File size ({len(content) / (1024 * 1024):.2f} MB) exceeds maximum "
                f"upload limit of {MAX_UPLOAD_SIZE_BYTES / (1024 * 1024):.0f} MB."
            ),
        )

    # 3. Validate actual file signature (magic bytes)
    try:
        file_type = detect_file_type(content, safe_filename)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    # 4. Extract document text with page boundaries and OCR fallback
    try:
        doc_result = extract_document_text(content, file_type)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err))

    # 5. Scan extracted text for prompt-injection instructions
    suspicious_warnings = scan_for_suspicious_content(doc_result.full_text)
    suspicious_detected = len(suspicious_warnings) > 0

    # 6. Run AI-assisted field extraction with server-side evidence verification
    pages_text_map = {p.page_number: p.text for p in doc_result.pages}
    fields, ai_available, model_name, ai_warnings = extract_invoice_fields(
        doc_result.full_text, pages_text=pages_text_map
    )

    # 7. Formulate structured response (never directly approves or executes)
    return DocumentExtractionResponse(
        filename=safe_filename,
        file_type=doc_result.file_type,
        page_count=doc_result.page_count,
        pages=[
            DocumentPage(
                page_number=p.page_number,
                text=p.text,
                ocr_applied=p.ocr_applied,
            )
            for p in doc_result.pages
        ],
        raw_text=doc_result.full_text,
        ocr_applied=doc_result.ocr_applied,
        ocr_engine=doc_result.ocr_engine,
        ai_extraction_available=ai_available,
        ai_model=model_name,
        fields=fields,
        suspicious_content_detected=suspicious_detected,
        suspicious_warnings=suspicious_warnings,
        processing_warnings=ai_warnings,
    )

