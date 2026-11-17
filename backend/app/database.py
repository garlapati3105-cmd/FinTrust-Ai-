from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parents[1] / "fintrust.db"

_TABLES = (
    """
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY,
        vendor_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        bank_account_ref TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        gstin TEXT,
        gstin_verification_status TEXT NOT NULL DEFAULT 'NOT_VERIFIED',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS purchase_orders (
        id INTEGER PRIMARY KEY,
        po_number TEXT UNIQUE NOT NULL,
        vendor_id INTEGER NOT NULL REFERENCES vendors(id),
        approved_total_paise INTEGER NOT NULL CHECK (approved_total_paise >= 0),
        approved_gst_paise INTEGER NOT NULL CHECK (approved_gst_paise >= 0),
        approved_line_items INTEGER NOT NULL CHECK (approved_line_items >= 0),
        status TEXT NOT NULL,
        issue_date TEXT NOT NULL,
        recipient_gstin TEXT,
        place_of_supply_state_code TEXT,
        gst_transaction_profile TEXT NOT NULL DEFAULT 'STANDARD_DOMESTIC',
        approved_cgst_paise INTEGER NOT NULL DEFAULT 0,
        approved_sgst_paise INTEGER NOT NULL DEFAULT 0,
        approved_utgst_paise INTEGER NOT NULL DEFAULT 0,
        approved_igst_paise INTEGER NOT NULL DEFAULT 0,
        approved_cess_paise INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY,
        invoice_number TEXT NOT NULL,
        normalized_invoice_number TEXT NOT NULL,
        vendor_id INTEGER NOT NULL REFERENCES vendors(id),
        po_id INTEGER REFERENCES purchase_orders(id),
        invoice_total_paise INTEGER NOT NULL CHECK (invoice_total_paise >= 0),
        gst_amount_paise INTEGER NOT NULL CHECK (gst_amount_paise >= 0),
        line_items INTEGER NOT NULL CHECK (line_items >= 0),
        invoice_bank_account_ref TEXT,
        decision TEXT,
        risk_level TEXT,
        supplier_gstin TEXT,
        recipient_gstin TEXT,
        place_of_supply_state_code TEXT,
        cgst_paise INTEGER NOT NULL DEFAULT 0,
        sgst_paise INTEGER NOT NULL DEFAULT 0,
        utgst_paise INTEGER NOT NULL DEFAULT 0,
        igst_paise INTEGER NOT NULL DEFAULT 0,
        cess_paise INTEGER NOT NULL DEFAULT 0,
        gst_validation_status TEXT,
        created_at TEXT NOT NULL,
        UNIQUE (vendor_id, normalized_invoice_number)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_events (
        id INTEGER PRIMARY KEY,
        entity_type TEXT NOT NULL,
        entity_id INTEGER,
        event_type TEXT NOT NULL,
        decision TEXT,
        reason TEXT,
        created_at TEXT NOT NULL
    )
    """,
)

_INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_purchase_orders_vendor_id ON purchase_orders(vendor_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_vendor_id ON invoices(vendor_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_po_id ON invoices(po_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_created_at ON invoices(created_at)",
    "CREATE INDEX IF NOT EXISTS idx_audit_events_created_at ON audit_events(created_at, id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type, entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_vendors_gstin ON vendors(gstin)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_supplier_gstin ON invoices(supplier_gstin)",
)


def migrate_database(connection: sqlite3.Connection) -> None:
    """
    Safe, idempotent migration to extend existing tables with GST fields.
    Does not drop tables or alter existing data.
    """
    # 1. Vendors columns
    vendor_cols = {row["name"] for row in connection.execute("PRAGMA table_info(vendors)").fetchall()}
    if "gstin" not in vendor_cols:
        connection.execute("ALTER TABLE vendors ADD COLUMN gstin TEXT")
    if "gstin_verification_status" not in vendor_cols:
        connection.execute("ALTER TABLE vendors ADD COLUMN gstin_verification_status TEXT NOT NULL DEFAULT 'NOT_VERIFIED'")

    # 2. Purchase Orders columns
    po_cols = {row["name"] for row in connection.execute("PRAGMA table_info(purchase_orders)").fetchall()}
    if "recipient_gstin" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN recipient_gstin TEXT")
    if "place_of_supply_state_code" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN place_of_supply_state_code TEXT")
    if "gst_transaction_profile" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN gst_transaction_profile TEXT NOT NULL DEFAULT 'STANDARD_DOMESTIC'")
    if "approved_cgst_paise" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN approved_cgst_paise INTEGER NOT NULL DEFAULT 0")
    if "approved_sgst_paise" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN approved_sgst_paise INTEGER NOT NULL DEFAULT 0")
    if "approved_utgst_paise" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN approved_utgst_paise INTEGER NOT NULL DEFAULT 0")
    if "approved_igst_paise" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN approved_igst_paise INTEGER NOT NULL DEFAULT 0")
    if "approved_cess_paise" not in po_cols:
        connection.execute("ALTER TABLE purchase_orders ADD COLUMN approved_cess_paise INTEGER NOT NULL DEFAULT 0")

    # 3. Invoices columns
    invoice_cols = {row["name"] for row in connection.execute("PRAGMA table_info(invoices)").fetchall()}
    if "supplier_gstin" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN supplier_gstin TEXT")
    if "recipient_gstin" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN recipient_gstin TEXT")
    if "place_of_supply_state_code" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN place_of_supply_state_code TEXT")
    if "cgst_paise" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN cgst_paise INTEGER NOT NULL DEFAULT 0")
    if "sgst_paise" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN sgst_paise INTEGER NOT NULL DEFAULT 0")
    if "utgst_paise" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN utgst_paise INTEGER NOT NULL DEFAULT 0")
    if "igst_paise" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN igst_paise INTEGER NOT NULL DEFAULT 0")
    if "cess_paise" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN cess_paise INTEGER NOT NULL DEFAULT 0")
    if "gst_validation_status" not in invoice_cols:
        connection.execute("ALTER TABLE invoices ADD COLUMN gst_validation_status TEXT")


@contextmanager
def get_connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    path = Path(db_path) if db_path is not None else DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as connection:
        for statement in _TABLES:
            connection.execute(statement)
        migrate_database(connection)
        for statement in _INDEXES:
            connection.execute(statement)
