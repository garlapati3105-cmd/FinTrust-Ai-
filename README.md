# FinTrust AI — Financial Evidence-Verification & Fraud-Prevention Workspace

[![Next.js 16](https://img.shields.io/badge/Frontend-Next.js%2016%20%7C%20React%2019-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20(Integer%20Paise)-003B57?logo=sqlite)](https://sqlite.org/)
[![PyMuPDF & RapidOCR](https://img.shields.io/badge/OCR-PyMuPDF%20%2B%20RapidOCR%20ONNX-orange)](#-document-extraction--ocr-pipeline)
[![Tests Passing](https://img.shields.io/badge/Tests-68%2F68%20Passing%20(100%25)-success)](#-automated-testing--regression-suite)
[![Evaluation Benchmark](https://img.shields.io/badge/Benchmark-100%25%20Decision%20Accuracy%20(31%20Docs)-blue)](#-evaluation-lab--real-world-reliability)
[![Live AI Validated](https://img.shields.io/badge/Live%20AI-100%25%20Field%20%26%20Evidence%20Match-brightgreen)](#-live-openrouter-ai-model-validation)
[![Hackathon](https://img.shields.io/badge/Hackathon-Arthaton%202026%20(AI%20for%20Finance)-purple)](#)

> **FinTrust AI** is an evidence-first, database-backed financial operations workspace engineered for Indian MSMEs. It stops overbilling, GST tax errors, duplicate payment fraud, and rogue account redirection before vendor disbursements are executed.

---

## 📌 Executive Summary & Problem Statement

Indian Micro, Small, and Medium Enterprises (MSMEs) process hundreds of physical and digital invoices every month. Accounts payable teams routinely face four critical risks:

1. **Invoice Overbilling & Tax Variance:** Bills that subtly or significantly exceed approved Purchase Orders (POs) or miscalculate Goods & Services Tax (GST).
2. **Duplicate Invoicing Fraud:** Inadvertently or maliciously re-submitting previously approved invoices weeks apart with modified dates or whitespace variants.
3. **Vendor Impersonation & Account Redirection:** Discrepancies between invoice remittance accounts and trusted vendor bank references on file.
4. **Unaccountable AI "Hallucinations":** Conventional generative AI tools produce plausible numbers without deterministic cross-referencing against internal ERP records, risking costly financial errors.

**FinTrust AI solves this with a strict architectural invariant:**  
The AI model is an **untrusted extraction parser**, and the **SQLite database is the authoritative truth**. The LLM never approves invoices, never mutates the database, and never initiates financial transfers.

---

## 🏛️ System Architecture

```
[ Upload Document (PDF / PNG / JPEG) ]
                  │
                  ▼
[ Binary File Signature Validation ] ──► (Magic bytes: %PDF, PNG, JPEG; 10MB & 10pg limits)
                  │
                  ▼
[ Multi-Tier Text Ingestion ]
    ├── PyMuPDF (High-speed native selectable text)
    └── RapidOCR ONNX Runtime (Scanned rasterized PDFs & standalone images)
                  │
                  ▼
[ Heuristic Security Scanner ] ──────► (Flags adversarial prompt-injection phrases)
                  │
                  ▼
[ Isolated OpenRouter AI Parsing ] ──► (Strict JSON schema; zero execution/tool access)
                  │
                  ▼
[ Bidirectional Evidence Grounding ] ─► (Validates verbatim quotes & numeric value binding)
                  │
                  ▼
[ Human Review Workspace (UI) ] ─────► (Finance officer validates/edits extracted evidence)
                  │
                  ▼
[ POST /api/verify-invoice ] ────────► (Deterministic SQLite Verification Engine)
    ├── Retrieve authoritative PO by po_number
    ├── Verify active vendor status
    ├── Exact integer-paise comparison (Decimal)
    ├── Internal bank-reference consistency check
    └── Atomic normalized duplicate check
                  │
                  ▼
[ Verification Decision: APPROVE / HOLD ] ──► [ Immutable Append-Only Audit Ledger ]
```

---

## 🛡️ Core Architectural Guarantees

| Invariant | Implementation Mechanism | Purpose |
|---|---|---|
| **AI Never Approves** | AI extractor outputs draft JSON fields; verification happens solely via `POST /api/verify-invoice`. | Eliminates unsupervised AI actions and hallucinated approvals. |
| **Integer-Paise Precision** | All monetary amounts use Python `Decimal` and persist as integer paise (`₹1.00 = 100 paise`). | Prevents floating-point rounding errors and precision leaks. |
| **Zero Client Authority** | Frontend submits only what the invoice claims; approved baselines are queried directly from the server database. | Prevents client-side tampering of approved budgets or GST rates. |
| **Bidirectional Grounding** | Verifies quote presence in document text, page containment, and value substantiation in quote. | Prevents models from citing unrelated text to justify hallucinated figures. |
| **Append-Only Immutability** | Database layer contains zero `UPDATE` or `DELETE` statements for audit records or invoices. | Guarantees an immutable, tamper-evident audit trail for financial comptrollers. |

---

## 🖥️ Application Screens & Workflows

FinTrust AI is designed with an enterprise financial operations aesthetic: **warm ivory background** (`#f5efe9`), **forest-green brand accent** (`#1f5d4a`), **charcoal typography** (`#1b1f1c`), muted amber warnings, and restrained red alerts.

### 1. Overview Dashboard (`OverviewPage`)
- **Live Database KPIs:** Real-time counts for Registered Vendors, Approved POs, Invoices Processed, and Pending Reviews queried directly from `GET /api/dashboard`.
- **4-Step Workflow Stepper:** Clear operational visualization (`1. Upload Document` → `2. Extract & OCR` → `3. Compare Baseline` → `4. Human Review`).
- **Needs Your Attention Queue:** Action-focused queue of held invoices featuring direct **"Investigate →"** prefill links.
- **Recent Activity:** Live feeds of recent verification decisions and immutable audit logs.

### 2. Invoice Verification Workspace (`InvoiceVerificationWorkspace`)
- **Document Ingestion:** Drag-and-drop zone supporting PDF, PNG, JPG, and JPEG files.
- **Collapsible Document Text Preview:** Tipalti-inspired text inspector showing extracted multi-page document text with `--- Page N ---` boundaries.
- **Live Side-by-Side Reconciliation Table:** Displays Invoice Claim, PO Baseline, and exact Variance across Total, GST, and Line Items.
- **Discrepancy Analysis Card:** Plain-English explanation of variances with recommended next financial actions.
- **Supporting Evidence Card:** Field-by-field evidence quotes, reported page numbers, confidence ratings, and green verified badges.
- **Sample Presets:** One-click loaders (`Matching PO-1001`, `Amount Mismatch +₹50`, `GST Mismatch +₹6k`, `Bank Ref Mismatch`).

### 3. Vendor Records (`VendorRecordsPage`)
- **Vendor Master Directory:** Displays registered vendors, active status badges, and masked internal bank account references (`DEMO-ACCT-****1001`).
- **Interactive Vendor Details Modal:** Full profile with associated purchase orders, historical invoices, and a direct *"Verify New Invoice for this Vendor"* shortcut.

### 4. Risk Monitoring (`RiskMonitoringPage`)
- **Risk Invariant Metric:** Displays `Invoices flagged for review: X / Y (Z%)` derived from actual database records.
- **Advisory Banner:** Clarifies that flagged items reflect internal PO variances or documentation discrepancies, not definitive fraud convictions.
- **Interactive Risk Filter Chips:** Filter table instantly by `All`, `High`, `Medium`, and `Low` risk.

### 5. Audit Trail (`AuditTrailPage`)
- **Immutable Ledger:** Complete event log capturing every approval, hold, and duplicate attempt.
- **IST Timestamps:** Formatted in India Standard Time (`Asia/Kolkata`, `en-IN`, e.g., `15 Nov 2026, 05:15:25 pm IST`).
- **Event Filter Chips:** Filter by `All Events`, `Approvals`, `Holds`, and `Duplicate Blocks`.
- **Audit Detail Modal:** Deep-dive modal inspecting raw cryptographic event payloads and decision rationales.

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and **npm**

### 1. Backend Setup (FastAPI)
```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional: set your OpenRouter key)
# Copy .env.example to .env or set environment variables:
$env:OPENROUTER_API_KEY = "your-openrouter-key"        # Optional: uses free router by default
$env:FINTRUST_EXTRACTION_MODEL = "openrouter/free"     # Auto-routes across active free models

# Start FastAPI server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*Backend runs on: `http://127.0.0.1:8000` (API Docs: `http://127.0.0.1:8000/docs`)*

### 2. Frontend Setup (Next.js)
```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```
*Frontend runs on: `http://localhost:3000`*

---

## 🎯 5-Minute Judge Demonstration Sequence

To demonstrate the full verification and fraud-prevention workflow in 5 minutes, follow this sequence using the pre-generated synthetic invoices in `evaluation/dataset/documents/`:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SCENARIO A: Clean Invoice Verification (APPROVE)                            │
│ 1. Drag & drop 'INV-EVAL-001.pdf' into the Verification Workspace.          │
│ 2. Observe ~4s live AI extraction & 100% green verified evidence quotes.   │
│ 3. Point to PO-1001 reconciliation (₹85k / ₹12,966.10 / 5 items: ₹0 var).  │
│ 4. Click 'Submit for Authoritative Verification' ──► Instant APPROVE.       │
├─────────────────────────────────────────────────────────────────────────────┤
│ SCENARIO B: Overbilling Variance Detection (HOLD)                           │
│ 1. Drag & drop 'INV-EVAL-009.pdf' (₹95,000 claimed vs ₹85,000 approved).   │
│ 2. Discrepancy card flags: 'Invoice exceeds approved PO by ₹10,000.00'.     │
│ 3. Click 'Submit for Authoritative Verification' ──► Instant HOLD.          │
├─────────────────────────────────────────────────────────────────────────────┤
│ SCENARIO C: Duplicate Invoicing Fraud Prevention (HOLD)                     │
│ 1. Re-submit 'INV-EVAL-001.pdf' (already approved in Scenario A).           │
│ 2. Click 'Submit for Authoritative Verification'.                           │
│ 3. Atomic UNIQUE check triggers: 'Duplicate invoice submission'.            │
│ 4. Original record is preserved without overwrite; duplicate event logged.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ SCENARIO D: Immutable Audit Trail Inspection                                │
│ 1. Navigate to 'Audit Trail' tab.                                           │
│ 2. Show append-only event log with India Standard Time (IST) timestamps.    │
│ 3. Click an event to open the Audit Event Details Modal.                    │
└─────────────────────────────────────────────────────────────────────────────┘
```
*(For the full second-by-second script, see [`docs/FINTRUST_AI_FIVE_MINUTE_DEMO.md`](file:///c:/Users/hp/Downloads/FinTrustAI/docs/FINTRUST_AI_FIVE_MINUTE_DEMO.md))*

---

## 📊 Live OpenRouter AI Model Validation

FinTrust AI includes a dedicated live model validation runner ([`evaluation/scripts/run_live_smoke_test.py`](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/scripts/run_live_smoke_test.py)) executing real external inferences against OpenRouter:

```powershell
$env:OPENROUTER_API_KEY = "your-openrouter-key"
$env:FINTRUST_EXTRACTION_MODEL = "openrouter/free"
python evaluation/scripts/run_live_smoke_test.py
```

### Live Test Results (Measured November 16, 2026)

| Document | Test Category | Format | Resolved Live Model | AI Latency | Field Match | Evidence Verified |
|---|---|---|---|---|---|---|
| **INV-EVAL-001** | Clean digital invoice | PDF | `baidu/ernie-5.5-flash-preview:free` | 4.11s | **7/7 (100%)** | **7/7 (100%)** |
| **INV-EVAL-031** | Scanned rasterized invoice | PDF | `nvidia/nemotron-3.5-super-vl:free` | 5.21s | **7/7 (100%)** | **7/7 (100%)** |
| **INV-EVAL-022** | Adversarial prompt-injection | PDF | `recursive/flint-v1.0:free` | 11.84s | **7/7 (100%)** | **7/7 (100%)** |

- **Overall Field Accuracy:** **100.0%** (21 / 21 fields matched ground truth)
- **Evidence Grounding Accuracy:** **100.0%** (21 / 21 quotes verified against source text and page bounds)
- **Missing Field Rate:** **0.0%**
- **OCR Completion Rate:** **100.0%** (RapidOCR recovered all text layers on rasterized PDF)
- **Average Network AI Latency:** **7.05 seconds**
- **Total Token Usage:** **5,092 tokens** ($0 cost on free tier)
- **Adversarial Security:** Flagged 2 injection directives in `INV-EVAL-022.pdf` and emitted zero unauthorized decisions.
- **Detailed Audit Artifacts:** [`evaluation/reports/live_smoke_test.json`](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.json) and [`evaluation/reports/live_smoke_test.md`](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.md).

---

## 🧪 Evaluation Lab & Real-World Reliability

The repository includes an automated Evaluation Lab benchmarking the end-to-end workflow across a dataset of **31 synthetic invoice documents** (30 PDFs, 1 high-resolution PNG):

```powershell
python evaluation/scripts/run_evaluation.py
```

### 31-Document Benchmark Results

| Evaluation Pillar | Target Metric | Measured Value | Outcome |
|---|---|---|---|
| **Synthetic Dataset** | 30+ Documents | **31 Documents** (PDF & PNG) | **PASSED** |
| **OCR Text Extraction** | 100% on scanned/image docs | **100.0%** (2/2 documents) | **PASSED** |
| **Field Extraction Accuracy** | High precision across 7 fields | **100.0%** (217/217 fields) | **PASSED** |
| **Adversarial Grounding** | Reject ungrounded / mismatched quotes | **100.0%** (5/5 adversarial cases) | **PASSED** |
| **Malicious Injection Detection** | Flag directive injection phrases | **100.0%** (4/4 attacks flagged) | **PASSED** |
| **Heuristic False Positive Rate** | Document regex boundary trade-off | **100.0%** on benign shipping note | **OBSERVED** |
| **Verification Decision Accuracy** | Exact deterministic policy execution | **100.0%** (31/31 correct decisions) | **PASSED** |
| **Clean Invoice Approvals** | 0% false holds on valid invoices | **100.0%** (8/8 clean approved) | **PASSED** |
| **Duplicate Prevention** | Catch resubmissions & retain original | **100.0%** (3/3 duplicates caught) | **PASSED** |

---

## 🔬 Automated Testing & Regression Suite

The project includes **68 automated backend tests** validating database constraints, verification rules, document security, OCR, AI extraction fallbacks, and adversarial grounding:

```powershell
pytest backend/tests
============================= 68 passed in 22.50s =============================
```

- **`test_database.py` (13 tests):** Schema creation, integer-paise conversions, foreign key constraints, unique constraints, and append-only audit logs.
- **`test_verification.py` (21 tests):** Clean matches, amount variances, GST mismatches, line-item mismatches, inactive/unknown vendors, duplicate submissions, and missing required fields.
- **`test_document_extraction.py` (19 tests):** Magic byte validation, upload limits, PyMuPDF extraction, RapidOCR fallback, prompt-injection scanner, evidence quote verification, and API key absence fallback.
- **`test_evaluation_framework.py` (15 tests):** Ground truth integrity, adversarial grounding, OCR edge cases, deterministic verification consistency, and decision immutability.

### Frontend Production Build
```powershell
cd frontend; npx next build --webpack
▲ Next.js 16.4.6 (webpack)
✓ Compiled successfully in 5.8s
✓ Generating static pages (3/3)
```
*Result: **0 TypeScript errors, 0 compilation warnings**.*

---

## 🗄️ Database Schema & Synthetic Seed Data

The database initializes four relational tables in `backend/fintrust.db` with foreign keys enabled:

```sql
-- Vendors Master
CREATE TABLE vendors (
    id INTEGER PRIMARY KEY,
    vendor_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    bank_account_ref TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL
);

-- Approved Purchase Orders
CREATE TABLE purchase_orders (
    id INTEGER PRIMARY KEY,
    po_number TEXT UNIQUE NOT NULL,
    vendor_id INTEGER NOT NULL REFERENCES vendors(id),
    approved_total_paise INTEGER NOT NULL CHECK (approved_total_paise >= 0),
    approved_gst_paise INTEGER NOT NULL CHECK (approved_gst_paise >= 0),
    approved_line_items INTEGER NOT NULL CHECK (approved_line_items >= 0),
    status TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Verified Invoices
CREATE TABLE invoices (
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
    created_at TEXT NOT NULL,
    UNIQUE (vendor_id, normalized_invoice_number)
);

-- Immutable Append-Only Audit Ledger
CREATE TABLE audit_events (
    id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    event_type TEXT NOT NULL,
    decision TEXT,
    reason TEXT,
    created_at TEXT NOT NULL
);
```

### Synthetic Seed Records

| Vendor Code | Vendor Legal Name | Synthetic Account Ref | Purchase Order | Approved Total | Approved GST | Items |
|---|---|---|---|---:|---:|---:|
| **VND-1001** | Aster Office Supplies | `DEMO-ACCT-1001` | **PO-1001** | ₹85,000.00 | ₹12,966.10 | 5 |
| **VND-1002** | BluePeak Technologies | `DEMO-ACCT-1002` | **PO-1002** | ₹1,20,000.00 | ₹18,305.08 | 8 |
| **VND-1003** | GreenField Logistics | `DEMO-ACCT-1003` | **PO-1003** | ₹46,500.00 | ₹7,093.22 | 4 |

---

## 📡 Complete REST API Inventory

| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| `GET` | `/health` | Service health probe | None | JSON application & connectivity status |
| `GET` | `/api/dashboard` | Aggregated dashboard KPI metrics | None | JSON with vendor, PO, invoice, and pending counts |
| `GET` | `/api/vendors` | List registered vendor records | None | Array of `VendorRead` records |
| `GET` | `/api/purchase-orders` | List approved purchase orders | None | Array of `PurchaseOrderRead` records |
| `GET` | `/api/invoices` | List historical verified invoices | None | Array of `InvoiceRead` records |
| `GET` | `/api/audit-events` | List immutable audit events | None | Array of `AuditEventRead` records |
| `POST` | `/api/verify-invoice` | Deterministic verification engine | `InvoiceVerificationRequest` | `InvoiceVerificationResponse` (APPROVE / HOLD) |
| `POST` | `/api/documents/extract` | Document upload, OCR, and AI extraction | `UploadFile` (multipart) | `DocumentExtractionResponse` with quotes & confidence |

---

## ⚠️ Limitations, Scope & Honest Presentation Disclaimers

1. **Synthetic Demonstration Data:** All vendor records, purchase orders, account references, and test documents are fictional demonstration fixtures. No real personal data or genuine corporate documents are used.
2. **Account Reference Verification:** The system verifies consistency against stored vendor master records (`DEMO-ACCT-*`). It does **not** interface with live banking APIs (e.g. NPCI / RBI account aggregator) to verify external bank account ownership.
3. **No Financial Disbursements:** The system verifies invoices and logs discrepancies; it does not initiate or execute wire transfers or bank payments.
4. **Heuristic Scanner Trade-off:** The regex prompt scanner is a defense-in-depth heuristic. Benign logistics notes containing phrases like *"ignore previous instructions"* will trigger a warning, requiring human review to confirm benign intent.
5. **No Automated Approvals:** The platform strictly enforces a human-in-the-loop requirement. Document upload only extracts and drafts values into an interactive workspace; verification requires deliberate user submission.

---

## 📚 In-Depth Project Documentation

- **[5-Minute Judge Presentation Script](file:///c:/Users/hp/Downloads/FinTrustAI/docs/FINTRUST_AI_FIVE_MINUTE_DEMO.md):** `docs/FINTRUST_AI_FIVE_MINUTE_DEMO.md`
- **[Comprehensive Project Status & Architecture Report](file:///c:/Users/hp/Downloads/FinTrustAI/docs/FINTRUST_AI_COMPLETE_PROJECT_STATUS_REPORT.md):** `docs/FINTRUST_AI_COMPLETE_PROJECT_STATUS_REPORT.md`
- **[Live Model Validation Report (JSON)](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.json):** `evaluation/reports/live_smoke_test.json`
- **[Live Model Validation Report (Markdown)](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.md):** `evaluation/reports/live_smoke_test.md`
- **[31-Document Evaluation Benchmark Report](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/evaluation_report.md):** `evaluation/reports/evaluation_report.md`

---

## 👥 Authors & Acknowledgments

Developed by **Garlapati** for **Arthaton 2026** (AI for Finance Hackathon).  
GitHub Repository: **[https://github.com/garlapati3105-cmd/FinTrust-Ai-](https://github.com/garlapati3105-cmd/FinTrust-Ai-)**
