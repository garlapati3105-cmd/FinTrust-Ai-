from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .database import get_connection
from .financial import to_paise

VENDORS = (
    ("VND-1001", "Aster Office Supplies", "DEMO-ACCT-1001"),
    ("VND-1002", "BluePeak Technologies", "DEMO-ACCT-1002"),
    ("VND-1003", "GreenField Logistics", "DEMO-ACCT-1003"),
)

PURCHASE_ORDERS = (
    ("PO-1001", "VND-1001", Decimal("85000.00"), Decimal("12966.10"), 5, "2026-10-28"),
    ("PO-1002", "VND-1002", Decimal("120000.00"), Decimal("18305.08"), 8, "2026-11-02"),
    ("PO-1003", "VND-1003", Decimal("46500.00"), Decimal("7093.22"), 4, "2026-11-05"),
)


def seed_database(db_path: str | Path | None = None) -> dict[str, int]:
    inserted_vendors = 0
    inserted_purchase_orders = 0
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with get_connection(db_path) as connection:
        for vendor_code, name, bank_account_ref in VENDORS:
            existing = connection.execute(
                "SELECT id FROM vendors WHERE vendor_code = ?",
                (vendor_code,),
            ).fetchone()
            if existing is None:
                connection.execute(
                    """
                    INSERT INTO vendors (vendor_code, name, bank_account_ref, is_active, created_at)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (vendor_code, name, bank_account_ref, created_at),
                )
                inserted_vendors += 1

        for po_number, vendor_code, total, gst, line_items, issue_date in PURCHASE_ORDERS:
            existing = connection.execute(
                "SELECT id FROM purchase_orders WHERE po_number = ?",
                (po_number,),
            ).fetchone()
            if existing is not None:
                continue

            vendor = connection.execute(
                "SELECT id FROM vendors WHERE vendor_code = ?",
                (vendor_code,),
            ).fetchone()
            if vendor is None:
                raise ValueError(f"Cannot seed {po_number}: vendor {vendor_code} does not exist.")

            connection.execute(
                """
                INSERT INTO purchase_orders (
                    po_number,
                    vendor_id,
                    approved_total_paise,
                    approved_gst_paise,
                    approved_line_items,
                    status,
                    issue_date,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, 'approved', ?, ?)
                """,
                (
                    po_number,
                    vendor["id"],
                    to_paise(total),
                    to_paise(gst),
                    line_items,
                    issue_date,
                    created_at,
                ),
            )
            inserted_purchase_orders += 1

    return {
        "vendors": inserted_vendors,
        "purchase_orders": inserted_purchase_orders,
        "invoices": 0,
        "audit_events": 0,
    }
