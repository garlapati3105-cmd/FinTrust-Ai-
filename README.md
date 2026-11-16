# FinTrust AI — Financial Document Verification & Extraction Platform

FinTrust AI is a financial-document verification workspace designed for Indian MSMEs. It features a deterministic, database-backed verification engine coupled with secure document upload, native/OCR text extraction, and AI-assisted financial field parsing with mandatory human-in-the-loop review.

---

## Architecture Overview

```
[ Upload Document (PDF/PNG/JPG) ]
               │
               ▼
[ Magic Byte & Size Validation ] ──► (Reject malformed / oversized / invalid files)
               │
               ▼
[ Text Extraction Engine ]
   ├── PyMuPDF (Native selectable text)
   └── RapidOCR Fallback (Scanned PDFs / Images)
               │
               ▼
[ Prompt-Injection Heuristic Scan ] ──► (Flag suspicious injection phrases)
               │
               ▼
[ AI Field Extractor (OpenRouter) ] ──► (Structured JSON extraction in isolated prompt)
               │
               ▼
[ Server-Side Evidence Verification ] ──► (Verify quotes against extracted document text)
               │
               ▼
[ Frontend Review Workspace ] ──► (User inspects & edits values; NEVER auto-approved)
               │
               ▼
[ POST /api/verify-invoice ] ──► (Authoritative SQLite Database Verification Engine)
               │
               ▼
[ Decision (APPROVE / HOLD) + Audit Log ]
```

---

## Core Components

### 1. Document Extraction & OCR Pipeline
- **Formats Supported**: PDF, PNG, JPG, JPEG.
- **Constraints**: Configurable max upload size (10 MB default) and max page count (10 pages default).
- **Native PDF Extraction**: Utilizes **PyMuPDF (`fitz`)** for rapid, accurate extraction of selectable text while preserving page numbering and boundaries.
- **OCR Engine**: Utilizes **RapidOCR (`rapidocr-onnxruntime`)** as an embedded fallback when PDF pages contain no native text (scanned documents) and for standalone image uploads.
- **Graceful Degradation**: If an external AI API key is not configured, the endpoint returns the raw extracted document text with `extraction_status: "unavailable"`, enabling complete manual data entry without failure.

### 2. AI-Assisted Structured Extraction
- **Model Integration**: OpenRouter-compatible endpoint configured via environment variables (`OPENROUTER_API_KEY`, `FINTRUST_EXTRACTION_MODEL`).
- **Structured Fields**:
  - `invoice_number`
  - `vendor_name`
  - `po_number`
  - `invoice_total`
  - `gst_amount`
  - `line_items`
  - `invoice_bank_account_ref`
- **Field Metadata**: Each field includes `value`, `page_number`, `evidence_quote`, and a `confidence` rating (0.0 to 1.0).
- **Server-Side Quote Verification**: The backend strictly validates that the AI's reported `evidence_quote` is a genuine normalized substring of the actual extracted page text, setting `evidence_verified: true/false`.

### 3. Security Controls & Defense-in-Depth
- **File Signature (Magic Bytes) Verification**: Files are validated using binary headers (`%PDF`, `\x89PNG`, `\xFF\xD8\xFF`), ignoring untrusted client-supplied MIME types and file extensions.
- **Safe Temporary Files**: All file processing uses randomly named temporary files in system temporary directories with guaranteed cleanup in `finally` blocks.
- **Path Traversal Protection**: User-supplied filenames are never used to construct server paths. No internal filesystem paths are exposed in API responses.
- **Prompt Injection Defense**:
  - Document text is isolated inside `<document_content>` XML-style delimiters with explicit system instructions prohibiting execution of instructions contained within the document.
  - Heuristic pattern scanner flags adversarial phrases (e.g., "ignore previous instructions", "override decision", "system prompt", "approve this invoice").
- **Human-in-the-Loop Policy**: AI extraction **never** directly approves an invoice. Extracted values populate editable input controls in the frontend for human validation before being submitted to the verification engine.

### 4. Database-Backed Verification Engine
- **Storage**: SQLite (`backend/fintrust.db`) with foreign keys enabled.
- **Precision**: Monetary calculations use Python `Decimal` and database persistence in integer paise. Values with more than two decimal places are rejected.
- **Trusted Record Comparison**: The invoice endpoint looks up approved totals, GST amounts, item counts, active vendor status, and account references directly from the database using `po_number`. The invoice is never trusted to supply its own baseline.
- **Duplicate Detection**: Invoices are normalized (`TRIM` and `UPPER`) and checked against `(vendor_id, normalized_invoice_number)`. Duplicate submissions result in `HOLD` and record an audit event without overwriting existing data.
- **Audit Trail**: Every verification decision records an append-only audit event.

---

## Synthetic Seed Data

The database seeds three fictional vendors and approved purchase orders:

| Vendor Code | Fictional Vendor | Synthetic Account Ref | Purchase Order | Approved Total | Approved GST | Approved Items |
|---|---|---|---|---:|---:|---:|
| VND-1001 | Aster Office Supplies | DEMO-ACCT-1001 | PO-1001 | ₹85,000.00 | ₹12,966.10 | 5 |
| VND-1002 | BluePeak Technologies | DEMO-ACCT-1002 | PO-1002 | ₹1,20,000.00 | ₹18,305.08 | 8 |
| VND-1003 | GreenField Logistics | DEMO-ACCT-1003 | PO-1003 | ₹46,500.00 | ₹7,093.22 | 4 |

*Note: Account references (`DEMO-ACCT-*`) are synthetic internal identifiers. Matching an account reference checks internal consistency only and does not verify bank account ownership.*

---

## Local Setup & Configuration

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### Backend Configuration
1. Navigate to `backend`:
   ```powershell
   cd backend
   ```
2. Create and activate a virtual environment:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   Copy `.env.example` to `.env` and configure your OpenRouter credentials (optional for testing):
   ```ini
   OPENROUTER_API_KEY=your_api_key_here
   FINTRUST_EXTRACTION_MODEL=openrouter/free
   OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
   MAX_UPLOAD_SIZE_MB=10
   MAX_PDF_PAGES=10
   ```
5. Run the FastAPI development server:
   ```powershell
   python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

### Frontend Configuration
1. Navigate to `frontend`:
   ```powershell
   cd frontend
   ```
2. Install dependencies:
   ```powershell
   npm install
   ```
3. Run the Next.js development server:
   ```powershell
   npm run dev
   ```
   Or build for production:
   ```powershell
   npm run build
   ```

---

## API Documentation

### 1. Document Extraction
- **Endpoint**: `POST /api/documents/extract`
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (Binary file: PDF, PNG, JPG, or JPEG)
- **Response**:
  ```json
  {
    "filename": "invoice_demo.pdf",
    "file_type": "pdf",
    "page_count": 1,
    "pages": [
      {
        "page_number": 1,
        "text": "INVOICE #INV-2026-001 ...",
        "ocr_applied": false
      }
    ],
    "raw_text": "INVOICE #INV-2026-001 ...",
    "ocr_applied": false,
    "ocr_engine": "rapidocr",
    "ai_extraction_available": true,
    "ai_model": "anthropic/claude-3.5-sonnet",
    "fields": {
      "invoice_number": {
        "field": "invoice_number",
        "value": "INV-2026-001",
        "page_number": 1,
        "evidence_quote": "INVOICE #INV-2026-001",
        "confidence": 0.98,
        "evidence_verified": true,
        "warning": null
      },
      "vendor_name": {
        "field": "vendor_name",
        "value": "Aster Office Supplies",
        "page_number": 1,
        "evidence_quote": "Aster Office Supplies",
        "confidence": 0.95,
        "evidence_verified": true,
        "warning": null
      },
      "po_number": {
        "field": "po_number",
        "value": "PO-1001",
        "page_number": 1,
        "evidence_quote": "PO Number: PO-1001",
        "confidence": 0.99,
        "evidence_verified": true,
        "warning": null
      },
      "invoice_total": {
        "field": "invoice_total",
        "value": "85000.00",
        "page_number": 1,
        "evidence_quote": "Total: 85,000.00",
        "confidence": 0.96,
        "evidence_verified": true,
        "warning": null
      },
      "gst_amount": {
        "field": "gst_amount",
        "value": "12966.10",
        "page_number": 1,
        "evidence_quote": "GST 18%: 12,966.10",
        "confidence": 0.94,
        "evidence_verified": true,
        "warning": null
      },
      "line_items": {
        "field": "line_items",
        "value": 5,
        "page_number": 1,
        "evidence_quote": "Total Items: 5",
        "confidence": 0.9,
        "evidence_verified": true,
        "warning": null
      },
      "invoice_bank_account_ref": {
        "field": "invoice_bank_account_ref",
        "value": "DEMO-ACCT-1001",
        "page_number": 1,
        "evidence_quote": "Account Ref: DEMO-ACCT-1001",
        "confidence": 0.92,
        "evidence_verified": true,
        "warning": null
      }
    },
    "suspicious_content_detected": false,
    "suspicious_warnings": [],
    "processing_warnings": []
  }
  ```

### 2. Invoice Verification
- **Endpoint**: `POST /api/verify-invoice`
- **Content-Type**: `application/json`
- **Request**:
  ```json
  {
    "invoice_number": "INV-2026-001",
    "vendor_name": "Aster Office Supplies",
    "po_number": "PO-1001",
    "invoice_total": "85000.00",
    "gst_amount": "12966.10",
    "line_items": 5,
    "invoice_bank_account_ref": "DEMO-ACCT-1001"
  }
  ```
- **Response**:
  ```json
  {
    "decision": "APPROVE",
    "risk_level": "low",
    "findings": [],
    "invoice_id": 1,
    "audit_event_id": 1,
    "duplicate_of_invoice_id": null,
    "duplicate": false,
    "po_number": "PO-1001",
    "vendor_id": 1,
    "vendor_code": "VND-1001",
    "vendor_name": "Aster Office Supplies",
    "invoice_number": "INV-2026-001",
    "invoice_total": 85000.0,
    "gst_amount": 12966.1,
    "line_items": 5,
    "approved_total": 85000.0,
    "approved_gst": 12966.1,
    "approved_line_items": 5,
    "variance": {
      "total_difference": 0.0,
      "gst_difference": 0.0,
      "line_items_difference": 0
    }
  }
  ```

---

## Automated Testing & Evaluation Lab

The backend test suite contains **68 automated tests** covering database operations, verification rules, security boundaries, OCR parsing, AI extraction, adversarial evidence grounding, and evaluation lab benchmarks:

```powershell
python -m pytest backend/tests -p no:langsmith -o pythonpath=backend -q
```

### Test Coverage Highlights
- **`backend/tests/test_database.py` (13 tests)**: Schema creation, integer-paise conversions, foreign key constraints, duplicate detection, and append-only audit logs.
- **`backend/tests/test_verification.py` (21 tests)**: Exact matches, amount discrepancies, GST mismatches, inactive/unknown vendors, bank reference mismatches, missing required fields, and boundary cases.
- **`backend/tests/test_document_extraction.py` (19 tests)**: Native/OCR text extraction, magic byte validation, upload limits, prompt-injection defense, and evidence quote verification.
- **`backend/tests/test_evaluation_framework.py` (15 tests)**:
  - Evaluation dataset & ground truth schema integrity (31 documents).
  - Adversarial evidence grounding (wrong value in quote, wrong field quote, wrong page quote, fabricated quote, missing field).
  - Prompt-injection heuristic detection and benign lookalike trade-offs.
  - End-to-end OCR processing of real PNG and scanned PDF documents.
  - Deterministic authoritative verification on clean invoices, discrepancies, and duplicates.
  - Invariant validation: document extraction never persists or auto-approves invoices.

---

## Evaluation Lab: Real-World Reliability Testing

The project includes a standalone, reproducible Evaluation Lab for benchmarking OCR text extraction, field-level extraction accuracy, evidence grounding, prompt-injection resilience, and deterministic verification.

### Running the Evaluation Lab
1. **Regenerate Synthetic Dataset**:
   ```powershell
   python evaluation/scripts/generate_dataset.py
   ```
   Generates 31 synthetic documents (PDFs & PNG) in `evaluation/dataset/documents/` and ground truth JSON files in `evaluation/dataset/ground_truth/`.

2. **Execute Full Evaluation Suite**:
   ```powershell
   $env:PYTHONPATH='backend'; python evaluation/scripts/run_evaluation.py
   ```
   Generates a machine-readable report (`evaluation/reports/evaluation_report.json`) and human-readable summary (`evaluation/reports/evaluation_report.md`).

### Evaluation Benchmark Results (31 Synthetic Invoices)

| Metric | Target | Result | Status |
|---|---|---|---|
| **Total Evaluation Documents** | 30+ Documents | **31 Documents** (30 PDF, 1 PNG) | **PASSED** |
| **OCR Text Extraction Success** | 100% on scanned & image docs | **100.0%** (2/2 documents) | **PASSED** |
| **Field Extraction Accuracy** | High accuracy across 7 fields | **100.0%** (217/217 fields) | **PASSED** |
| **Adversarial Evidence Grounding** | Reject ungrounded / mismatched quotes | **100.0%** (5/5 adversarial cases) | **PASSED** |
| **Malicious Injection Detection** | Flag directive injection phrases | **100.0%** (4/4 attacks flagged) | **PASSED** |
| **Heuristic False Positive Rate** | Document regex boundary limitations | **100.0%** on benign lookalike | **OBSERVED** |
| **Authoritative Decision Accuracy** | Exact deterministic policy execution | **100.0%** (31/31 correct) | **PASSED** |
| **False HOLD Rate on Clean Records** | 0% false holds on valid invoices | **0.0%** (8/8 clean approved) | **PASSED** |
| **Duplicate Submission Catch** | 100% duplicate catch & hold | **100.0%** (3/3 duplicates caught) | **PASSED** |

---

## Live AI Provider Validation (OpenRouter)

FinTrust AI includes a dedicated live model validation runner (`evaluation/scripts/run_live_smoke_test.py`) that executes real external model requests over OpenRouter.

### Running the Live Smoke Test
```powershell
$env:OPENROUTER_API_KEY = "your-openrouter-key"
$env:FINTRUST_EXTRACTION_MODEL = "openrouter/free"
python evaluation/scripts/run_live_smoke_test.py
```

### Live Validation Results (November 16, 2026)
- **External Requests Completed:** 3 / 3 (100%) across Document A (`INV-EVAL-001.pdf`), Document B (`INV-EVAL-031.pdf`), and Document C (`INV-EVAL-022.pdf`).
- **Models Routed via `openrouter/free`:** `baidu/ernie-5.5-flash-preview:free`, `nvidia/nemotron-3.5-super-vl:free`, `recursive/flint-v1.0:free`.
- **Field Extraction Accuracy:** **100.0%** (21 / 21 fields matched ground truth exactly).
- **Bidirectional Evidence Grounding:** **100.0%** (21 / 21 evidence quotes verified in document text and page bounds).
- **Missing Field Rate:** **0.0%**.
- **OCR Fallback Completion:** **100.0%** (RapidOCR recovered text on rasterized PDF).
- **Average Network AI Latency:** **7.05 seconds** (Complete average document latency: 9.29s).
- **Token Usage:** 5,092 tokens total ($0 cost on free tier).
- **Adversarial Injection Defense:** Flagged suspicious directives in `INV-EVAL-022.pdf` and emitted zero unauthorized decisions.
- **Detailed Reports:** `evaluation/reports/live_smoke_test.json` and `evaluation/reports/live_smoke_test.md`.

---

## Limitations & Scope

1. **Synthetic Data**: All vendor records, purchase orders, account references, and test documents are synthetic fixtures for demonstration purposes.
2. **Account Reference Verification**: The system verifies consistency against internal database records. It does not interface with live banking APIs or prove external account ownership.
3. **No Automated Approvals**: The system is strictly designed with a human-in-the-loop requirement. Document upload only extracts and drafts values into an interactive workspace; verification requires deliberate user submission.
4. **Heuristic Prompt-Injection Limitations**: Regex pattern scanning is a defense-in-depth heuristic. It can produce false positives on benign business notes and cannot alone guarantee immunity against novel phrasing; security relies on isolated prompt framing, strict evidence binding, and deterministic backend verification rules.
5. **No Financial Transactions**: The system verifies invoices and logs discrepancies; it does not initiate or execute payment orders.
