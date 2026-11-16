from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .database import get_connection
from .financial import normalize_invoice_number, to_paise


def _created_at() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def list_vendors(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, vendor_code, name, bank_account_ref, is_active, created_at
            FROM vendors
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_purchase_orders(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                po.id,
                po.po_number,
                po.vendor_id,
                v.vendor_code,
                v.name AS vendor_name,
                po.approved_total_paise,
                po.approved_gst_paise,
                po.approved_line_items,
                po.status,
                po.issue_date,
                po.created_at
            FROM purchase_orders AS po
            JOIN vendors AS v ON v.id = po.vendor_id
            ORDER BY po.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_invoices(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                invoice_number,
                normalized_invoice_number,
                vendor_id,
                po_id,
                invoice_total_paise,
                gst_amount_paise,
                line_items,
                invoice_bank_account_ref,
                decision,
                risk_level,
                created_at
            FROM invoices
            ORDER BY created_at, id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def list_audit_events(db_path: str | Path | None = None) -> list[dict[str, Any]]:
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, entity_type, entity_id, event_type, decision, reason, created_at
            FROM audit_events
            ORDER BY created_at, id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def insert_invoice(
    *,
    invoice_number: str,
    vendor_id: int,
    invoice_total: Decimal | str | int | float,
    gst_amount: Decimal | str | int | float,
    line_items: int,
    po_id: int | None = None,
    invoice_bank_account_ref: str | None = None,
    decision: str | None = None,
    risk_level: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    normalized_number = normalize_invoice_number(invoice_number)
    if not normalized_number:
        raise ValueError("Invoice number must not be empty.")

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO invoices (
                invoice_number,
                normalized_invoice_number,
                vendor_id,
                po_id,
                invoice_total_paise,
                gst_amount_paise,
                line_items,
                invoice_bank_account_ref,
                decision,
                risk_level,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_number,
                normalized_number,
                vendor_id,
                po_id,
                to_paise(invoice_total),
                to_paise(gst_amount),
                line_items,
                invoice_bank_account_ref,
                decision,
                risk_level,
                _created_at(),
            ),
        )
        return int(cursor.lastrowid)


def append_audit_event(
    *,
    entity_type: str,
    event_type: str,
    entity_id: int | None = None,
    decision: str | None = None,
    reason: str | None = None,
    created_at: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO audit_events (
                entity_type, entity_id, event_type, decision, reason, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entity_type,
                entity_id,
                event_type,
                decision,
                reason,
                created_at or _created_at(),
            ),
        )
        return int(cursor.lastrowid)
