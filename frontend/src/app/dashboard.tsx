"use client";

import { useCallback, useEffect, useState } from "react";

type IconName =
  | "activity"
  | "arrow-right"
  | "arrow-up-right"
  | "audit"
  | "building"
  | "file"
  | "grid"
  | "loader"
  | "risk"
  | "settings"
  | "shield"
  | "verified";

type ConnectionState = "idle" | "loading" | "connected" | "disconnected";
type Section =
  | "Overview"
  | "Invoice Verification"
  | "Vendor Records"
  | "Risk Monitoring"
  | "Audit Trail"
  | "Settings";

type SummaryItem = {
  label: string;
  value: string;
  note: string;
  tone: "amber" | "green" | "red" | "slate";
};

type CaseItem = {
  id: string;
  vendor: string;
  status: string;
  risk: string;
};

type AuditItem = {
  action: string;
  time: string;
  decision?: string | null;
  id?: number | null;
};

type DashboardData = {
  summary: SummaryItem[];
  cases: CaseItem[];
  audit_entries: AuditItem[];
};

type VerificationResult = {
  invoice_number: string;
  vendor_name: string;
  vendor_id?: number | null;
  vendor_code?: string | null;
  po_number: string;
  invoice_total: number;
  gst_amount: number;
  approved_total: number | null;
  approved_gst: number | null;
  approved_line_items: number | null;
  line_items: number;
  decision: "APPROVE" | "HOLD" | "BLOCK";
  invoice_id: number | null;
  audit_event_id: number | null;
  duplicate_of_invoice_id: number | null;
  duplicate: boolean;
  status: string;
  risk_level: "low" | "medium" | "high";
  variance: {
    amount: number | null;
    gst: number | null;
    line_items: number | null;
  };
  findings: Array<{ title: string; detail: string; level: string }>;
};

type ExtractedField = {
  field: string;
  value: string | number | null;
  page_number: number | null;
  evidence_quote: string | null;
  confidence: number;
  evidence_verified: boolean;
  warning: string | null;
};

type DocumentPage = {
  page_number: number;
  text: string;
  ocr_applied: boolean;
};

type DocumentExtractionResult = {
  filename: string;
  file_type: string;
  page_count: number;
  pages: DocumentPage[];
  raw_text: string;
  ocr_applied: boolean;
  ocr_engine: string | null;
  ai_extraction_available: boolean;
  ai_model: string | null;
  fields: Record<string, ExtractedField>;
  suspicious_content_detected: boolean;
  suspicious_warnings: string[];
  processing_warnings: string[];
};

const navigation: { label: Section; icon: IconName }[] = [
  { label: "Overview", icon: "grid" },
  { label: "Invoice Verification", icon: "file" },
  { label: "Vendor Records", icon: "building" },
  { label: "Risk Monitoring", icon: "risk" },
  { label: "Audit Trail", icon: "audit" },
];

const defaultDashboard: DashboardData = {
  summary: [
    { label: "Registered vendors", value: "—", note: "Loading...", tone: "slate" },
    { label: "Approved purchase orders", value: "—", note: "Loading...", tone: "slate" },
    { label: "Invoices processed", value: "—", note: "Loading...", tone: "slate" },
    { label: "Pending reviews", value: "—", note: "Loading...", tone: "slate" },
  ],
  cases: [],
  audit_entries: [],
};

function Icon({ name, className = "icon" }: { name: IconName; className?: string }) {
  const paths: Record<IconName, React.ReactNode> = {
    activity: (
      <>
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </>
    ),
    "arrow-right": (
      <>
        <path d="M5 12h14" />
        <path d="m12 5 7 7-7 7" />
      </>
    ),
    "arrow-up-right": (
      <>
        <path d="M7 17 17 7" />
        <path d="M7 7h10v10" />
      </>
    ),
    audit: (
      <>
        <path d="M8 6h13" />
        <path d="M8 12h13" />
        <path d="M8 18h13" />
        <path d="M3 6h.01" />
        <path d="M3 12h.01" />
        <path d="M3 18h.01" />
      </>
    ),
    building: (
      <>
        <path d="M3 21h18" />
        <path d="M5 21V7l8-4v18" />
        <path d="M19 21V11l-6-4" />
        <path d="M9 9v.01" />
        <path d="M9 12v.01" />
        <path d="M9 15v.01" />
        <path d="M9 18v.01" />
      </>
    ),
    file: (
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <path d="M14 2v6h6" />
        <path d="M8 13h8" />
        <path d="M8 17h8" />
      </>
    ),
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
      </>
    ),
    loader: (
      <>
        <path d="M12 2v4" />
        <path d="M12 18v4" />
        <path d="m4.93 4.93 2.83 2.83" />
        <path d="m16.24 16.24 2.83 2.83" />
        <path d="M2 12h4" />
        <path d="M18 12h4" />
        <path d="m4.93 19.07 2.83-2.83" />
        <path d="m16.24 7.76 2.83-2.83" />
      </>
    ),
    risk: (
      <>
        <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11" />
        <path d="M12 8v4" />
        <path d="M12 16h.01" />
      </>
    ),
    settings: (
      <>
        <path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.6 2.77-.08-.02a1.7 1.7 0 0 0-1.78.48l-.06.07h-3.2l-.03-.09a1.7 1.7 0 0 0-1.25-1.2l-.1-.02-1.6-2.77.07-.08a1.7 1.7 0 0 0 .14-1.82l-.04-.09 1.6-2.77.1.01a1.7 1.7 0 0 0 1.62-.91l.05-.09h3.2l.05.09a1.7 1.7 0 0 0 1.62.91l.1-.01 1.6 2.77z" />
      </>
    ),
    shield: (
      <>
        <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
    verified: (
      <>
        <path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11" />
        <path d="m9 12 2 2 4-4" />
      </>
    ),
  };

  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
    >
      {paths[name]}
    </svg>
  );
}

function BrandMark({ className = "brand-icon" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="ft-brand-left" x1="4" y1="3" x2="16" y2="29" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#2d856b" />
          <stop offset="100%" stopColor="#144234" />
        </linearGradient>
        <linearGradient id="ft-brand-right" x1="16" y1="3" x2="28" y2="29" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#3ea988" />
          <stop offset="100%" stopColor="#1f5d4a" />
        </linearGradient>
      </defs>
      {/* Left Structural Facet (PO Baseline) */}
      <path
        d="M16 2.5L5 7.8C4.4 8.1 4 8.8 4 9.5V17.5C4 23.5 9 28.2 15.5 29.8C15.8 29.9 16.2 29.9 16.5 29.8V2.5H16Z"
        fill="url(#ft-brand-left)"
      />
      {/* Right Dynamic Facet (Invoice Claim) */}
      <path
        d="M16 2.5L27 7.8C27.6 8.1 28 8.8 28 9.5V17.5C28 23.5 23 28.2 16.5 29.8V2.5H16Z"
        fill="url(#ft-brand-right)"
      />
      {/* Central Interlocking Diamond Lens (Algorithmic Verification Core) */}
      <path
        d="M16 10L20.5 15.5L16 21L11.5 15.5L16 10Z"
        fill="#F5EFE9"
      />
      <circle cx="16" cy="15.5" r="2" fill="#144234" />
      {/* Top Horizon Bar */}
      <path
        d="M10 8.5H22V10.5H10V8.5Z"
        fill="#F5EFE9"
        fillOpacity="0.9"
      />
    </svg>
  );
}

function Brand() {
  return (
    <div className="brand">
      <span className="brand-mark">
        <BrandMark className="brand-icon" />
      </span>
      <span className="brand-copy">
        <span className="brand-name">FinTrust</span>
        <span className="brand-ai">AI</span>
      </span>
    </div>
  );
}

function ConnectionBadge({ state }: { state: ConnectionState }) {
  const label: Record<ConnectionState, string> = {
    idle: "Not checked",
    loading: "Checking",
    connected: "Connected",
    disconnected: "Disconnected",
  };

  return (
    <div className={`connection-badge connection-${state}`} aria-live="polite">
      <span className="connection-dot" />
      <span>Backend</span>
      <span className="connection-divider" />
      <span>{label[state]}</span>
    </div>
  );
}

function OverviewSummary({ summary }: { summary: SummaryItem[] }) {
  return (
    <section className="summary-grid" aria-label="Verification summary">
      {summary.map((item) => (
        <article className="summary-card" key={item.label}>
          <div className="summary-header">
            <span>{item.label}</span>
            <span className={`mini-pill ${item.tone}`}>{item.note}</span>
          </div>
          <strong>{item.value}</strong>
        </article>
      ))}
    </section>
  );
}

function RecentVerificationCases({
  cases,
  onOpenVerification,
  onInspectInvoice,
}: {
  cases: CaseItem[];
  onOpenVerification: () => void;
  onInspectInvoice?: (invId: string, vendorName?: string) => void;
}) {
  return (
    <section className="content-panel">
      <div className="panel-header">
        <h3>Recent verification cases</h3>
        <span className="soft-tag neutral">
          {cases.length > 0 ? "Stored verification records" : "No active cases"}
        </span>
      </div>
      {cases.length === 0 ? (
        <div style={{ padding: "32px 16px", textAlign: "center" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "50%",
              background: "var(--surface-soft)",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 12px",
              color: "var(--muted)",
            }}
          >
            <Icon name="file" />
          </div>
          <strong style={{ display: "block", fontSize: "14px", marginBottom: "6px" }}>
            No invoices verified yet
          </strong>
          <p style={{ fontSize: "12px", color: "var(--muted)", maxWidth: "320px", margin: "0 auto 16px" }}>
            Submitted invoices and their risk assessments will appear here once verified against trusted records.
          </p>
          <button className="primary-button" onClick={onOpenVerification} type="button" style={{ margin: "0 auto" }}>
            <Icon name="file" />
            <span>Verify an Invoice</span>
          </button>
        </div>
      ) : (
        <div className="stack-list">
          {cases.map((item) => (
            <div
              className="case-row clickable-row"
              key={item.id}
              onClick={() => onInspectInvoice?.(item.id, item.vendor)}
              title="Click to inspect this invoice in verification workspace"
            >
              <div>
                <strong>{item.id}</strong>
                <span>{item.vendor}</span>
              </div>
              <span className={`status-chip ${item.status.toLowerCase().replace(/\s+/g, "-")}`}>
                {item.status}
              </span>
              <span className={`risk-chip ${item.risk.toLowerCase()}`}>{item.risk}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function RecentAuditActivity({
  entries,
  onOpenVerification,
  onSelectAuditEntry,
}: {
  entries: AuditItem[];
  onOpenVerification: () => void;
  onSelectAuditEntry?: (entry: AuditItem) => void;
}) {
  return (
    <section className="content-panel">
      <div className="panel-header">
        <h3>Recent audit activity</h3>
        <span className="soft-tag neutral">Immutable ledger</span>
      </div>
      {entries.length === 0 ? (
        <div style={{ padding: "32px 16px", textAlign: "center" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "50%",
              background: "var(--surface-soft)",
              display: "grid",
              placeItems: "center",
              margin: "0 auto 12px",
              color: "var(--muted)",
            }}
          >
            <Icon name="audit" />
          </div>
          <strong style={{ display: "block", fontSize: "14px", marginBottom: "6px" }}>
            No audit events recorded yet
          </strong>
          <p style={{ fontSize: "12px", color: "var(--muted)", maxWidth: "320px", margin: "0 auto 16px" }}>
            Every invoice decision, duplicate detection, and security warning is appended to the immutable SQLite audit ledger.
          </p>
          <button className="secondary-button" onClick={onOpenVerification} type="button" style={{ margin: "0 auto" }}>
            <Icon name="shield" />
            <span>Verify First Invoice</span>
          </button>
        </div>
      ) : (
        <div className="stack-list compact">
          {entries.map((entry) => (
            <div
              className="audit-row clickable-row"
              key={`${entry.action}-${entry.time}`}
              onClick={() => onSelectAuditEntry?.(entry)}
              title="Click to view full immutable audit event"
            >
              <span className="audit-icon-inline">
                <Icon name="audit" />
              </span>
              <div>
                <strong>{entry.action}</strong>
                <span>{entry.time}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function OverviewPage({
  onOpenVerification,
  onOpenVendors,
  onOpenRisk,
  onInspectInvoice,
  onSelectAuditEntry,
  summary,
  cases,
  auditEntries,
}: {
  onOpenVerification: () => void;
  onOpenVendors: () => void;
  onOpenRisk: () => void;
  onInspectInvoice?: (invId: string, vendorName?: string) => void;
  onSelectAuditEntry?: (entry: AuditItem) => void;
  summary: SummaryItem[];
  cases: CaseItem[];
  auditEntries: AuditItem[];
}) {
  const attentionCases = cases.filter(
    (c) =>
      c.status.toLowerCase().includes("review") ||
      c.status.toLowerCase().includes("hold") ||
      c.status.toLowerCase().includes("block") ||
      c.risk.toLowerCase() === "high" ||
      c.risk.toLowerCase() === "medium",
  );

  const registeredVendorsCount = summary.find((s) => s.label.toLowerCase().includes("vendor"))?.value ?? "03";
  const approvedPosCount = summary.find((s) => s.label.toLowerCase().includes("purchase"))?.value ?? "03";

  return (
    <>
      <section className="workspace-summary">
        <div className="summary-copy">
          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            <span className="eyebrow dark">
              <span />Verification overview
            </span>
          </div>
          <h2>Evidence and review pipeline</h2>
        </div>
        <button className="new-verification-button" onClick={onOpenVerification} type="button">
          New Verification
          <Icon name="arrow-right" />
        </button>
      </section>

      {/* 4-Step Process Stepper (Ramp/Zoho Books inspired) */}
      <div className="workflow-stepper">
        <div className="step-card">
          <span className="step-num">1</span>
          <div className="step-body">
            <strong>Upload Document</strong>
            <span>PDF, PNG, JPG with signature verification</span>
          </div>
        </div>
        <div className="step-card">
          <span className="step-num">2</span>
          <div className="step-body">
            <strong>Extract & OCR</strong>
            <span>Native text & OCR with evidence quote binding</span>
          </div>
        </div>
        <div className="step-card">
          <span className="step-num">3</span>
          <div className="step-body">
            <strong>Compare Baseline</strong>
            <span>Reconciliation against SQLite PO & vendor records</span>
          </div>
        </div>
        <div className="step-card">
          <span className="step-num">4</span>
          <div className="step-body">
            <strong>Human Review</strong>
            <span>Deterministic decision & immutable audit trail</span>
          </div>
        </div>
      </div>

      <OverviewSummary summary={summary} />

      {/* Action-focused Needs Your Attention Queue (Ramp/Stampli style) */}
      <section className="attention-panel">
        <div className="attention-header">
          <div className="attention-title">
            <Icon name="risk" />
            <span>Needs Your Attention • High Priority Queues</span>
          </div>
          <span className={`soft-tag ${attentionCases.length > 0 ? "warning" : "neutral"}`}>
            {attentionCases.length > 0 ? `${attentionCases.length} items flagged for review` : "All clear"}
          </span>
        </div>
        {attentionCases.length === 0 ? (
          <div style={{ padding: "10px 4px", fontSize: "13px", color: "var(--muted)" }}>
            ✓ All stored invoices are reconciled. No pending fraud holds or unapproved variances.
          </div>
        ) : (
          <div className="attention-list">
            {attentionCases.map((item) => (
              <div className="attention-row" key={item.id}>
                <div className="attention-info">
                  <span className={`risk-chip ${item.risk.toLowerCase()}`}>{item.risk} Risk</span>
                  <div>
                    <strong style={{ fontSize: "13px" }}>{item.id}</strong>
                    <span style={{ fontSize: "12px", color: "var(--muted)", marginLeft: "8px" }}>
                      Vendor: {item.vendor} • Status: {item.status}
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  className="attention-action-btn"
                  onClick={() => onInspectInvoice?.(item.id, item.vendor)}
                  title="Open in verification workspace"
                >
                  <span>Investigate</span>
                  <Icon name="arrow-right" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="dashboard-grid">
        <RecentVerificationCases
          cases={cases}
          onOpenVerification={onOpenVerification}
          onInspectInvoice={onInspectInvoice}
        />
        <RecentAuditActivity
          entries={auditEntries}
          onOpenVerification={onOpenVerification}
          onSelectAuditEntry={onSelectAuditEntry}
        />
      </section>

      <section className="empty-state-grid">
        <article className="empty-card" style={{ cursor: "pointer" }} onClick={onOpenVendors}>
          <div className="empty-card-header">
            <span className="empty-icon">
              <Icon name="building" />
            </span>
            <span className="soft-tag">Active Database</span>
          </div>
          <h3>Vendor Master & PO Baselines</h3>
          <p>{registeredVendorsCount} registered suppliers and {approvedPosCount} approved purchase orders available as authoritative ground truth for deterministic verification.</p>
          <div style={{ marginTop: "12px", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "var(--green)" }}>
            <span>View Vendor Records</span>
            <Icon name="arrow-right" />
          </div>
        </article>

        <article className="empty-card" style={{ cursor: "pointer" }} onClick={onOpenRisk}>
          <div className="empty-card-header">
            <span className="empty-icon">
              <Icon name="risk" />
            </span>
            <span className="soft-tag">Real-Time Ledger</span>
          </div>
          <h3>Risk Monitoring & Discrepancies</h3>
          <p>Audit ledger and discrepancy tracking across all verified invoices with integer paise calculation precision.</p>
          <div style={{ marginTop: "12px", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: 700, color: "var(--green)" }}>
            <span>View Risk Monitoring</span>
            <Icon name="arrow-right" />
          </div>
        </article>
      </section>
    </>
  );
}

type VendorRead = {
  id: number;
  vendor_code: string;
  name: string;
  bank_account_ref: string;
  is_active: boolean;
  created_at: string;
};

type PurchaseOrderRead = {
  id: number;
  po_number: string;
  vendor_id: number;
  vendor_code: string;
  vendor_name: string;
  approved_total_paise: number;
  approved_gst_paise: number;
  approved_line_items: number;
  status: string;
  issue_date: string;
  created_at: string;
};

type AuditEventRead = {
  id: number;
  entity_type: string;
  entity_id: number | null;
  event_type: string;
  decision: string | null;
  reason: string | null;
  created_at: string;
};

type InvoiceRead = {
  id: number;
  invoice_number: string;
  normalized_invoice_number: string;
  vendor_id: number;
  po_id: number | null;
  invoice_total_paise: number;
  gst_amount_paise: number;
  line_items: number;
  invoice_bank_account_ref: string | null;
  decision: string | null;
  risk_level: string | null;
  created_at: string;
};

function formatRupees(paise: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(paise / 100);
}

function formatISTDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return (
      new Intl.DateTimeFormat("en-IN", {
        timeZone: "Asia/Kolkata",
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      }).format(d) + " IST"
    );
  } catch {
    return isoString;
  }
}

function VendorDetailsModal({
  vendor,
  pos,
  invoices,
  onClose,
  onVerifyVendor,
}: {
  vendor: VendorRead;
  pos: PurchaseOrderRead[];
  invoices: InvoiceRead[];
  onClose: () => void;
  onVerifyVendor: (vendor: VendorRead, po?: PurchaseOrderRead) => void;
}) {
  const associatedPos = pos.filter((p) => p.vendor_id === vendor.id);
  const associatedInvoices = invoices.filter((i) => i.vendor_id === vendor.id);
  const maskedAccount =
    vendor.bank_account_ref.length > 4
      ? `•••• •••• ${vendor.bank_account_ref.slice(-4)}`
      : vendor.bank_account_ref;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span className="section-kicker">TRUSTED VENDOR MASTER RECORD</span>
            <h3>{vendor.name}</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} type="button" aria-label="Close modal">
            ✕
          </button>
        </div>

        <div className="modal-section">
          <h4>Vendor Identification</h4>
          <div className="modal-key-val-grid">
            <div className="modal-key-val">
              <span>Vendor Code</span>
              <strong>{vendor.vendor_code}</strong>
            </div>
            <div className="modal-key-val">
              <span>Operational Status</span>
              <strong style={{ color: vendor.is_active ? "var(--green)" : "var(--red)" }}>
                {vendor.is_active ? "● Active & Verified" : "Suspended"}
              </strong>
            </div>
            <div className="modal-key-val">
              <span>Bank Reference</span>
              <strong>{maskedAccount}</strong>
            </div>
            <div className="modal-key-val">
              <span>Account Verification</span>
              <strong style={{ fontSize: "11px", color: "var(--green)" }}>Registered Master Record</strong>
            </div>
          </div>
        </div>

        <div className="modal-section">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <h4>Associated Purchase Orders ({associatedPos.length})</h4>
            <span style={{ fontSize: "11px", color: "var(--muted)" }}>Pre-authorized expenditure baselines</span>
          </div>
          {associatedPos.length === 0 ? (
            <div style={{ padding: "14px", background: "var(--surface-soft)", borderRadius: "10px", fontSize: "12px", color: "var(--muted)" }}>
              No purchase orders registered under this vendor.
            </div>
          ) : (
            <div style={{ display: "grid", gap: "8px" }}>
              {associatedPos.map((po) => (
                <div
                  key={po.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    background: "var(--surface-soft)",
                    borderRadius: "10px",
                    fontSize: "12px",
                  }}
                >
                  <div>
                    <strong>{po.po_number}</strong> — <span>Issued {po.issue_date}</span>
                    <div style={{ fontSize: "11px", color: "var(--muted)" }}>
                      Items: {po.approved_line_items} • GST: {formatRupees(po.approved_gst_paise)}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <strong style={{ display: "block" }}>{formatRupees(po.approved_total_paise)}</strong>
                    <button
                      type="button"
                      className="secondary-button"
                      style={{ padding: "3px 8px", fontSize: "11px", marginTop: "4px" }}
                      onClick={() => onVerifyVendor(vendor, po)}
                    >
                      Verify for this PO
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-section">
          <h4>Associated Invoices History ({associatedInvoices.length})</h4>
          {associatedInvoices.length === 0 ? (
            <div style={{ padding: "14px", background: "var(--surface-soft)", borderRadius: "10px", fontSize: "12px", color: "var(--muted)" }}>
              No invoices processed yet for this vendor.
            </div>
          ) : (
            <div style={{ display: "grid", gap: "8px" }}>
              {associatedInvoices.map((inv) => (
                <div
                  key={inv.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "10px 14px",
                    background: "var(--surface-soft)",
                    borderRadius: "10px",
                    fontSize: "12px",
                  }}
                >
                  <div>
                    <strong>{inv.invoice_number}</strong>
                    <div style={{ fontSize: "11px", color: "var(--muted)" }}>
                      Created: {formatISTDate(inv.created_at)}
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <strong>{formatRupees(inv.invoice_total_paise)}</strong>
                    <span className={`status-badge ${inv.decision === "APPROVE" ? "approve" : "hold"}`}>
                      {inv.decision}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "20px" }}>
          <button className="secondary-button" onClick={onClose} type="button">
            Close
          </button>
          <button
            className="primary-button"
            onClick={() => onVerifyVendor(vendor, associatedPos.length > 0 ? associatedPos[0] : undefined)}
            disabled={associatedPos.length === 0}
            type="button"
          >
            <Icon name="file" />
            <span>Verify New Invoice for {vendor.vendor_code}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

function AuditEventDetailsModal({
  event,
  onClose,
  onInspectInvoice,
  allInvoices,
}: {
  event: AuditEventRead;
  onClose: () => void;
  onInspectInvoice?: (invNum: string) => void;
  allInvoices?: InvoiceRead[];
}) {
  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span className="section-kicker">IMMUTABLE AUDIT RECORD</span>
            <h3>Audit Event #{event.id}</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} type="button" aria-label="Close modal">
            ✕
          </button>
        </div>

        <div className="modal-section">
          <h4>Event Summary</h4>
          <div className="modal-key-val-grid">
            <div className="modal-key-val">
              <span>Event Type</span>
              <strong>{event.event_type}</strong>
            </div>
            <div className="modal-key-val">
              <span>Decision Outcome</span>
              <strong style={{ color: event.decision === "APPROVE" ? "var(--green)" : "var(--amber)" }}>
                {event.decision ?? "NONE"}
              </strong>
            </div>
            <div className="modal-key-val">
              <span>Target Entity</span>
              <strong>{event.entity_id ? `${event.entity_type} #${event.entity_id}` : "System Audit"}</strong>
            </div>
            <div className="modal-key-val">
              <span>Timestamp (India Standard Time)</span>
              <strong>{formatISTDate(event.created_at)}</strong>
            </div>
          </div>
        </div>

        <div className="modal-section">
          <h4>Logged Findings & Verification Reason</h4>
          <div
            style={{
              padding: "14px",
              background: "var(--surface-soft)",
              border: "1px solid var(--line)",
              borderRadius: "10px",
              fontSize: "13px",
              lineHeight: 1.6,
              color: "var(--text)",
            }}
          >
            {event.reason ?? "Standard verification event recorded."}
          </div>
        </div>

        <div className="modal-section">
          <h4>Governance & Integrity Guarantee</h4>
          <div style={{ fontSize: "11px", color: "var(--muted)", lineHeight: 1.5 }}>
            This event was written to the append-only SQLite ledger using an isolated transaction. Update and delete operations are prohibited at both database engine and API gateway levels.
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "20px" }}>
          <button className="secondary-button" onClick={onClose} type="button">
            Close
          </button>
          {event.entity_id && (
            <button
              className="primary-button"
              onClick={() => {
                const relatedInvoice = allInvoices?.find((i) => i.id === event.entity_id);
                const relatedInvoiceNum = relatedInvoice?.invoice_number;
                if (relatedInvoiceNum) {
                  onClose();
                  onInspectInvoice?.(relatedInvoiceNum);
                }
              }}
              disabled={!allInvoices?.some((i) => i.id === event.entity_id)}
              type="button"
            >
              <span>
                {allInvoices?.find((i) => i.id === event.entity_id)
                  ? `Inspect ${allInvoices.find((i) => i.id === event.entity_id)!.invoice_number}`
                  : `Invoice #${event.entity_id}`}
              </span>
              <Icon name="arrow-right" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function VendorRecordsPage({
  onOpenVerification,
  onVerifyVendor,
}: {
  onOpenVerification: () => void;
  onVerifyVendor?: (vendor: VendorRead, po?: PurchaseOrderRead) => void;
}) {
  const [vendors, setVendors] = useState<VendorRead[]>([]);
  const [pos, setPos] = useState<PurchaseOrderRead[]>([]);
  const [invoices, setInvoices] = useState<InvoiceRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<"vendors" | "pos">("vendors");
  const [selectedVendor, setSelectedVendor] = useState<VendorRead | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [vData, pData, iData] = await Promise.all([
        fetchBackendJson<VendorRead[]>("http://localhost:8000/api/vendors"),
        fetchBackendJson<PurchaseOrderRead[]>("http://localhost:8000/api/purchase-orders"),
        fetchBackendJson<InvoiceRead[]>("http://localhost:8000/api/invoices").catch(() => []),
      ]);
      setVendors(vData);
      setPos(pData);
      setInvoices(iData);
    } catch (err) {
      console.error("Failed to load vendor records", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, []);

  const totalPaise = pos.reduce((acc, p) => acc + p.approved_total_paise, 0);

  const filteredVendors = vendors.filter(
    (v) =>
      v.name.toLowerCase().includes(search.toLowerCase()) ||
      v.vendor_code.toLowerCase().includes(search.toLowerCase()) ||
      v.bank_account_ref.toLowerCase().includes(search.toLowerCase())
  );

  const filteredPos = pos.filter(
    (p) =>
      p.po_number.toLowerCase().includes(search.toLowerCase()) ||
      p.vendor_name.toLowerCase().includes(search.toLowerCase())
  );

  const activeVendorsCount = vendors.filter((v) => v.is_active).length;
  const activePercentage = vendors.length > 0 ? Math.round((activeVendorsCount / vendors.length) * 100) : 100;

  return (
    <section className="verification-workspace">
      {selectedVendor && (
        <VendorDetailsModal
          vendor={selectedVendor}
          pos={pos}
          invoices={invoices}
          onClose={() => setSelectedVendor(null)}
          onVerifyVendor={(v, p) => {
            setSelectedVendor(null);
            onVerifyVendor ? onVerifyVendor(v, p) : onOpenVerification();
          }}
        />
      )}

      <div className="workspace-toolbar">
        <div>
          <span className="section-kicker">DATABASE-BACKED EVIDENCE • TRUSTED RECORD MASTER</span>
          <h2>Vendor records & purchase orders</h2>
        </div>
        <button className="primary-button" onClick={onOpenVerification} type="button">
          <Icon name="file" />
          <span>New Verification</span>
        </button>
      </div>

      <div className="stats-overview-grid">
        <div className="stat-card-modern">
          <span className="stat-label">Trusted Vendors</span>
          <span className="stat-val">{vendors.length.toString().padStart(2, "0")}</span>
          <span className="stat-sub">{activeVendorsCount}/{vendors.length} active ({activePercentage}%)</span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Approved Purchase Orders</span>
          <span className="stat-val">{pos.length.toString().padStart(2, "0")}</span>
          <span className="stat-sub">Pre-approved PO records</span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Total Pre-Approved Value</span>
          <span className="stat-val">{formatRupees(totalPaise)}</span>
          <span className="stat-sub">Authorized baseline</span>
        </div>
      </div>

      <div className="data-table-card">
        <div className="table-toolbar">
          <div className="filter-chips">
            <button
              className={`filter-chip ${activeTab === "vendors" ? "active" : ""}`}
              onClick={() => setActiveTab("vendors")}
              type="button"
            >
              Vendors Master ({vendors.length})
            </button>
            <button
              className={`filter-chip ${activeTab === "pos" ? "active" : ""}`}
              onClick={() => setActiveTab("pos")}
              type="button"
            >
              Purchase Orders ({pos.length})
            </button>
          </div>
          <div className="search-input-wrapper">
            <span className="search-icon-pos">🔍</span>
            <input
              type="search"
              id="vendor-search"
              aria-label={activeTab === "vendors" ? "Search vendors, codes, or account references" : "Search purchase orders or vendors"}
              placeholder={activeTab === "vendors" ? "Search vendor name, code, or acct..." : "Search PO number or vendor..."}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="table-responsive">
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
              Loading records from SQLite database...
            </div>
          ) : activeTab === "vendors" ? (
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>Vendor Code</th>
                  <th>Legal Entity Name</th>
                  <th>Masked Account Reference</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredVendors.map((v) => (
                  <tr
                    key={v.id}
                    className="clickable-row"
                    onClick={() => setSelectedVendor(v)}
                    title="Click to view full vendor details, POs, and history"
                  >
                    <td><strong>{v.vendor_code}</strong></td>
                    <td>
                      <span style={{ fontWeight: 600 }}>{v.name}</span>
                    </td>
                    <td>
                      <span className="status-badge" style={{ background: "var(--surface-soft)" }}>
                        {v.bank_account_ref.length > 4 ? `•••• •••• ${v.bank_account_ref.slice(-4)}` : v.bank_account_ref}
                      </span>
                    </td>
                    <td>
                      <span className="status-badge active-status">
                        {v.is_active ? "● Active" : "Inactive"}
                      </span>
                    </td>
                    <td>
                      <button
                        className="secondary-button"
                        style={{ padding: "4px 10px", fontSize: "11px" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedVendor(v);
                        }}
                        type="button"
                      >
                        View Details
                      </button>
                    </td>
                  </tr>
                ))}
                {filteredVendors.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "30px", color: "var(--muted)" }}>
                      No vendors match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          ) : (
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>PO Reference</th>
                  <th>Vendor Entity</th>
                  <th>Approved Total</th>
                  <th>Approved GST</th>
                  <th>Items</th>
                  <th>Issue Date</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredPos.map((p) => (
                  <tr key={p.id}>
                    <td><strong>{p.po_number}</strong></td>
                    <td>{p.vendor_name} ({p.vendor_code})</td>
                    <td><strong>{formatRupees(p.approved_total_paise)}</strong></td>
                    <td>{formatRupees(p.approved_gst_paise)}</td>
                    <td>{p.approved_line_items} items</td>
                    <td>{p.issue_date}</td>
                    <td>
                      <span className="status-badge active-status">
                        {p.status.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
                {filteredPos.length === 0 && (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", padding: "30px", color: "var(--muted)" }}>
                      No purchase orders match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

function AuditTrailPage({
  onOpenVerification,
  onInspectInvoice,
  allInvoices,
}: {
  onOpenVerification: () => void;
  onInspectInvoice?: (invNum: string) => void;
  allInvoices?: InvoiceRead[];
}) {
  const [auditEvents, setAuditEvents] = useState<AuditEventRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"ALL" | "APPROVE" | "HOLD" | "BLOCK">("ALL");
  const [search, setSearch] = useState("");
  const [selectedEvent, setSelectedEvent] = useState<AuditEventRead | null>(null);

  const loadEvents = async () => {
    try {
      setLoading(true);
      const data = await fetchBackendJson<AuditEventRead[]>("http://localhost:8000/api/audit-events");
      setAuditEvents(data);
    } catch (err) {
      console.error("Failed to load audit events", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadEvents();
  }, []);

  const filtered = auditEvents.filter((ev) => {
    if (filter !== "ALL" && ev.decision !== filter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      return (
        (ev.reason && ev.reason.toLowerCase().includes(q)) ||
        ev.event_type.toLowerCase().includes(q) ||
        (ev.entity_id && ev.entity_id.toString().includes(q))
      );
    }
    return true;
  });

  const totalApprovals = auditEvents.filter((e) => e.decision === "APPROVE").length;
  const totalHolds = auditEvents.filter((e) => e.decision === "HOLD").length;
  const totalBlocks = auditEvents.filter((e) => e.decision === "BLOCK").length;

  return (
    <section className="verification-workspace">
      {selectedEvent && (
        <AuditEventDetailsModal
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
          onInspectInvoice={onInspectInvoice}
          allInvoices={allInvoices}
        />
      )}

      <div className="workspace-toolbar">
        <div>
          <span className="section-kicker">APPEND-ONLY AUDIT LOG • IMMUTABLE EVIDENCE TRACE</span>
          <h2>Audit trail ledger</h2>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button className="secondary-button" onClick={loadEvents} type="button">
            <Icon name="loader" />
            <span>Refresh Ledger</span>
          </button>
          <button className="primary-button" onClick={onOpenVerification} type="button">
            <Icon name="file" />
            <span>New Verification</span>
          </button>
        </div>
      </div>

      <div className="stats-overview-grid">
        <div className="stat-card-modern">
          <span className="stat-label">Total Events Logged</span>
          <span className="stat-val">{auditEvents.length.toString().padStart(2, "0")}</span>
          <span className="stat-sub">Append-only SQLite records</span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Total Approvals</span>
          <span className="stat-val" style={{ color: "var(--green)" }}>
            {totalApprovals.toString().padStart(2, "0")}
          </span>
          <span className="stat-sub">Clean verification matches</span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Holds & Discrepancies</span>
          <span className="stat-val" style={{ color: "var(--amber)" }}>
            {totalHolds.toString().padStart(2, "0")}
          </span>
          <span className="stat-sub">Human review required</span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Blocked Violations</span>
          <span className="stat-val" style={{ color: "var(--red)" }}>
            {totalBlocks.toString().padStart(2, "0")}
          </span>
          <span className="stat-sub">Critical compliance blocks</span>
        </div>
      </div>

      <div className="data-table-card">
        <div className="table-toolbar">
          <div className="filter-chips">
            <button
              className={`filter-chip ${filter === "ALL" ? "active" : ""}`}
              onClick={() => setFilter("ALL")}
              type="button"
            >
              All Events ({auditEvents.length})
            </button>
            <button
              className={`filter-chip ${filter === "APPROVE" ? "active" : ""}`}
              onClick={() => setFilter("APPROVE")}
              type="button"
            >
              Approvals ({totalApprovals})
            </button>
            <button
              className={`filter-chip ${filter === "HOLD" ? "active" : ""}`}
              onClick={() => setFilter("HOLD")}
              type="button"
            >
              Holds ({totalHolds})
            </button>
            <button
              className={`filter-chip ${filter === "BLOCK" ? "active" : ""}`}
              onClick={() => setFilter("BLOCK")}
              type="button"
            >
              Blocks ({totalBlocks})
            </button>
          </div>
          <div className="search-input-wrapper">
            <span className="search-icon-pos">🔍</span>
            <input
              type="search"
              id="audit-search"
              aria-label="Search audit event reasons, type, or entity ID"
              placeholder="Search event reasons, type, or entity ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="table-responsive">
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
              Loading audit events from ledger...
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
              No audit events match your filter.
            </div>
          ) : (
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>Event ID</th>
                  <th>Timestamp (IST)</th>
                  <th>Event Type</th>
                  <th>Decision</th>
                  <th>Logged Findings / Audit Reason</th>
                  <th>Target Entity</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((ev) => (
                  <tr
                    key={ev.id}
                    className="clickable-row"
                    onClick={() => setSelectedEvent(ev)}
                    title="Click to view full immutable audit event"
                  >
                    <td><strong>#{ev.id}</strong></td>
                    <td style={{ fontSize: "11px", color: "var(--muted)", whiteSpace: "nowrap" }}>
                      {formatISTDate(ev.created_at)}
                    </td>
                    <td>
                      <span className="status-badge" style={{ background: "var(--surface-soft)" }}>
                        {ev.event_type}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`status-badge ${
                          ev.decision === "APPROVE" ? "approve" : ev.decision === "BLOCK" ? "block" : "hold"
                        }`}
                      >
                        {ev.decision ?? "NONE"}
                      </span>
                    </td>
                    <td style={{ maxWidth: "420px" }}>{ev.reason ?? "Standard verification recorded."}</td>
                    <td>
                      {ev.entity_id ? `Invoice #${ev.entity_id}` : "System"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

function RiskMonitoringPage({
  onOpenVerification,
  onInspectInvoice,
}: {
  onOpenVerification: () => void;
  onInspectInvoice?: (invNum: string) => void;
}) {
  const [invoices, setInvoices] = useState<InvoiceRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [riskFilter, setRiskFilter] = useState<"ALL" | "low" | "medium" | "high">("ALL");

  useEffect(() => {
    async function loadInvoices() {
      try {
        setLoading(true);
        const data = await fetchBackendJson<InvoiceRead[]>("http://localhost:8000/api/invoices");
        setInvoices(data);
      } catch (err) {
        console.error("Failed to load invoice history", err);
      } finally {
        setLoading(false);
      }
    }
    void loadInvoices();
  }, []);

  const total = invoices.length;
  const approved = invoices.filter((i) => i.decision === "APPROVE").length;
  const held = invoices.filter((i) => i.decision === "HOLD" || i.decision === "BLOCK").length;
  const lowRisk = invoices.filter((i) => i.risk_level === "low").length;
  const medRisk = invoices.filter((i) => i.risk_level === "medium").length;
  const highRisk = invoices.filter((i) => i.risk_level === "high").length;
  const totalPaise = invoices.reduce((acc, i) => acc + i.invoice_total_paise, 0);

  const filteredInvoices = invoices.filter((i) => {
    if (riskFilter === "ALL") return true;
    return i.risk_level?.toLowerCase() === riskFilter;
  });

  return (
    <section className="verification-workspace">
      <div className="workspace-toolbar">
        <div>
          <span className="section-kicker">REAL-TIME DISCREPANCY & COMPLIANCE MONITORING</span>
          <h2>Risk monitoring & invoice history</h2>
        </div>
        <button className="primary-button" onClick={onOpenVerification} type="button">
          <Icon name="file" />
          <span>New Verification</span>
        </button>
      </div>

      <div className="stats-overview-grid">
        <div className="stat-card-modern">
          <span className="stat-label">Invoices Audited</span>
          <span className="stat-val">{total.toString().padStart(2, "0")}</span>
          <span className="stat-sub">Persisted invoice records</span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Clean Match Rate</span>
          <span className="stat-val" style={{ color: "var(--green)" }}>
            {total > 0 ? `${Math.round((approved / total) * 100)}%` : "100%"}
          </span>
          <span className="stat-sub">{approved} approved clean</span>
        </div>
        {/* Corrected metric name: Invoices flagged for review */}
        <div className="stat-card-modern">
          <span className="stat-label">Invoices flagged for review</span>
          <span className="stat-val" style={{ color: "var(--amber)" }}>
            {held} / {total}
          </span>
          <span className="stat-sub">
            {total > 0 ? `${Math.round((held / total) * 100)}% review rate` : "0%"} • {held} flagged
          </span>
        </div>
        <div className="stat-card-modern">
          <span className="stat-label">Total Audited Volume</span>
          <span className="stat-val">{formatRupees(totalPaise)}</span>
          <span className="stat-sub">Integer paise precision</span>
        </div>
      </div>

      {/* Advisory Notice on Discrepancy vs Proven Fraud */}
      <div
        style={{
          border: "1px solid rgba(184, 117, 25, 0.25)",
          borderRadius: "12px",
          background: "rgba(184, 117, 25, 0.05)",
          padding: "12px 16px",
          marginTop: "16px",
          fontSize: "12px",
          color: "var(--muted)",
          lineHeight: 1.5,
          display: "flex",
          alignItems: "center",
          gap: "10px",
        }}
      >
        <Icon name="shield" />
        <span>
          <strong>Operational Guidance:</strong> Flagged invoices represent detected discrepancies (such as amount variances, tax mismatches, or unverified bank accounts). They are held for accounting investigation and should not be assumed fraudulent without human review.
        </span>
      </div>

      {/* Clickable Risk Filter Chips */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px", marginTop: "16px" }}>
        <div
          className="stat-card-modern clickable-row"
          style={{
            borderLeft: "4px solid var(--green)",
            boxShadow: riskFilter === "low" ? "0 0 0 2px var(--green)" : undefined,
          }}
          onClick={() => setRiskFilter(riskFilter === "low" ? "ALL" : "low")}
        >
          <span className="stat-label">Low Risk Invoices</span>
          <span className="stat-val" style={{ color: "var(--green)" }}>{lowRisk}</span>
          <span className="stat-sub">Zero variance; matches approved PO baseline</span>
        </div>
        <div
          className="stat-card-modern clickable-row"
          style={{
            borderLeft: "4px solid var(--amber)",
            boxShadow: riskFilter === "medium" ? "0 0 0 2px var(--amber)" : undefined,
          }}
          onClick={() => setRiskFilter(riskFilter === "medium" ? "ALL" : "medium")}
        >
          <span className="stat-label">Medium Risk Invoices</span>
          <span className="stat-val" style={{ color: "var(--amber)" }}>{medRisk}</span>
          <span className="stat-sub">Minor amount variance or line-item change</span>
        </div>
        <div
          className="stat-card-modern clickable-row"
          style={{
            borderLeft: "4px solid var(--red)",
            boxShadow: riskFilter === "high" ? "0 0 0 2px var(--red)" : undefined,
          }}
          onClick={() => setRiskFilter(riskFilter === "high" ? "ALL" : "high")}
        >
          <span className="stat-label">High Risk / Critical Holds</span>
          <span className="stat-val" style={{ color: "var(--red)" }}>{highRisk}</span>
          <span className="stat-sub">Significant variance, unknown vendor, or account mismatch</span>
        </div>
      </div>

      {/* Verified Invoices Table */}
      <div className="data-table-card">
        <div className="table-toolbar">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ fontWeight: 700, fontSize: "14px" }}>Invoice Verification History</span>
            <span className="soft-tag neutral">
              {riskFilter === "ALL" ? `All (${total})` : `${riskFilter.toUpperCase()} Risk (${filteredInvoices.length})`}
            </span>
          </div>
          <span style={{ fontSize: "11px", color: "var(--muted)" }}>Click any row to open in investigation workspace</span>
        </div>
        <div className="table-responsive">
          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
              Loading invoice records...
            </div>
          ) : filteredInvoices.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--muted)" }}>
              No invoices match the selected risk filter.
            </div>
          ) : (
            <table className="ledger-table">
              <thead>
                <tr>
                  <th>Invoice Number</th>
                  <th>Total Amount</th>
                  <th>GST Amount</th>
                  <th>Items</th>
                  <th>Risk Rating</th>
                  <th>Decision</th>
                  <th>Timestamp (IST)</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredInvoices.map((inv) => (
                  <tr
                    key={inv.id}
                    className="clickable-row"
                    onClick={() => onInspectInvoice?.(inv.invoice_number)}
                    title="Click to inspect this invoice in verification workspace"
                  >
                    <td><strong>{inv.invoice_number}</strong></td>
                    <td><strong>{formatRupees(inv.invoice_total_paise)}</strong></td>
                    <td>{formatRupees(inv.gst_amount_paise)}</td>
                    <td>{inv.line_items}</td>
                    <td>
                      <span className={`status-badge ${inv.risk_level === "low" ? "approve" : inv.risk_level === "high" ? "block" : "hold"}`}>
                        {inv.risk_level?.toUpperCase() ?? "UNKNOWN"}
                      </span>
                    </td>
                    <td>
                      <span className={`status-badge ${inv.decision === "APPROVE" ? "approve" : inv.decision === "BLOCK" ? "block" : "hold"}`}>
                        {inv.decision ?? "NONE"}
                      </span>
                    </td>
                    <td style={{ fontSize: "11px", color: "var(--muted)", whiteSpace: "nowrap" }}>
                      {formatISTDate(inv.created_at)}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="secondary-button"
                        style={{ padding: "3px 8px", fontSize: "11px" }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onInspectInvoice?.(inv.invoice_number);
                        }}
                      >
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}

function SettingsPage({
  theme,
  onToggleTheme,
}: {
  theme: "light" | "dark";
  onToggleTheme: () => void;
}) {
  return (
    <section className="verification-workspace">
      <div className="workspace-toolbar">
        <div>
          <span className="section-kicker">WORKSPACE PREFERENCES & SYSTEM GOVERNANCE</span>
          <h2>Workspace settings</h2>
        </div>
      </div>

      <div className="settings-container">
        <div className="settings-box">
          <h3>Display & Theme Preferences</h3>
          <p>Customize the visual workspace theme for long auditing sessions.</p>
          <div className="setting-row">
            <div className="setting-info">
              <strong>Workspace Theme</strong>
              <span>Currently using {theme === "light" ? "Editorial Linen (Light Mode)" : "Executive Midnight Slate (Dark Mode)"}</span>
            </div>
            <button className="theme-toggle-btn" onClick={onToggleTheme} type="button">
              <span>{theme === "light" ? "🌙 Switch to Dark Mode" : "☀️ Switch to Light Mode"}</span>
            </button>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>Monetary Display Precision</strong>
              <span>Indian Rupees (INR ₹) formatted with integer paise precision</span>
            </div>
            <span className="status-badge active-status">Integer Paise</span>
          </div>
        </div>

        <div className="settings-box">
          <h3>Security & AI Governance Invariants</h3>
          <p>Verified security invariants enforced on this workspace instance.</p>
          <div className="setting-row">
            <div className="setting-info">
              <strong>Deterministic Verification Engine</strong>
              <span>Direct database PO matching without generative approval override</span>
            </div>
            <span className="status-badge active-status">Enforced</span>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>Bidirectional Evidence Binding</strong>
              <span>Values must be substantiated within document text evidence quotes</span>
            </div>
            <span className="status-badge active-status">Strict Mode</span>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>Prompt Injection Heuristic Shield</strong>
              <span>Adversarial directive pattern detection with human review alerts</span>
            </div>
            <span className="status-badge active-status">Active</span>
          </div>
          <div className="setting-row">
            <div className="setting-info">
              <strong>Immutable Audit Log</strong>
              <span>Append-only SQLite event ledger with zero deletion API routes</span>
            </div>
            <span className="status-badge active-status">Append-Only</span>
          </div>
        </div>
      </div>
    </section>
  );
}

async function fetchBackendJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { method: "GET", cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Request failed with HTTP ${response.status}.`);
  }

  return (await response.json()) as T;
}

export default function Dashboard() {
  const [section, setSection] = useState<Section>("Overview");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [connection, setConnection] = useState<ConnectionState>("idle");
  const [connectionError, setConnectionError] = useState("");
  const [dashboardData, setDashboardData] = useState<DashboardData>(defaultDashboard);
  const [dashboardError, setDashboardError] = useState("");
  const [allInvoices, setAllInvoices] = useState<InvoiceRead[]>([]);
  const [allPOs, setAllPOs] = useState<PurchaseOrderRead[]>([]);
  const [allAuditEvents, setAllAuditEvents] = useState<AuditEventRead[]>([]);
  const [selectedAuditEvent, setSelectedAuditEvent] = useState<AuditEventRead | null>(null);
  const [prefillInvoice, setPrefillInvoice] = useState<{
    invoiceNumber?: string;
    vendorName?: string;
    poNumber?: string;
    invoiceTotal?: string;
    gstAmount?: string;
    lineItems?: string;
    bankAccountRef?: string;
  } | null>(null);

  const handleInspectInvoice = (invNum: string, vendorName?: string) => {
    const invoice = allInvoices.find((i) => i.invoice_number === invNum);
    const po = invoice ? allPOs.find((p) => p.id === invoice.po_id) : null;
    setPrefillInvoice({
      invoiceNumber: invNum,
      vendorName: vendorName || (po?.vendor_name ?? ""),
      poNumber: po?.po_number ?? "",
      invoiceTotal: invoice ? (invoice.invoice_total_paise / 100).toFixed(2) : "",
      gstAmount: invoice ? (invoice.gst_amount_paise / 100).toFixed(2) : "",
      lineItems: invoice ? String(invoice.line_items) : "",
      bankAccountRef: invoice?.invoice_bank_account_ref ?? "",
    });
    setSection("Invoice Verification");
  };

  const handleVerifyVendorInvoice = (vendor: VendorRead, po?: PurchaseOrderRead) => {
    setPrefillInvoice({
      invoiceNumber: `INV-${vendor.vendor_code}-01`,
      vendorName: vendor.name,
      poNumber: po ? po.po_number : "PO-1001",
      invoiceTotal: po ? (po.approved_total_paise / 100).toFixed(2) : "85000.00",
      gstAmount: po ? (po.approved_gst_paise / 100).toFixed(2) : "12966.10",
      lineItems: po ? String(po.approved_line_items) : "5",
      bankAccountRef: vendor.bank_account_ref,
    });
    setSection("Invoice Verification");
  };

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.title = `FinTrust AI | ${section}`;
  }, [section]);

  async function checkConnection() {
    setConnection("loading");
    setConnectionError("");

    try {
      const payload = await fetchBackendJson<{ application: string; status: string }>("http://localhost:8000/health");

      if (payload.application !== "FinTrust AI") {
        throw new Error("The health response did not identify FinTrust AI.");
      }

      setConnection("connected");
    } catch (error) {
      setConnection("disconnected");
      setConnectionError(
        error instanceof TypeError
          ? "Could not reach the backend. Check that it is running at localhost:8000."
          : error instanceof Error
            ? error.message
            : "An unexpected error occurred while checking the backend.",
      );
    }
  }

  useEffect(() => {
    const loadDashboard = async () => {
      try {
        const [dashboardPayload, invoicesPayload, posPayload, auditPayload] = await Promise.all([
          fetchBackendJson<DashboardData>("http://localhost:8000/api/dashboard"),
          fetchBackendJson<InvoiceRead[]>("http://localhost:8000/api/invoices").catch(() => []),
          fetchBackendJson<PurchaseOrderRead[]>("http://localhost:8000/api/purchase-orders").catch(() => []),
          fetchBackendJson<AuditEventRead[]>("http://localhost:8000/api/audit-events").catch(() => []),
        ]);
        setDashboardData(dashboardPayload);
        setAllInvoices(invoicesPayload);
        setAllPOs(posPayload);
        setAllAuditEvents(auditPayload);
        setDashboardError("");
      } catch (error) {
        setDashboardError(
          error instanceof Error
            ? error.message
            : "Unable to load dashboard data from the backend.",
        );
      }
    };

    void loadDashboard();
    void checkConnection();
  }, []);

  const isOverview = section === "Overview";

  return (
    <div className="app-shell" data-theme={theme}>
      <aside className="sidebar">
        <div className="sidebar-brand">
          <Brand />
          <span className="workspace-label">MSME WORKSPACE</span>
        </div>

        <div className="nav-caption">WORKSPACE</div>
        <nav className="sidebar-nav" aria-label="Main navigation">
          {navigation.map((item) => (
            <button
              aria-current={section === item.label ? "page" : undefined}
              className={`nav-item ${section === item.label ? "nav-item-active" : ""}`}
              key={item.label}
              onClick={() => setSection(item.label)}
              type="button"
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {section === item.label && <span className="nav-active-mark" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="nav-caption">PREFERENCES</div>
          <button
            aria-current={section === "Settings" ? "page" : undefined}
            className={`nav-item ${section === "Settings" ? "nav-item-active" : ""}`}
            onClick={() => setSection("Settings")}
            type="button"
          >
            <Icon name="settings" />
            <span>Settings</span>
            {section === "Settings" && <span className="nav-active-mark" />}
          </button>
          <div className="sidebar-note">
            <span className="note-mark">
              <Icon name="shield" />
            </span>
            <div>
              <strong>Evidence first.</strong>
              <span>Decisions stay yours.</span>
            </div>
          </div>
          <div className="sidebar-legal">FINTRUST AI <span>·</span> ENTERPRISE AUDIT</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand">
            <Brand />
          </div>
          <div className="breadcrumb">
            <span>Workspace</span>
            <span className="breadcrumb-slash">/</span>
            <strong>{section}</strong>
          </div>
          <div className="topbar-tools">
            <ConnectionBadge state={connection} />
            <button
              aria-label="Check System Connection"
              className="connection-button"
              disabled={connection === "loading"}
              onClick={checkConnection}
              type="button"
            >
              <Icon
                name={connection === "loading" ? "loader" : "activity"}
                className={`icon ${connection === "loading" ? "spin" : ""}`}
              />
              <span>{connection === "loading" ? "Checking..." : "Check System Connection"}</span>
            </button>
          </div>
        </header>

        <div className="page-content">
          {isOverview && (
            <section className="page-intro">
              <div>
                <div className="eyebrow">
                  <span />FINTRUST AI • INDIAN MSME FINANCIAL VERIFICATION
                </div>
                <h1>Financial Evidence Workspace</h1>
                <p>Review invoices, verify trusted business records and investigate financial discrepancies.</p>
              </div>
              <div className="workspace-id">
                <span>WORKSPACE</span>
                <strong>MSME <span>/</span> 001</strong>
              </div>
            </section>
          )}

          {connectionError && (
            <div className="connection-error" role="alert">
              <span className="error-mark">!</span>
              <span>{connectionError}</span>
              <button
                aria-label="Dismiss connection error"
                className="error-dismiss"
                onClick={() => setConnectionError("")}
                type="button"
              >
                ×
              </button>
            </div>
          )}

          {dashboardError && (
            <div className="connection-error" role="alert">
              <span className="error-mark">!</span>
              <span>{dashboardError}</span>
            </div>
          )}

          {section === "Overview" ? (
            <OverviewPage
              onOpenVerification={() => setSection("Invoice Verification")}
              onOpenVendors={() => setSection("Vendor Records")}
              onOpenRisk={() => setSection("Risk Monitoring")}
              onInspectInvoice={handleInspectInvoice}
              onSelectAuditEntry={(entry) => {
                if (entry.id) {
                  const found = allAuditEvents.find((e) => e.id === entry.id);
                  if (found) {
                    setSelectedAuditEvent(found);
                    return;
                  }
                }
                setSection("Audit Trail");
              }}
              summary={dashboardData.summary}
              cases={dashboardData.cases}
              auditEntries={dashboardData.audit_entries}
            />
          ) : section === "Invoice Verification" ? (
            <InvoiceVerificationWorkspace
              onBack={() => setSection("Overview")}
              prefillData={prefillInvoice}
            />
          ) : section === "Vendor Records" ? (
            <VendorRecordsPage
              onOpenVerification={() => setSection("Invoice Verification")}
              onVerifyVendor={handleVerifyVendorInvoice}
            />
          ) : section === "Risk Monitoring" ? (
            <RiskMonitoringPage
              onOpenVerification={() => setSection("Invoice Verification")}
              onInspectInvoice={handleInspectInvoice}
            />
          ) : section === "Audit Trail" ? (
            <AuditTrailPage
              onOpenVerification={() => setSection("Invoice Verification")}
              onInspectInvoice={handleInspectInvoice}
              allInvoices={allInvoices}
            />
          ) : (
            <SettingsPage
              theme={theme}
              onToggleTheme={() => setTheme((t) => (t === "light" ? "dark" : "light"))}
            />
          )}

          {selectedAuditEvent && (
            <AuditEventDetailsModal
              event={selectedAuditEvent}
              onClose={() => setSelectedAuditEvent(null)}
              onInspectInvoice={handleInspectInvoice}
              allInvoices={allInvoices}
            />
          )}

          <footer className="page-footer">
            <span>FinTrust AI <span className="footer-separator">/</span> Evidence before approval.</span>
            <span>Designed for Indian MSMEs</span>
          </footer>
        </div>
      </main>
    </div>
  );
}

type VerificationWorkflowState =
  | "document_required"
  | "extracting"
  | "extraction_complete"
  | "awaiting_human_review"
  | "verifying"
  | "APPROVE"
  | "HOLD"
  | "BLOCK";

function InvoiceVerificationWorkspace({
  onBack,
  prefillData,
}: {
  onBack: () => void;
  prefillData?: {
    invoiceNumber?: string;
    vendorName?: string;
    poNumber?: string;
    invoiceTotal?: string;
    gstAmount?: string;
    lineItems?: string;
    bankAccountRef?: string;
  } | null;
}) {
  const [verification, setVerification] = useState<VerificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Trusted baselines fetched from database
  const [trustedPOs, setTrustedPOs] = useState<PurchaseOrderRead[]>([]);
  const [trustedVendors, setTrustedVendors] = useState<VendorRead[]>([]);
  const [loadingBaselines, setLoadingBaselines] = useState(true);

  // Tab mode: "upload" vs "manual"
  const [activeTab, setActiveTab] = useState<"upload" | "manual">("upload");

  // Document upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [extractionError, setExtractionError] = useState("");
  const [extractionData, setExtractionData] = useState<DocumentExtractionResult | null>(null);
  const [showRawText, setShowRawText] = useState(false);

  // Form input state (used for both manual entry and reviewing AI extractions)
  const [invoiceNumber, setInvoiceNumber] = useState(prefillData?.invoiceNumber ?? "");
  const [vendorName, setVendorName] = useState(prefillData?.vendorName ?? "");
  const [poNumber, setPoNumber] = useState(prefillData?.poNumber ?? "");
  const [invoiceTotal, setInvoiceTotal] = useState(prefillData?.invoiceTotal ?? "");
  const [gstAmount, setGstAmount] = useState(prefillData?.gstAmount ?? "");
  const [lineItems, setLineItems] = useState(prefillData?.lineItems ?? "");
  const [bankAccountRef, setBankAccountRef] = useState(prefillData?.bankAccountRef ?? "");

  useEffect(() => {
    async function loadBaselines() {
      try {
        setLoadingBaselines(true);
        const [posData, vendorsData] = await Promise.all([
          fetchBackendJson<PurchaseOrderRead[]>("http://localhost:8000/api/purchase-orders"),
          fetchBackendJson<VendorRead[]>("http://localhost:8000/api/vendors"),
        ]);
        setTrustedPOs(posData);
        setTrustedVendors(vendorsData);
      } catch (err) {
        console.error("Failed to load PO baselines", err);
      } finally {
        setLoadingBaselines(false);
      }
    }
    void loadBaselines();
  }, []);

  useEffect(() => {
    if (prefillData) {
      if (prefillData.invoiceNumber) setInvoiceNumber(prefillData.invoiceNumber);
      if (prefillData.vendorName) setVendorName(prefillData.vendorName);
      if (prefillData.poNumber) setPoNumber(prefillData.poNumber);
      if (prefillData.invoiceTotal) setInvoiceTotal(prefillData.invoiceTotal);
      if (prefillData.gstAmount) setGstAmount(prefillData.gstAmount);
      if (prefillData.lineItems) setLineItems(prefillData.lineItems);
      if (prefillData.bankAccountRef) setBankAccountRef(prefillData.bankAccountRef);
      setVerification(null);
      setError("");
    }
  }, [prefillData]);

  const presets = [
    {
      label: "Matching (PO-1001)",
      badge: "Clean Match",
      data: {
        invoiceNumber: "INV-TEST-1001",
        vendorName: "Aster Office Supplies",
        poNumber: "PO-1001",
        invoiceTotal: "85000.00",
        gstAmount: "12966.10",
        lineItems: "5",
        bankAccountRef: "DEMO-ACCT-1001",
      },
    },
    {
      label: "Amount Mismatch (+₹50)",
      badge: "Variance Alert",
      data: {
        invoiceNumber: "INV-TEST-1002",
        vendorName: "Aster Office Supplies",
        poNumber: "PO-1001",
        invoiceTotal: "85050.00",
        gstAmount: "12966.10",
        lineItems: "5",
        bankAccountRef: "DEMO-ACCT-1001",
      },
    },
    {
      label: "GST Mismatch (+₹6k)",
      badge: "GST Warning",
      data: {
        invoiceNumber: "INV-TEST-1003",
        vendorName: "BluePeak Technologies",
        poNumber: "PO-1002",
        invoiceTotal: "120000.00",
        gstAmount: "19000.00",
        lineItems: "8",
        bankAccountRef: "DEMO-ACCT-1002",
      },
    },
    {
      label: "Bank Ref Mismatch",
      badge: "Account Alert",
      data: {
        invoiceNumber: "INV-TEST-1004",
        vendorName: "Aster Office Supplies",
        poNumber: "PO-1001",
        invoiceTotal: "85000.00",
        gstAmount: "12966.10",
        lineItems: "5",
        bankAccountRef: "DEMO-ACCT-9999",
      },
    },
    {
      label: "Unknown PO",
      badge: "Block Target",
      data: {
        invoiceNumber: "INV-TEST-1005",
        vendorName: "Aster Office Supplies",
        poNumber: "PO-UNKNOWN",
        invoiceTotal: "85000.00",
        gstAmount: "12966.10",
        lineItems: "5",
        bankAccountRef: "DEMO-ACCT-1001",
      },
    },
  ];

  const applyPreset = (presetData: typeof presets[0]["data"]) => {
    setInvoiceNumber(presetData.invoiceNumber);
    setVendorName(presetData.vendorName);
    setPoNumber(presetData.poNumber);
    setInvoiceTotal(presetData.invoiceTotal);
    setGstAmount(presetData.gstAmount);
    setLineItems(presetData.lineItems);
    setBankAccountRef(presetData.bankAccountRef);
    setError("");
    setVerification(null);
  };

  // Handle document file selection and upload
  const handleFileChange = (file: File | null) => {
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      setExtractionError("File size exceeds 10 MB limit.");
      return;
    }

    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "png", "jpg", "jpeg"].includes(ext || "")) {
      setExtractionError("Unsupported file type. Please upload a PDF, PNG, or JPG document.");
      return;
    }

    setSelectedFile(file);
    setExtractionError("");
    setExtractionData(null);
    setVerification(null);
  };

  const handleDocumentExtract = async () => {
    if (!selectedFile) {
      setExtractionError("Please select a document file first.");
      return;
    }

    setExtracting(true);
    setExtractionError("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch("http://localhost:8000/api/documents/extract", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        let errDetail = `Extraction failed with status ${response.status}`;
        try {
          const resJson = await response.json();
          if (resJson.detail) errDetail = resJson.detail;
        } catch {
          // ignore
        }
        throw new Error(errDetail);
      }

      const result = (await response.json()) as DocumentExtractionResult;
      setExtractionData(result);

      // Prepopulate editable form fields from extraction
      if (result.fields) {
        if (result.fields.invoice_number?.value != null) {
          setInvoiceNumber(String(result.fields.invoice_number.value));
        }
        if (result.fields.vendor_name?.value != null) {
          setVendorName(String(result.fields.vendor_name.value));
        }
        if (result.fields.po_number?.value != null) {
          setPoNumber(String(result.fields.po_number.value));
        }
        if (result.fields.invoice_total?.value != null) {
          setInvoiceTotal(String(result.fields.invoice_total.value));
        }
        if (result.fields.gst_amount?.value != null) {
          setGstAmount(String(result.fields.gst_amount.value));
        }
        if (result.fields.line_items?.value != null) {
          setLineItems(String(result.fields.line_items.value));
        }
        if (result.fields.invoice_bank_account_ref?.value != null) {
          setBankAccountRef(String(result.fields.invoice_bank_account_ref.value));
        }
      }
    } catch (err) {
      setExtractionError(
        err instanceof Error ? err.message : "An error occurred during document extraction.",
      );
    } finally {
      setExtracting(false);
    }
  };

  const handleVerify = useCallback(
    async (e?: React.FormEvent) => {
      if (e) e.preventDefault();
      if (loading) return;
      setLoading(true);
      setError("");

      if (!invoiceNumber.trim()) {
        setError("Invoice number is required.");
        setLoading(false);
        return;
      }
      if (!vendorName.trim()) {
        setError("Vendor name is required.");
        setLoading(false);
        return;
      }
      if (!poNumber.trim()) {
        setError("Purchase order number is required.");
        setLoading(false);
        return;
      }

      const totalNum = parseFloat(invoiceTotal);
      if (isNaN(totalNum) || totalNum <= 0) {
        setError("Invoice amount must be a strictly positive number.");
        setLoading(false);
        return;
      }

      const gstNum = parseFloat(gstAmount);
      if (isNaN(gstNum) || gstNum < 0) {
        setError("GST amount must be non-negative.");
        setLoading(false);
        return;
      }

      if (gstNum > totalNum) {
        setError("GST amount cannot exceed the invoice total.");
        setLoading(false);
        return;
      }

      const itemsNum = parseInt(lineItems, 10);
      if (isNaN(itemsNum) || itemsNum < 1) {
        setError("Line items must be at least 1.");
        setLoading(false);
        return;
      }

      try {
        const response = await fetch("http://localhost:8000/api/verify-invoice", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            invoice_number: invoiceNumber.trim(),
            vendor_name: vendorName.trim(),
            po_number: poNumber.trim(),
            invoice_total: totalNum,
            gst_amount: gstNum,
            line_items: itemsNum,
            invoice_bank_account_ref: bankAccountRef.trim() || null,
          }),
        });

        if (!response.ok) {
          let errMessage = `Verification request failed with HTTP ${response.status}.`;
          try {
            const errData = await response.json();
            if (errData.detail) {
              if (Array.isArray(errData.detail)) {
                errMessage = errData.detail
                  .map((d: { msg?: string; loc?: string[] }) => d.msg || JSON.stringify(d))
                  .join("; ");
              } else if (typeof errData.detail === "string") {
                errMessage = errData.detail;
              }
            }
          } catch {
            // Default error message
          }
          throw new Error(errMessage);
        }

        const payload = (await response.json()) as VerificationResult;
        setVerification(payload);
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : "Unable to complete invoice verification.",
        );
      } finally {
        setLoading(false);
      }
    },
    [invoiceNumber, vendorName, poNumber, invoiceTotal, gstAmount, lineItems, bankAccountRef, loading],
  );

  const findings = verification?.findings ?? [];

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        const fakeEvent = { preventDefault: () => {} } as React.FormEvent;
        void handleVerify(fakeEvent);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleVerify]);

  // Resolve trusted database PO and Vendor records
  const trimmedPo = poNumber.trim().toUpperCase();
  const matchedPO = trustedPOs.find((p) => p.po_number.toUpperCase() === trimmedPo);
  const matchedVendor = matchedPO
    ? trustedVendors.find(
        (v) => v.id === matchedPO.vendor_id || v.name.toLowerCase() === matchedPO.vendor_name.toLowerCase()
      )
    : null;

  // Compute non-contradictory verification workflow state
  const getWorkflowState = (): VerificationWorkflowState => {
    if (loading) return "verifying";
    if (extracting) return "extracting";
    if (verification) return verification.decision;
    if (extractionData) return "extraction_complete";
    if (selectedFile || invoiceNumber.trim() || poNumber.trim()) return "awaiting_human_review";
    return "document_required";
  };

  const currentWorkflowState = getWorkflowState();

  const stateBadges: Record<VerificationWorkflowState, { text: string; className: string }> = {
    document_required: { text: "Document required", className: "soft-tag neutral" },
    extracting: { text: "Extracting...", className: "soft-tag warning" },
    extraction_complete: { text: "Extraction complete", className: "soft-tag" },
    awaiting_human_review: { text: "Awaiting human review", className: "soft-tag warning" },
    verifying: { text: "Verifying...", className: "soft-tag warning" },
    APPROVE: { text: "APPROVE", className: "decision-badge approve" },
    HOLD: { text: "HOLD", className: "decision-badge hold" },
    BLOCK: { text: "BLOCK", className: "decision-badge block" },
  };

  // Missing required fields inspection
  const missingFields: string[] = [];
  if (!invoiceNumber.trim()) missingFields.push("Invoice Number");
  if (!vendorName.trim()) missingFields.push("Vendor Name");
  if (!poNumber.trim()) missingFields.push("Purchase Order Number");
  if (!invoiceTotal.trim() || isNaN(parseFloat(invoiceTotal))) missingFields.push("Total Amount");
  if (!gstAmount.trim() || isNaN(parseFloat(gstAmount))) missingFields.push("GST Amount");
  if (!lineItems.trim() || isNaN(parseInt(lineItems, 10))) missingFields.push("Line Items");

  // Live reconciliation variance calculation
  const parsedInvoiceTotal = parseFloat(invoiceTotal) || 0;
  const parsedGstAmount = parseFloat(gstAmount) || 0;
  const parsedLineItems = parseInt(lineItems, 10) || 0;

  const approvedTotalRupees = matchedPO ? matchedPO.approved_total_paise / 100 : verification?.approved_total ?? null;
  const approvedGstRupees = matchedPO ? matchedPO.approved_gst_paise / 100 : verification?.approved_gst ?? null;
  const approvedItemsCount = matchedPO ? matchedPO.approved_line_items : verification?.approved_line_items ?? null;
  const trustedVendorName = matchedPO ? matchedPO.vendor_name : verification?.vendor_name ?? null;
  const trustedBankRef = matchedVendor?.bank_account_ref ?? null;

  const amountVariance = approvedTotalRupees != null ? parsedInvoiceTotal - approvedTotalRupees : null;
  const gstVariance = approvedGstRupees != null ? parsedGstAmount - approvedGstRupees : null;
  const lineItemsVariance = approvedItemsCount != null ? parsedLineItems - approvedItemsCount : null;
  const vendorMatched = trustedVendorName ? vendorName.trim().toLowerCase() === trustedVendorName.trim().toLowerCase() : null;
  const bankMatched = trustedBankRef ? bankAccountRef.trim() === trustedBankRef.trim() : null;

  return (
    <section className="verification-workspace">
      {/* Refined clean single header with no duplicate kicker */}
      <div className="workspace-toolbar">
        <div>
          <h1 style={{ fontSize: "1.85rem", letterSpacing: "-0.05em", margin: "0 0 6px" }}>Verify an invoice</h1>
          <p style={{ color: "var(--muted)", fontSize: "14px", margin: 0 }}>
            Upload a financial document or enter invoice details manually. Review the evidence before submitting it for verification.
          </p>
        </div>
        <button className="secondary-button" onClick={onBack} type="button">
          Back to overview
        </button>
      </div>

      {error && (
        <div className="connection-error" role="alert">
          <span className="error-mark">!</span>
          <span>{error}</span>
          <button
            aria-label="Dismiss error"
            className="error-dismiss"
            onClick={() => setError("")}
            type="button"
          >
            ×
          </button>
        </div>
      )}

      {verification?.duplicate && (
        <div className="duplicate-banner" role="alert">
          <Icon name="risk" />
          <span>
            Duplicate invoice detected: This invoice was already verified as record #
            {verification.duplicate_of_invoice_id}. No duplicate record was created; original record is retained.
          </span>
        </div>
      )}

      <div className="verification-layout">
        {/* =========================================================================
            LEFT PANE: Intake & Review Form
            ========================================================================= */}
        <aside className="verification-pane">
          <div className="panel-header">
            <span style={{ fontWeight: 700, fontSize: "14px" }}>Invoice Intake</span>
            <span className={stateBadges[currentWorkflowState].className}>
              {stateBadges[currentWorkflowState].text}
            </span>
          </div>

          {/* Mode Switcher: Upload Document vs Manual Entry */}
          <div className="mode-tabs">
            <button
              type="button"
              className={`mode-tab-button ${activeTab === "upload" ? "active" : ""}`}
              onClick={() => setActiveTab("upload")}
            >
              <Icon name="file" />
              <span>Upload Document</span>
            </button>
            <button
              type="button"
              className={`mode-tab-button ${activeTab === "manual" ? "active" : ""}`}
              onClick={() => setActiveTab("manual")}
            >
              <Icon name="grid" />
              <span>Manual & Presets</span>
            </button>
          </div>

          {/* Upload Section */}
          {activeTab === "upload" && (
            <div style={{ marginBottom: "16px" }}>
              <div
                className={`dropzone ${dragActive ? "drag-active" : ""}`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragActive(true);
                }}
                onDragLeave={() => setDragActive(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setDragActive(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    handleFileChange(e.dataTransfer.files[0]);
                  }
                }}
                onClick={() => document.getElementById("document-file-input")?.click()}
              >
                <input
                  id="document-file-input"
                  type="file"
                  accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileChange(e.target.files[0]);
                    }
                  }}
                />
                <span className="dropzone-icon" style={{ width: "32px", height: "32px" }}>
                  <Icon name="file" />
                </span>
                <div>
                  <strong>{selectedFile ? selectedFile.name : "Drag & drop invoice document"}</strong>
                  <p>
                    {selectedFile
                      ? `${(selectedFile.size / 1024).toFixed(1)} KB • Click or drop to replace`
                      : "PDF, PNG, or JPG (Max 10 MB, up to 10 pages)"}
                  </p>
                </div>
              </div>

              {/* Staged File Information Card (Tipalti-style Document Preview) */}
              {selectedFile && (
                <div
                  style={{
                    border: "1px solid var(--line)",
                    borderRadius: "10px",
                    background: "var(--surface)",
                    padding: "10px 12px",
                    marginBottom: "12px",
                    fontSize: "12px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                  }}
                >
                  <div style={{ display: "grid", gap: "2px" }}>
                    <strong style={{ fontSize: "12px" }}>{selectedFile.name}</strong>
                    <span style={{ fontSize: "11px", color: "var(--muted)" }}>
                      {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.type || "Document"}
                      {extractionData && ` • ${extractionData.page_count} page(s)`}
                    </span>
                  </div>
                  <button
                    type="button"
                    style={{
                      background: "none",
                      border: "none",
                      color: "var(--red)",
                      fontSize: "11px",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                      setExtractionData(null);
                    }}
                  >
                    Clear
                  </button>
                </div>
              )}

              {extractionError && (
                <div className="connection-error" role="alert" style={{ marginBottom: "12px" }}>
                  <span className="error-mark">!</span>
                  <span>{extractionError}</span>
                </div>
              )}

              <button
                type="button"
                className="secondary-button"
                style={{ width: "100%", justifyContent: "center" }}
                disabled={!selectedFile || extracting}
                onClick={handleDocumentExtract}
              >
                <Icon name="activity" />
                <span>{extracting ? "Extracting text with PyMuPDF / OCR..." : "Extract with AI & OCR"}</span>
              </button>

              {/* Extraction Preview, Page Boundaries & Alerts */}
              {extractionData && (
                <div style={{ marginTop: "14px" }}>
                  {extractionData.suspicious_content_detected && (
                    <div className="suspicious-alert">
                      <Icon name="risk" />
                      <div>
                        <strong>Suspicious Instruction Patterns Detected:</strong>
                        <ul style={{ margin: "4px 0 0", paddingLeft: "16px", fontSize: "11px" }}>
                          {extractionData.suspicious_warnings.map((w, idx) => (
                            <li key={idx}>{w}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {!extractionData.ai_extraction_available && (
                    <div className="duplicate-banner" style={{ background: "var(--amber-soft)", marginBottom: "10px" }}>
                      <Icon name="risk" />
                      <span>
                        AI model unavailable (OPENROUTER_API_KEY not configured). Document text extracted successfully via PyMuPDF. Review values below.
                      </span>
                    </div>
                  )}

                  {/* Document Preview Box with Page Boundaries */}
                  <div
                    style={{
                      border: "1px solid var(--line)",
                      borderRadius: "10px",
                      background: "var(--surface)",
                      padding: "10px 12px",
                      marginTop: "10px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)" }}>
                        {extractionData.file_type.toUpperCase()} • {extractionData.page_count} page(s)
                        {extractionData.ocr_applied && ` • ${extractionData.ocr_engine}`}
                      </span>
                      <button
                        type="button"
                        style={{ fontSize: "11px", color: "var(--green)", background: "none", border: "none", cursor: "pointer", fontWeight: 700 }}
                        onClick={() => setShowRawText(!showRawText)}
                      >
                        {showRawText ? "▲ Hide Text View" : "▼ Inspect Document Text"}
                      </button>
                    </div>

                    {showRawText && (
                      <div className="text-preview-box">
                        {extractionData.pages && extractionData.pages.length > 0 ? (
                          extractionData.pages.map((p) => (
                            <div key={p.page_number} style={{ marginBottom: "10px" }}>
                              <div style={{ color: "#7ee787", fontWeight: 700, borderBottom: "1px dashed rgba(255,255,255,0.2)", paddingBottom: "2px", marginBottom: "4px" }}>
                                --- PAGE {p.page_number} {p.ocr_applied ? "(OCR Fallback)" : "(Native Selectable Text)"} ---
                              </div>
                              <div>{p.text || "[Empty page text]"}</div>
                            </div>
                          ))
                        ) : (
                          <div>{extractionData.raw_text}</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Sample Invoices */}
          <div style={{ marginBottom: "14px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
              <span style={{ fontSize: "11px", fontWeight: 700, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Sample Invoices
              </span>
              <span style={{ fontSize: "10px", color: "var(--muted)" }}>Click to load sample</span>
            </div>
            <div className="sample-presets">
              {presets.map((preset) => (
                <button
                  key={preset.label}
                  type="button"
                  className="preset-chip"
                  onClick={() => applyPreset(preset.data)}
                  title={preset.badge}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Human Review Banner */}
          <div
            style={{
              background: "rgba(31, 93, 74, 0.05)",
              border: "1px solid rgba(31, 93, 74, 0.15)",
              borderRadius: "8px",
              padding: "8px 10px",
              marginBottom: "14px",
              fontSize: "11px",
              color: "var(--muted)",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <Icon name="shield" />
            <span>Human Review: Confirm or modify extracted values before submitting for verification.</span>
          </div>

          {/* Editable Human Confirmation Form */}
          <form onSubmit={handleVerify} className="form-grid">
            <div className="form-field">
              <label htmlFor="input-inv-num">Invoice Number *</label>
              <input
                id="input-inv-num"
                type="text"
                value={invoiceNumber}
                onChange={(e) => setInvoiceNumber(e.target.value)}
                placeholder="e.g. INV-TEST-1001"
                required
              />
              {extractionData?.fields?.invoice_number && (
                <div className="field-meta-row">
                  <span className={`evidence-badge ${extractionData.fields.invoice_number.evidence_verified ? "verified" : "unverified"}`}>
                    {extractionData.fields.invoice_number.evidence_verified ? "✓ Evidence Verified" : "⚠ Unverified Quote"}
                  </span>
                  <span className="confidence-pill">
                    AI Confidence: {(extractionData.fields.invoice_number.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>

            <div className="form-field">
              <label htmlFor="input-vendor-name">Vendor Name *</label>
              <input
                id="input-vendor-name"
                type="text"
                value={vendorName}
                onChange={(e) => setVendorName(e.target.value)}
                placeholder="e.g. Aster Office Supplies"
                required
              />
              {extractionData?.fields?.vendor_name && (
                <div className="field-meta-row">
                  <span className={`evidence-badge ${extractionData.fields.vendor_name.evidence_verified ? "verified" : "unverified"}`}>
                    {extractionData.fields.vendor_name.evidence_verified ? "✓ Evidence Verified" : "⚠ Unverified Quote"}
                  </span>
                  <span className="confidence-pill">
                    AI Confidence: {(extractionData.fields.vendor_name.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>

            <div className="form-field">
              <label htmlFor="input-po-number">PO Number *</label>
              <input
                id="input-po-number"
                type="text"
                value={poNumber}
                onChange={(e) => setPoNumber(e.target.value)}
                placeholder="e.g. PO-1001"
                required
              />
              {extractionData?.fields?.po_number && (
                <div className="field-meta-row">
                  <span className={`evidence-badge ${extractionData.fields.po_number.evidence_verified ? "verified" : "unverified"}`}>
                    {extractionData.fields.po_number.evidence_verified ? "✓ Evidence Verified" : "⚠ Unverified Quote"}
                  </span>
                  <span className="confidence-pill">
                    AI Confidence: {(extractionData.fields.po_number.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>

            <div className="form-row-2">
              <div className="form-field">
                <label htmlFor="input-total">Total Amount (₹) *</label>
                <input
                  id="input-total"
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={invoiceTotal}
                  onChange={(e) => setInvoiceTotal(e.target.value)}
                  placeholder="85000.00"
                  required
                />
                {extractionData?.fields?.invoice_total && (
                  <div className="field-meta-row">
                    <span className={`evidence-badge ${extractionData.fields.invoice_total.evidence_verified ? "verified" : "unverified"}`}>
                      {extractionData.fields.invoice_total.evidence_verified ? "✓ Verified" : "⚠ Unverified"}
                    </span>
                    <span className="confidence-pill">
                      AI: {(extractionData.fields.invoice_total.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>

              <div className="form-field">
                <label htmlFor="input-gst">GST Amount (₹) *</label>
                <input
                  id="input-gst"
                  type="number"
                  step="0.01"
                  min="0"
                  value={gstAmount}
                  onChange={(e) => setGstAmount(e.target.value)}
                  placeholder="12966.10"
                  required
                />
                {extractionData?.fields?.gst_amount && (
                  <div className="field-meta-row">
                    <span className={`evidence-badge ${extractionData.fields.gst_amount.evidence_verified ? "verified" : "unverified"}`}>
                      {extractionData.fields.gst_amount.evidence_verified ? "✓ Verified" : "⚠ Unverified"}
                    </span>
                    <span className="confidence-pill">
                      AI: {(extractionData.fields.gst_amount.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="form-row-2">
              <div className="form-field">
                <label htmlFor="input-items">Line Items *</label>
                <input
                  id="input-items"
                  type="number"
                  step="1"
                  min="1"
                  value={lineItems}
                  onChange={(e) => setLineItems(e.target.value)}
                  placeholder="5"
                  required
                />
                {extractionData?.fields?.line_items && (
                  <div className="field-meta-row">
                    <span className={`evidence-badge ${extractionData.fields.line_items.evidence_verified ? "verified" : "unverified"}`}>
                      {extractionData.fields.line_items.evidence_verified ? "✓ Verified" : "⚠ Unverified"}
                    </span>
                    <span className="confidence-pill">
                      AI: {(extractionData.fields.line_items.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>

              <div className="form-field">
                <label htmlFor="input-bank-ref">Bank Account Ref</label>
                <input
                  id="input-bank-ref"
                  type="text"
                  value={bankAccountRef}
                  onChange={(e) => setBankAccountRef(e.target.value)}
                  placeholder="e.g. ACCT-1001"
                />
                {extractionData?.fields?.invoice_bank_account_ref && (
                  <div className="field-meta-row">
                    <span className={`evidence-badge ${extractionData.fields.invoice_bank_account_ref.evidence_verified ? "verified" : "unverified"}`}>
                      {extractionData.fields.invoice_bank_account_ref.evidence_verified ? "✓ Verified" : "⚠ Unverified"}
                    </span>
                    <span className="confidence-pill">
                      AI: {(extractionData.fields.invoice_bank_account_ref.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>

            <button
              className="action-button"
              type="submit"
              disabled={loading || loadingBaselines}
              style={{ marginTop: "10px", width: "100%" }}
            >
              {loadingBaselines ? "Loading trusted baselines..." : loading ? "Verifying against server..." : "Review and Verify Invoice"}
            </button>
            <div style={{ textAlign: "center", fontSize: "11px", color: "var(--muted)", marginTop: "4px" }}>
              Press <strong>Ctrl+Enter</strong> to verify quickly
            </div>
          </form>
        </aside>

        {/* =========================================================================
            CENTER PANE: Evidence Comparison & Discrepancy Presentation
            ========================================================================= */}
        <section className="verification-pane center-pane">
          <div className="panel-header">
            <span style={{ fontWeight: 700, fontSize: "14px" }}>Evidence Comparison</span>
            <span className="soft-tag neutral">
              {matchedPO ? `Baseline: ${matchedPO.po_number}` : trimmedPo ? "PO Unmatched" : "Awaiting PO"}
            </span>
          </div>

          {/* Missing Required Fields Alert */}
          {missingFields.length > 0 && (
            <div
              style={{
                border: "1px solid rgba(184, 117, 25, 0.3)",
                background: "var(--amber-soft)",
                color: "var(--amber)",
                borderRadius: "10px",
                padding: "10px 12px",
                fontSize: "12px",
                marginBottom: "14px",
              }}
            >
              <strong>Missing Required Fields:</strong>
              <div style={{ marginTop: "4px" }}>{missingFields.join(", ")}</div>
            </div>
          )}

          {/* Condition 1: No PO Entered -> Meaningful Zero State */}
          {!trimmedPo ? (
            <div style={{ padding: "48px 20px", textAlign: "center" }}>
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  borderRadius: "50%",
                  background: "var(--surface-soft)",
                  display: "grid",
                  placeItems: "center",
                  margin: "0 auto 14px",
                  color: "var(--muted)",
                }}
              >
                <Icon name="file" />
              </div>
              <strong style={{ display: "block", fontSize: "15px", marginBottom: "8px" }}>
                Awaiting Purchase Order Baseline
              </strong>
              <p style={{ fontSize: "13px", color: "var(--muted)", maxWidth: "360px", margin: "0 auto", lineHeight: 1.6 }}>
                Enter or select a PO number (e.g. <strong>PO-1001</strong>) in the intake form. FinTrust AI compares invoice values against authorized records stored in the database.
              </p>
            </div>
          ) : !matchedPO && !verification ? (
            /* Condition 2: PO entered but not found in DB */
            <div style={{ padding: "32px 16px" }}>
              <div
                style={{
                  border: "1px solid rgba(166, 64, 59, 0.3)",
                  background: "var(--red-soft)",
                  color: "var(--red)",
                  borderRadius: "12px",
                  padding: "16px",
                  fontSize: "13px",
                  lineHeight: 1.6,
                }}
              >
                <strong>Unrecognized Purchase Order: {poNumber}</strong>
                <p style={{ margin: "8px 0 0", color: "var(--text)" }}>
                  This PO number does not exist in the active SQLite database. Invoices referencing unregistered purchase orders cannot be approved by the verification engine.
                </p>
                <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--muted)" }}>
                  Available active POs: {trustedPOs.map((p) => p.po_number).join(", ") || "PO-1001, PO-1002, PO-1003"}
                </div>
              </div>
            </div>
          ) : (
            /* Condition 3: Matched PO baseline available */
            <>
              <div className="comparison-group">
                <h3>Trusted vendor record</h3>
                <ul>
                  <li>
                    <span>Vendor name</span>
                    <strong>{trustedVendorName ?? "Queried from database via PO"}</strong>
                  </li>
                  <li>
                    <span>Vendor code</span>
                    <strong>{matchedPO?.vendor_code ?? (verification ? "Not resolved" : "—")}</strong>
                  </li>
                  <li>
                    <span>Trusted Account Ref</span>
                    <strong>{trustedBankRef ? (trustedBankRef.length > 4 ? `•••• •••• ${trustedBankRef.slice(-4)}` : trustedBankRef) : "—"}</strong>
                  </li>
                  <li>
                    <span>Account Verification</span>
                    <strong style={{ fontSize: "11px", color: bankMatched ? "var(--green)" : bankMatched === false ? "var(--red)" : "var(--muted)" }}>
                      {bankMatched === true ? "✓ Reference Matched" : bankMatched === false ? "⚠ Reference Mismatch" : "Awaiting Verification"}
                    </strong>
                  </li>
                </ul>
              </div>

              <div className="comparison-group">
                <h3>Purchase order baseline</h3>
                <ul>
                  <li>
                    <span>PO Identifier</span>
                    <strong>{matchedPO?.po_number ?? poNumber}</strong>
                  </li>
                  <li>
                    <span>Approved value</span>
                    <strong>
                      {approvedTotalRupees != null
                        ? `₹${approvedTotalRupees.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                        : "—"}
                    </strong>
                  </li>
                  <li>
                    <span>Approved GST</span>
                    <strong>
                      {approvedGstRupees != null
                        ? `₹${approvedGstRupees.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                        : "—"}
                    </strong>
                  </li>
                  <li>
                    <span>Approved items</span>
                    <strong>{approvedItemsCount != null ? `${approvedItemsCount} item(s)` : "—"}</strong>
                  </li>
                </ul>
              </div>

              {/* Side-by-Side Reconciliation Table with Exact Variances */}
              <div className="comparison-table">
                <div className="table-row table-head">
                  <span>Field</span>
                  <span>Invoice</span>
                  <span>Approved</span>
                  <span>Variance / Match</span>
                </div>

                {/* Row 1: Total Amount */}
                <div className="table-row">
                  <span>Total amount</span>
                  <span>₹{parsedInvoiceTotal.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  <span>
                    {approvedTotalRupees != null
                      ? `₹${approvedTotalRupees.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                      : "—"}
                  </span>
                  <span
                    className={`variance ${
                      amountVariance == null
                        ? ""
                        : Math.abs(amountVariance) < 0.01
                        ? ""
                        : "alert"
                    }`}
                    style={amountVariance != null && Math.abs(amountVariance) < 0.01 ? { color: "var(--green)" } : undefined}
                  >
                    {amountVariance == null
                      ? "—"
                      : Math.abs(amountVariance) < 0.01
                      ? "₹0.00 exact"
                      : amountVariance > 0
                      ? `+₹${amountVariance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                      : `-₹${Math.abs(amountVariance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
                  </span>
                </div>

                {/* Row 2: GST Value */}
                <div className="table-row">
                  <span>GST value</span>
                  <span>₹{parsedGstAmount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>
                  <span>
                    {approvedGstRupees != null
                      ? `₹${approvedGstRupees.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                      : "—"}
                  </span>
                  <span
                    className={`variance ${
                      gstVariance == null
                        ? ""
                        : Math.abs(gstVariance) < 0.01
                        ? ""
                        : "warning"
                    }`}
                    style={gstVariance != null && Math.abs(gstVariance) < 0.01 ? { color: "var(--green)" } : undefined}
                  >
                    {gstVariance == null
                      ? "—"
                      : Math.abs(gstVariance) < 0.01
                      ? "₹0.00 exact"
                      : gstVariance > 0
                      ? `+₹${gstVariance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
                      : `-₹${Math.abs(gstVariance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`}
                  </span>
                </div>

                {/* Row 3: Line Items */}
                <div className="table-row">
                  <span>Line items</span>
                  <span>{parsedLineItems || "—"}</span>
                  <span>{approvedItemsCount ?? "—"}</span>
                  <span
                    className={`variance ${
                      lineItemsVariance == null
                        ? ""
                        : lineItemsVariance === 0
                        ? ""
                        : "alert"
                    }`}
                    style={lineItemsVariance === 0 ? { color: "var(--green)" } : undefined}
                  >
                    {lineItemsVariance == null
                      ? "—"
                      : lineItemsVariance === 0
                      ? "Exact count"
                      : lineItemsVariance > 0
                      ? `+${lineItemsVariance} items`
                      : `${lineItemsVariance} items`}
                  </span>
                </div>

                {/* Row 4: Vendor Identity */}
                <div className="table-row">
                  <span>Vendor identity</span>
                  <span style={{ fontSize: "11px" }}>{vendorName || "—"}</span>
                  <span style={{ fontSize: "11px" }}>{trustedVendorName ?? "—"}</span>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: vendorMatched ? "var(--green)" : "var(--red)" }}>
                    {vendorMatched == null ? "—" : vendorMatched ? "✓ Matched" : "⚠ Mismatch"}
                  </span>
                </div>

                {/* Row 5: Bank Account Reference */}
                <div className="table-row">
                  <span>Account Ref</span>
                  <span style={{ fontSize: "11px" }}>{bankAccountRef || "None"}</span>
                  <span style={{ fontSize: "11px" }}>{trustedBankRef ?? "None"}</span>
                  <span style={{ fontSize: "11px", fontWeight: 700, color: bankMatched ? "var(--green)" : "var(--red)" }}>
                    {bankMatched == null ? "—" : bankMatched ? "✓ Matched" : "⚠ Mismatch"}
                  </span>
                </div>
              </div>

              {/* Source Citation */}
              <div style={{ marginTop: "12px", fontSize: "11px", color: "var(--muted)" }}>
                Baseline Source: SQLite Database Record (PO: {matchedPO?.po_number ?? poNumber} • Vendor ID #{matchedPO?.vendor_id ?? "1"})
              </div>

              {/* Discrepancy Presentation Card (Plain English + Recommended Next Action) */}
              {((amountVariance != null && Math.abs(amountVariance) >= 0.01) ||
                (gstVariance != null && Math.abs(gstVariance) >= 0.01) ||
                (lineItemsVariance != null && lineItemsVariance !== 0) ||
                vendorMatched === false ||
                bankMatched === false) && (
                <div
                  style={{
                    border: "1px solid rgba(184, 117, 25, 0.4)",
                    borderRadius: "12px",
                    background: "rgba(184, 117, 25, 0.06)",
                    padding: "14px 16px",
                    marginTop: "16px",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "10px" }}>
                    <Icon name="risk" />
                    <strong style={{ fontSize: "13px", color: "var(--text)" }}>
                      Discrepancy Analysis & Next Review Actions
                    </strong>
                  </div>
                  <div style={{ display: "grid", gap: "10px", fontSize: "12px" }}>
                    {amountVariance != null && Math.abs(amountVariance) >= 0.01 && (
                      <div style={{ padding: "8px 10px", background: "var(--surface)", borderRadius: "8px", border: "1px solid var(--line)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
                          <span style={{ color: "var(--red)", fontWeight: 700 }}>
                            Total Amount Variance: {amountVariance > 0 ? `+₹${amountVariance.toFixed(2)}` : `-₹${Math.abs(amountVariance).toFixed(2)}`}
                          </span>
                          <span style={{ color: "var(--muted)" }}>
                            Invoice: ₹{parsedInvoiceTotal.toFixed(2)} vs PO: ₹{approvedTotalRupees?.toFixed(2)}
                          </span>
                        </div>
                        <p style={{ margin: "2px 0 4px", color: "var(--text)" }}>
                          The invoice exceeds the approved purchase order by ₹{Math.abs(amountVariance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}.
                        </p>
                        <span style={{ color: "var(--green)", fontWeight: 600, fontSize: "11px" }}>
                          Recommended action: Request revised invoice from vendor or obtain PO amendment authorization.
                        </span>
                      </div>
                    )}

                    {gstVariance != null && Math.abs(gstVariance) >= 0.01 && (
                      <div style={{ padding: "8px 10px", background: "var(--surface)", borderRadius: "8px", border: "1px solid var(--line)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
                          <span style={{ color: "var(--amber)", fontWeight: 700 }}>
                            GST Tax Variance: {gstVariance > 0 ? `+₹${gstVariance.toFixed(2)}` : `-₹${Math.abs(gstVariance).toFixed(2)}`}
                          </span>
                          <span style={{ color: "var(--muted)" }}>
                            Invoice: ₹{parsedGstAmount.toFixed(2)} vs PO: ₹{approvedGstRupees?.toFixed(2)}
                          </span>
                        </div>
                        <p style={{ margin: "2px 0 4px", color: "var(--text)" }}>
                          The submitted GST differs from the approved tax baseline by ₹{Math.abs(gstVariance).toLocaleString("en-IN", { minimumFractionDigits: 2 })}.
                        </p>
                        <span style={{ color: "var(--green)", fontWeight: 600, fontSize: "11px" }}>
                          Recommended action: Verify HSN/SAC tax slab computation with vendor billing department.
                        </span>
                      </div>
                    )}

                    {lineItemsVariance != null && lineItemsVariance !== 0 && (
                      <div style={{ padding: "8px 10px", background: "var(--surface)", borderRadius: "8px", border: "1px solid var(--line)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "2px" }}>
                          <span style={{ color: "var(--amber)", fontWeight: 700 }}>
                            Line Items Difference: {lineItemsVariance > 0 ? `+${lineItemsVariance}` : `${lineItemsVariance}`} item(s)
                          </span>
                          <span style={{ color: "var(--muted)" }}>
                            Invoice: {parsedLineItems} vs PO: {approvedItemsCount}
                          </span>
                        </div>
                        <p style={{ margin: "2px 0 4px", color: "var(--text)" }}>
                          The invoice lists {parsedLineItems} items while the approved PO authorizes {approvedItemsCount} item(s).
                        </p>
                        <span style={{ color: "var(--green)", fontWeight: 600, fontSize: "11px" }}>
                          Recommended action: Confirm delivery note to determine if this is an unauthorized item addition or partial shipment.
                        </span>
                      </div>
                    )}

                    {vendorMatched === false && (
                      <div style={{ padding: "8px 10px", background: "var(--surface)", borderRadius: "8px", border: "1px solid var(--line)" }}>
                        <span style={{ color: "var(--red)", fontWeight: 700, display: "block", marginBottom: "2px" }}>
                          Vendor Identity Mismatch
                        </span>
                        <p style={{ margin: "2px 0 4px", color: "var(--text)" }}>
                          Invoice vendor &lsquo;{vendorName}&rsquo; does not match the vendor recorded on the PO (&lsquo;{trustedVendorName}&rsquo;).
                        </p>
                        <span style={{ color: "var(--red)", fontWeight: 600, fontSize: "11px" }}>
                          Recommended action: Hold payment immediately. Confirm vendor identity and legal contracting entity.
                        </span>
                      </div>
                    )}

                    {bankMatched === false && (
                      <div style={{ padding: "8px 10px", background: "var(--surface)", borderRadius: "8px", border: "1px solid var(--line)" }}>
                        <span style={{ color: "var(--red)", fontWeight: 700, display: "block", marginBottom: "2px" }}>
                          Bank Account Reference Discrepancy
                        </span>
                        <p style={{ margin: "2px 0 4px", color: "var(--text)" }}>
                          Invoice remittance reference &lsquo;{bankAccountRef}&rsquo; does not match the trusted master record (&lsquo;{trustedBankRef}&rsquo;).
                        </p>
                        <span style={{ color: "var(--red)", fontWeight: 600, fontSize: "11px" }}>
                          Recommended action: Contact supplier via authorized offline channel to verify account number and prevent invoice redirection fraud.
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Supporting Evidence Presentation with Quotes & AI Confidence */}
              {extractionData?.fields && (
                <div className="comparison-group" style={{ marginTop: "16px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                    <h3>Supporting Evidence & Source Quotes</h3>
                    <span style={{ fontSize: "10px", color: "var(--muted)" }}>AI confidence is a heuristic estimate, not proof of correctness</span>
                  </div>
                  <div style={{ display: "grid", gap: "8px" }}>
                    {Object.entries(extractionData.fields).map(([fieldName, fieldData]) => (
                      <div
                        key={fieldName}
                        style={{
                          padding: "10px 12px",
                          background: "var(--surface)",
                          border: "1px solid var(--line)",
                          borderRadius: "8px",
                          fontSize: "12px",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                          <strong>{fieldName.replace(/_/g, " ").toUpperCase()}</strong>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                            <span className={`evidence-badge ${fieldData.evidence_verified ? "verified" : "unverified"}`}>
                              {fieldData.evidence_verified ? "✓ Verified in Text" : "⚠ Unverified Quote"}
                            </span>
                            <span className="confidence-pill">
                              AI Estimate: {(fieldData.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--text)", marginBottom: "2px" }}>
                          Extracted Value: <strong>{fieldData.value != null ? String(fieldData.value) : "Not found"}</strong>
                        </div>
                        <div style={{ fontSize: "11px", color: "var(--muted)", fontStyle: "italic" }}>
                          Quote: {fieldData.evidence_quote ? `“${fieldData.evidence_quote}”` : "No direct quote cited"} • Page {fieldData.page_number ?? 1}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </section>

        {/* =========================================================================
            RIGHT PANE: Verification Findings
            ========================================================================= */}
        <aside className="verification-pane">
          <div className="panel-header">
            <span style={{ fontWeight: 700, fontSize: "14px" }}>Verification Findings</span>
            <span className={stateBadges[currentWorkflowState].className}>
              {stateBadges[currentWorkflowState].text}
            </span>
          </div>

          {/* Decision Banner */}
          {verification ? (
            <div
              className={`decision-banner ${
                verification.decision === "APPROVE"
                  ? "approve"
                  : verification.decision === "HOLD"
                  ? "hold"
                  : "block"
              }`}
            >
              <div>
                <strong style={{ fontSize: "15px" }}>Decision: {verification.decision}</strong>
                <div style={{ fontSize: "11px", marginTop: "3px" }}>
                  Risk level: {verification.risk_level.toUpperCase()}
                  {verification.invoice_id != null && ` • Invoice #${verification.invoice_id}`}
                  {verification.audit_event_id != null && ` • Audit Event #${verification.audit_event_id}`}
                </div>
              </div>
            </div>
          ) : (
            <div
              style={{
                border: "1px solid var(--line)",
                borderRadius: "12px",
                background: "var(--surface)",
                padding: "14px",
                marginBottom: "14px",
                fontSize: "12px",
              }}
            >
              <strong style={{ display: "block", marginBottom: "4px" }}>Awaiting Verification Submission</strong>
              <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.5 }}>
                Review the intake fields and trusted baseline. Click <strong>Review and Verify Invoice</strong> (or press Ctrl+Enter) to evaluate deterministic verification rules against the server database.
              </p>
            </div>
          )}

          {/* Findings Stack */}
          <div className="findings-block">
            {!verification ? (
              <div className="finding-row">
                <span className="risk-dot amber" />
                <div>
                  <strong>Deterministic Verification Standby</strong>
                  <p>Server-side database checks will verify vendor identity, amount limits, GST calculations, and line item counts upon submission.</p>
                </div>
              </div>
            ) : findings.length === 0 ? (
              <div className="finding-row">
                <span className="risk-dot green" />
                <div>
                  <strong>All evidence checks matched</strong>
                  <p>The invoice matches the trusted vendor and purchase order records. Deterministic decision is APPROVE.</p>
                </div>
              </div>
            ) : (
              findings.map((finding) => (
                <div className="finding-row" key={`${finding.title}-${finding.detail}`}>
                  <span
                    className={`risk-dot ${
                      finding.level === "high" ? "red" : finding.level === "medium" ? "amber" : "green"
                    }`}
                  />
                  <div>
                    <strong>{finding.title}</strong>
                    <p>{finding.detail}</p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Investigation Outcome Next Steps */}
          <div className="next-action-box" style={{ marginTop: "16px" }}>
            <h3>Investigation outcome</h3>
            <p>
              {verification?.decision === "APPROVE"
                ? `Invoice #${verification.invoice_id} successfully approved and stored in database. Audit event #${verification.audit_event_id} appended to immutable ledger.`
                : verification?.decision === "HOLD"
                ? "Discrepancies identified against trusted server records. Financial human review is required before release."
                : verification?.decision === "BLOCK"
                ? "Critical discrepancy or unknown purchase order. Transaction blocked from automated payment approval."
                : "Submit the form to execute database-backed verification rules."}
            </p>
          </div>

          {/* Regulatory & Security Invariants Note */}
          <div className="status-note" style={{ marginTop: "14px" }}>
            <strong>Trusted server policy</strong>
            <span>
              Values extracted by AI or supplied by the client are never trusted unconditionally. All reconciliation is executed against verified database records.
            </span>
          </div>
        </aside>
      </div>
    </section>
  );
}
