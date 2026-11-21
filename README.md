# FinTrust AI — Financial Evidence-Verification & Discrepancy-Detection Workspace

[![Next.js 16](https://img.shields.io/badge/Frontend-Next.js%2016%20%7C%20React%2019-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite%20(Integer%20Paise)-003B57?logo=sqlite)](https://sqlite.org/)
[![PyMuPDF & RapidOCR](https://img.shields.io/badge/OCR-PyMuPDF%20%2B%20RapidOCR%20ONNX-orange)](#-document-extraction--ocr-pipeline)
[![GST Engine](https://img.shields.io/badge/GST%20Engine-India%20GST%20(Luhn%20Mod%2036)-1f5d4a)](#-india-gst-integrity-engine)
[![Tests Passing](https://img.shields.io/badge/Tests-123%2F123%20Passing%20(100%25)-success)](#-automated-testing--regression-suite)
[![Evaluation Benchmark](https://img.shields.io/badge/Benchmark-31--Doc%20Synthetic%20Benchmark%20(100%25%20Accuracy)-blue)](#-evaluation-lab--31-document-synthetic-offline-benchmark)
[![Live AI Validated](https://img.shields.io/badge/Live%20AI-3--Doc%20Smoke%20Test%20(21%2F21%20Fields)-brightgreen)](#-live-openrouter-ai-model-validation)
[![Hackathon](https://img.shields.io/badge/Hackathon-Arthaton%202026%20(AI%20for%20Finance)-purple)](#)

> **FinTrust AI** is an evidence-first, database-backed financial verification and discrepancy-detection layer engineered for Indian MSMEs. It surfaces overbilling, GST tax calculation variances, duplicate invoice submissions, and unapproved bank account references before payment decisions are made.

---

## 📌 Executive Summary & Problem Statement

Indian Micro, Small, and Medium Enterprises (MSMEs) process hundreds of physical and digital invoices each month across multiple operational workflows. Accounts payable and finance teams routinely face four critical operational risks:

1. **Invoice Overbilling & Tax Variance:** Bills that subtly or significantly deviate from approved Purchase Orders (POs) or miscalculate Goods & Services Tax (GST) rates.
2. **Duplicate Invoice Submissions:** Inadvertently or maliciously re-submitting previously approved invoice numbers weeks apart with modified dates, casing, or whitespace.
3. **Unapproved Bank Account Discrepancies:** Discrepancies between invoice remittance accounts and trusted vendor bank references on file in the internal master database.
4. **Unaccountable AI "Hallucinations":** Conventional generative AI extractors can hallucinate plausible numbers without verifiable source quotes or deterministic cross-referencing against internal ERP records, risking costly financial errors.

### The Architectural Differentiator

While OCR and document matching tools exist in isolation, FinTrust AI bridges the trust gap through a strict separation of concerns:
- **The AI model is an untrusted extraction parser**: It extracts draft field suggestions from document text and must supply verbatim supporting quotes with character-level containment and value substantiation.
- **The SQLite database is the authoritative baseline**: The LLM never decides invoice validity, never approves invoices, never mutates the database, and never initiates financial transactions.
- **Authoritative verification is 100% deterministic**: The backend computes monetary comparisons in exact integer paise via Python `Decimal`, validates active vendor status, verifies internal bank references, checks unique vendor/invoice constraints, and issues an `APPROVE` or `HOLD` recommendation for human review.

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
[ Verification Decision: APPROVE / HOLD ] ──► [ Application-Level Append-Only Audit Ledger ]
```

---

## 🛡️ Core Architectural Guarantees

| Invariant | Implementation Mechanism | Purpose |
|---|---|---|
| **No AI-Initiated Approval** | AI extractor outputs draft JSON field suggestions; authoritative verification decisions are computed solely by the backend deterministic verification engine via `POST /api/verify-invoice` upon human submission. | Eliminates unsupervised AI actions and hallucinated approvals. |
| **Integer-Paise Precision** | All monetary amounts use Python `Decimal` and persist as integer paise (`₹1.00 = 100 paise`). | Prevents floating-point rounding errors and precision leaks. |
| **Zero Client Authority** | The frontend submits only what the invoice claims; approved purchase order values and vendor bank references are queried directly from the server database. | Prevents client-side tampering of approved budgets or GST rates. |
| **India GST Integrity Engine** | Validates 15-character GSTINs via Luhn mod 36, identifies State/UT codes, enforces Sections 7 & 8 of the IGST Act (CGST+SGST/UTGST vs IGST), and reconciles component breakdowns within internal ₹1.00 business tolerance. | Prevents tax-type misclassification and invalid GST filings. |
| **Bidirectional Grounding** | Verifies quote presence in document text, page containment, and value substantiation within the quote. | Prevents models from citing unrelated text to justify hallucinated figures. |
| **Application-Level Append-Only Audit Trail** | The application backend exposes strictly append-only `INSERT` operations for audit events with no `UPDATE` or `DELETE` API endpoints or repository methods. | Maintains an immutable operational ledger for financial reviews. (See limitations regarding direct database-file access). |

---

## 🖥️ Application Screens & Workflows

FinTrust AI is designed with an enterprise financial operations aesthetic: **warm ivory background** (`#fbfaf8`), **forest-green brand accent** (`#1f5d4a`), **charcoal typography** (`#1d2524`), dark mode support (`#0f1412` page, `#18201d` surfaces), muted amber warnings, and restrained red alerts.

### 1. Overview Dashboard (`OverviewPage`)
- **Live Database KPIs:** Real-time counts for Registered Vendors, Approved POs, Invoices Processed, and Pending Reviews queried directly from `GET /api/dashboard`.
- **4-Step Workflow Stepper:** Clear operational visualization (`1. Upload Document` → `2. Extract & OCR` → `3. Compare Baseline` → `4. Human Review`).
- **Needs Your Attention Queue:** Action-focused queue of held invoices featuring direct **"Investigate →"** prefill links.
- **Recent Activity:** Live feeds of recent verification decisions and append-only audit logs.

### 2. Invoice Verification Workspace (`InvoiceVerificationWorkspace`)
- **Document Ingestion:** Drag-and-drop zone supporting PDF, PNG, JPG, and JPEG files.
- **Collapsible Document Text Preview:** Text inspector showing extracted multi-page document text with `--- Page N ---` boundaries.
- **Live Side-by-Side Reconciliation Table:** Displays Invoice Claim, PO Baseline, and exact Variance across Total, GST, and Line Items.
- **India GST Integrity Engine Panel:** Real-time statutory GST analysis displaying Supplier GSTIN (with Luhn checksum validation), Recipient GSTIN matching, Place of Supply State identification, Intra-State vs Inter-State classification (CGST+SGST/UTGST vs IGST), and component breakdown reconciliation.
- **Discrepancy Analysis Card:** Plain-English explanation of variances with recommended next financial actions.
- **Supporting Evidence Card:** Field-by-field evidence quotes, reported page numbers, confidence ratings, and green verified badges.
- **Sample Presets:** One-click loaders (`Intra-State Clean PO-1001`, `Inter-State Clean PO-1002`, `Intra-UT Clean PO-1003`, `Tax Type Mismatch`, `Amount Mismatch +₹50`, `Invalid GSTIN Checksum`).

### 3. Vendor Records (`VendorRecordsPage`)
- **Vendor Master Directory:** Displays registered vendors, active status badges, and masked internal bank account references (`DEMO-ACCT-****1001`).
- **Interactive Vendor Details Modal:** Full profile with associated purchase orders, historical invoices, and a direct *"Verify New Invoice for this Vendor"* shortcut.

### 4. Risk Monitoring (`RiskMonitoringPage`)
- **Risk Invariant Metric:** Displays `Invoices flagged for review: X / Y (Z%)` derived from actual database records.
- **Advisory Banner:** Clarifies that flagged items reflect internal PO variances or documentation discrepancies, not definitive fraud convictions.
- **Interactive Risk Filter Chips:** Filter table instantly by `All`, `High`, `Medium`, and `Low` risk.

### 5. Audit Trail (`AuditTrailPage`)
- **Application-Level Append-Only Ledger:** Complete event log capturing every approval, hold, and duplicate submission attempt.
- **IST Timestamps:** Formatted in India Standard Time (`Asia/Kolkata`, `en-IN`, e.g., `15 Nov 2026, 05:15:25 pm IST`).
- **Event Filter Chips:** Filter by `All Events`, `Approvals`, `Holds`, and `Duplicate Blocks`.
- **Audit Detail Modal:** Detailed modal inspecting stored audit event attributes (`entity_type`, `entity_id`, `event_type`, `decision`, `reason`, `created_at`) and decision rationales.

---

## ⚡ Quickstart Guide

### Prerequisites
- **Python 3.11+** (Tested in Python 3.12.7)
- **Node.js 20.9+** (Required by Next.js 16.4.6) and **npm**

### OpenRouter API Configuration
- **Live External Inference:** An OpenRouter API key is **required** for live external AI extraction. Set `$env:OPENROUTER_API_KEY = "your-key"` in your shell before starting the backend.
- **Model Selection & Rate Limits:** The default model setting is `openrouter/free`. This routes dynamically across currently available free models on OpenRouter at zero token cost. However, free models remain subject to OpenRouter's rate limits (requests per minute/day), and the returned provider model identifier may differ from request to request.
- **Operation Without API Key:** When `OPENROUTER_API_KEY` is not set, the platform remains fully functional for manual entry, document upload, selectable PDF text extraction (PyMuPDF), and local OCR fallback (RapidOCR). Only live AI field extraction is disabled, with a clear notification banner displayed in the UI.

### 1. Backend Setup (FastAPI)
```powershell
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment for live AI extraction (optional, but required for external inference)
$env:OPENROUTER_API_KEY = "your-openrouter-api-key"
$env:FINTRUST_EXTRACTION_MODEL = "openrouter/free"

# Start FastAPI server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
*Backend runs on: `http://127.0.0.1:8000` (Interactive API Docs: `http://127.0.0.1:8000/docs`)*

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

To demonstrate the full verification and discrepancy-detection workflow in 5 minutes, follow this sequence using the pre-generated synthetic invoices in `evaluation/dataset/documents/`:

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
│ SCENARIO C: Duplicate Invoice Submission Detection (HOLD)                   │
│ 1. Re-submit 'INV-EVAL-001.pdf' (already approved in Scenario A).           │
│ 2. Click 'Submit for Authoritative Verification'.                           │
│ 3. Atomic UNIQUE constraint triggers: 'Duplicate invoice submission'.       │
│ 4. Original record is preserved without overwrite; duplicate event logged.  │
├─────────────────────────────────────────────────────────────────────────────┤
│ SCENARIO D: Application-Level Audit Trail Inspection                        │
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

### Live Smoke Test Results (Historical Baseline & Current Framework)

> [!NOTE]
> **Measurement History & 15-Field Support:**
> The table below records the historical live baseline measured on November 16, 2026 across **three synthetic documents** (21 total field assertions: 7 base fields × 3 documents) using dynamically resolved OpenRouter free models. The current evaluation framework has been upgraded to support all **15 schema fields** (7 base + 8 GST fields). In the current runtime, when `OPENROUTER_API_KEY` is not present, `run_live_smoke_test.py` safely completes in `SKIPPED` mode without making external network calls and without fabricating simulated model predictions or accuracy scores.

| Document | Test Category | Format | Resolved Live Model | AI Latency | Field Match (7 Base Fields) | Evidence Verified |
|---|---|---|---|---|---|---|
| **INV-EVAL-001** | Clean digital invoice | PDF | `baidu/ernie-5.5-flash-preview:free` | 4.11s | **7/7 (100%)** | **7/7 (100%)** |
| **INV-EVAL-031** | Scanned rasterized invoice | PDF | `nvidia/nemotron-3.5-super-vl:free` | 5.21s | **7/7 (100%)** | **7/7 (100%)** |
| **INV-EVAL-022** | Adversarial prompt-injection | PDF | `recursive/flint-v1.0:free` | 11.84s | **7/7 (100%)** | **7/7 (100%)** |

- **Field Extraction Match (Historical 7-Field Run):** **100.0%** (21 / 21 fields matched ground truth across the 3 live test documents)
- **Evidence Grounding Accuracy:** **100.0%** (21 / 21 quotes verified against source text and page bounds)
- **Missing Field Rate:** **0.0%** (0 / 21 fields missing)
- **OCR Completion Rate:** **100.0%** (RapidOCR successfully recovered text layers on the rasterized PDF)
- **Average Network AI Latency:** **7.05 seconds**
- **Total Token Usage:** **5,092 tokens** ($0 cost on OpenRouter free tier)
- **Adversarial Security:** Flagged 2 injection directives in `INV-EVAL-022.pdf` and emitted zero unauthorized decisions.
- **Detailed Artifacts:** [`evaluation/reports/live_smoke_test.json`](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.json) and [`evaluation/reports/live_smoke_test.md`](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.md).

---

## 🧪 Evaluation Lab — 31-Document Synthetic Offline Benchmark

The repository includes an automated Evaluation Lab benchmarking the end-to-end workflow across a dataset of **31 synthetic invoice documents** (30 PDFs, 1 high-resolution PNG) generated using fictional entities and synthetic `DEMO-ACCT-*` internal references:

```powershell
python evaluation/scripts/run_evaluation.py
```

### 31-Document Benchmark Results

> [!NOTE]
> **Methodological Disclosure — Deterministic Fixture-Based Regression vs Live Model Evaluation:**
> The 31-document offline benchmark evaluates structured JSON schema parsing, normalization, evidence grounding, and deterministic verification rules against ground-truth fixtures and synthetic PDFs across all 15 schema fields (`FIELD_KEYS`). It is a deterministic regression suite, NOT an empirical measurement of external LLM extraction accuracy. Note that the legacy 31-document synthetic dataset contains ground truth only for the 7 base fields; the 8 GST fields have no ground truth defined in this dataset and are correctly recorded as `NOT_EVALUATED` rather than artificially inflating accuracy metrics.

| Evaluation Pillar | Target Metric | Measured Value | Outcome |
|---|---|---|---|
| **Synthetic Dataset** | 30+ Documents | **31 Documents** (PDF & PNG) | **PASSED** |
| **OCR Text Extraction** | 100% on scanned/image docs | **100.0%** (2/2 documents) | **PASSED** |
| **Field Extraction Accuracy** | High precision across 7 evaluated fields | **100.0%** (217/217 fields) | **PASSED** |
| **GST Field Coverage** | 8 GST fields in schema | **NOT_EVALUATED** (No GT in 31-doc dataset) | **DISCLOSED** |
| **Adversarial Grounding** | Reject ungrounded / mismatched quotes | **100.0%** (5/5 adversarial cases) | **PASSED** |
| **Malicious Injection Detection** | Flag directive injection phrases | **100.0%** (4/4 attacks flagged) | **PASSED** |
| **Heuristic False Positive Rate** | Regex scanner boundary limitation | **100.0%** (1/1 benign lookalike sample flagged)* | **OBSERVED** |
| **Verification Decision Accuracy** | Exact deterministic policy execution | **100.0%** (31/31 correct decisions) | **PASSED** |
| **Clean Invoice Approvals** | 0% false holds on valid invoices | **100.0%** (8/8 clean approved) | **PASSED** |
| **Duplicate Submission Prevention** | Catch resubmissions & retain original | **100.0%** (3/3 duplicates caught) | **PASSED** |

*\*Note on Benign False-Positive Observation:* The heuristic regex scanner flagged 1 benign shipping instruction sample containing the phrase *"ignore previous delivery gate instructions"*. This observation reflects an intentional security trade-off based on a single adversarial test case rather than a broad statistical population estimate. It demonstrates why regex scanning is treated as an advisory defense-in-depth warning that prompts human review rather than an automated decision blocker.

- **Detailed Benchmark Report:** [`evaluation/reports/evaluation_report.md`](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/evaluation_report.md).

---

## 🔬 Automated Testing & Regression Suite

The project includes **123 automated backend tests** validating database constraints, verification rules, document security, OCR, AI extraction fallbacks, adversarial grounding, the India GST Integrity Engine, and 15-field evaluation framework integrity:

```powershell
pytest backend/tests -q
........................................................................ [ 58%]
...................................................                      [100%]
123 passed in 103.55s
```

- **`test_gst_integrity.py` (44 tests):** India GST Integrity Engine validation: 15-character GSTIN structure, official 38 State/UT catalogue, SGST vs UTGST distinction (Delhi/Puducherry/J&K vs Chandigarh/Ladakh/Dadra), Luhn mod 36 positive/negative checksum calculation, intra-state vs inter-state tax classification, component reconciliation (CGST, SGST, UTGST, IGST, Cess), internal ₹1.00 rounding tolerance boundaries, reverse state/UT name resolution (e.g. "Maharashtra" → "27"), taxable PO bypass protection, exempt/non-GST approvals, and full end-to-end API verification.
- **`test_database.py` (13 tests):** Schema initialization, integer-paise conversions, foreign key constraints, unique vendor/normalized invoice constraints, and append-only audit event logging.
- **`test_verification.py` (21 tests):** Clean matches, amount variances, GST mismatches, line-item mismatches, inactive/unknown vendors, duplicate submissions, and missing required fields.
- **`test_document_extraction.py` (19 tests):** Magic byte validation, upload limits, PyMuPDF extraction, RapidOCR fallback, prompt-injection scanner, evidence quote verification, and API key absence fallback.
- **`test_evaluation_framework.py` (24 tests):** Ground truth integrity, 15-field schema evaluation definitions, unannotated field exclusion from denominators, explicit expected null handling, adversarial grounding, OCR edge cases, deterministic verification consistency, decision immutability, safe API key absence fallback, and honest skipped metrics reporting.

### Frontend Production Build
```powershell
cd frontend; npm run build
▲ Next.js 16.4.6 (Turbopack)
✓ Compiled successfully in 5.0s
✓ Running TypeScript ... Finished in 14.0s
✓ Generating static pages (4/4) in 6.1s
```
*Result: **0 TypeScript errors, 0 compilation warnings**.*

---

## 🗄️ Database Schema & Synthetic Seed Data

The database initializes four relational tables in `backend/fintrust.db` with SQLite foreign keys enabled (`PRAGMA foreign_keys = ON`), featuring idempotent schema migrations for the GST Integrity Engine:

```sql
-- Vendors Master (with GSTIN support)
CREATE TABLE vendors (
    id INTEGER PRIMARY KEY,
    vendor_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    bank_account_ref TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    gstin TEXT,
    gstin_verification_status TEXT DEFAULT 'NOT_VERIFIED',
    created_at TEXT NOT NULL
);

-- Approved Purchase Orders (with GST baseline & components)
CREATE TABLE purchase_orders (
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
    gst_transaction_profile TEXT DEFAULT 'STANDARD_DOMESTIC',
    approved_cgst_paise INTEGER DEFAULT 0,
    approved_sgst_paise INTEGER DEFAULT 0,
    approved_utgst_paise INTEGER DEFAULT 0,
    approved_igst_paise INTEGER DEFAULT 0,
    approved_cess_paise INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Verified Invoices (with GST component breakdown)
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
    supplier_gstin TEXT,
    recipient_gstin TEXT,
    place_of_supply_state_code TEXT,
    cgst_paise INTEGER DEFAULT 0,
    sgst_paise INTEGER DEFAULT 0,
    utgst_paise INTEGER DEFAULT 0,
    igst_paise INTEGER DEFAULT 0,
    cess_paise INTEGER DEFAULT 0,
    gst_validation_status TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (vendor_id, normalized_invoice_number)
);

-- Application-Level Append-Only Audit Ledger
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
| `GET` | `/` | API welcome message | None | `{"message": "Welcome to the FinTrust AI API"}` |
| `GET` | `/health` / `/api/health` | Health and connectivity probe | None | JSON application & connectivity status |
| `GET` | `/api/dashboard` | Aggregated dashboard KPI metrics | None | JSON with vendor, PO, invoice, and pending counts |
| `GET` | `/api/vendors` | List registered vendor records | None | Array of `VendorRead` records |
| `GET` | `/api/purchase-orders` | List approved purchase orders | None | Array of `PurchaseOrderRead` records |
| `GET` | `/api/invoices` | List historical verified invoices | None | Array of `InvoiceRead` records |
| `GET` | `/api/audit-events` | List application audit events | None | Array of `AuditEventRead` records |
| `POST` | `/api/verify-invoice` | Deterministic verification engine | `InvoiceVerificationRequest` | `InvoiceVerificationResponse` (APPROVE / HOLD) |
| `POST` | `/api/documents/extract` | Document upload, OCR, and AI extraction | `UploadFile` (multipart) | `DocumentExtractionResponse` with quotes & confidence |

---

## ⚠️ Limitations, Scope & Honest Presentation Disclaimers

1. **Synthetic Demonstration Data:** All vendor entities, purchase orders, account references, and test documents are fictional fixtures generated for demonstration and evaluation. No genuine personal data, live corporate documents, or real banking records are used.
2. **Internal Account Consistency vs. Live Bank Ownership:** The system verifies consistency between the invoice's remittance reference and the vendor's pre-approved account reference on file in the internal database (`DEMO-ACCT-*`). It does **not** interface with live banking APIs (e.g., NPCI, RBI Account Aggregator, or bank verification networks) to verify external bank account ownership or beneficiary identities.
3. **Duplicate Submission Detection vs. Duplicate Payment Detection:** Duplicate detection is scoped to identifying repeat invoice submissions in the database based on `(vendor_id, normalized_invoice_number)`. FinTrust AI does not monitor external bank accounts, payment gateways, or ERP accounting disbursements, and therefore does not verify whether an actual duplicate financial payment was executed externally.
4. **No Payment Disbursement:** FinTrust AI operates strictly as a financial verification and discrepancy-detection layer. It does not initiate, schedule, or execute wire transfers, UPI transfers, or banking disbursements.
5. **Verification Decision Scope (APPROVE vs HOLD):** The backend emits `APPROVE` or `HOLD` recommendations based strictly on deterministic comparisons against stored purchase orders and vendor profiles. An `APPROVE` decision indicates that invoice claims match internal database baselines; it does not constitute payment authorization or fund release.
6. **No AI-Initiated Approval:** The architecture strictly enforces a human-controlled verification boundary. Document upload extracts draft fields into an interactive workspace; verification requires deliberate user review and submission. The AI extraction model has zero authority to issue decisions or update the database.
7. **Audit Trail Implementation:** The audit trail operates with application-level append-only guarantees: the application code exposes only `INSERT` queries, with no `UPDATE` or `DELETE` API endpoints or repository methods. It does not implement cryptographic hash chaining, digital signatures, or hardware tamper-proofing. Users with direct local filesystem access to the underlying `fintrust.db` file could modify or delete records.
8. **Heuristic Prompt Scanner Trade-off:** The regex-based prompt scanner is a defense-in-depth heuristic designed to flag common instruction-injection patterns. Benign text with overlapping terminology (such as delivery instructions containing *"ignore previous delivery gate instructions"*) will trigger advisory warnings, requiring human review to confirm benign intent.
9. **GST Verification Scope (Offline Validation Only):** Syntactic structure and Luhn mod 36 checksum validation confirms format adherence only. FinTrust AI does not scrape, bypass CAPTCHA, or integrate directly with the government GST Portal (gst.gov.in). Validation does not prove that a GSTIN is currently active, suspended, or cancelled by tax authorities. Automated tax classification applies standard domestic supply rules under Sections 7, 8, 10, and 12 of the IGST Act, 2017; complex transactions (SEZ supplies, export/import transactions, and reverse charge mechanisms) require manual tax specialist review.

---

## 📚 In-Depth Project Documentation

- **[India GST Integrity Engine Specification](file:///c:/Users/hp/Downloads/FinTrustAI/docs/GST_INTEGRITY_ENGINE.md):** `docs/GST_INTEGRITY_ENGINE.md`
- **[5-Minute Judge Presentation Script](file:///c:/Users/hp/Downloads/FinTrustAI/docs/FINTRUST_AI_FIVE_MINUTE_DEMO.md):** `docs/FINTRUST_AI_FIVE_MINUTE_DEMO.md`
- **[Comprehensive Project Status & Architecture Report](file:///c:/Users/hp/Downloads/FinTrustAI/docs/FINTRUST_AI_COMPLETE_PROJECT_STATUS_REPORT.md):** `docs/FINTRUST_AI_COMPLETE_PROJECT_STATUS_REPORT.md`
- **[Live Model Validation Report (JSON)](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.json):** `evaluation/reports/live_smoke_test.json`
- **[Live Model Validation Report (Markdown)](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/live_smoke_test.md):** `evaluation/reports/live_smoke_test.md`
- **[31-Document Evaluation Benchmark Report](file:///c:/Users/hp/Downloads/FinTrustAI/evaluation/reports/evaluation_report.md):** `evaluation/reports/evaluation_report.md`

---

## 👥 Authors & Acknowledgments

Developed by **Garlapati** for **Arthaton 2026** (AI for Finance Hackathon).  
GitHub Repository: **[https://github.com/garlapati3105-cmd/FinTrust-Ai-](https://github.com/garlapati3105-cmd/FinTrust-Ai-)**
