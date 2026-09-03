// frontend/src/lib/api.ts
const ORCH = process.env.NEXT_PUBLIC_ORCHESTRATION_API;
const ERP = process.env.NEXT_PUBLIC_ERP_API;

export type CaseSummary = { case_id: string; status: string; updated_at: number };
export type CaseDetail = {
  case_id: string;
  state: {
    transaction: Record<string, any>;
    pending_review?: { proposed_disposition: { confidence: number; explanation: string; disposition: string }; rejection_cycle_count: number };
    case_status?: string;
  };
  next_nodes: string[];
};
export type AuditEvent = {
  id: number; event_type: string; case_id: string; journal_entry_id: string | null;
  payload: Record<string, any>; previous_event_hash: string; event_hash: string; created_at: number; verified: boolean;
};
export type DashboardSummary = { baseline: any; agent: any; comparison: any };

export async function listCases(status?: string): Promise<CaseSummary[]> {
  const res = await fetch(status ? `${ORCH}/cases?status=${status}` : `${ORCH}/cases`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to list cases: ${res.status}`);
  return res.json();
}
export async function getCase(caseId: string): Promise<CaseDetail> {
  const res = await fetch(`${ORCH}/cases/${caseId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch case: ${res.status}`);
  return res.json();
}
export async function reviewCase(caseId: string, decision: "approve" | "reject", reviewerRole: string, reason?: string) {
  const res = await fetch(`${ORCH}/cases/${caseId}/review`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, reviewer_role: reviewerRole, reason }),
  });
  if (!res.ok) throw new Error(`Failed to submit review: ${res.status}`);
  return res.json();
}
export async function listAuditLog(caseId?: string): Promise<AuditEvent[]> {
  const res = await fetch(caseId ? `${ERP}/audit-log?case_id=${caseId}` : `${ERP}/audit-log`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch audit log: ${res.status}`);
  return res.json();
}
export async function getDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch(`${ORCH}/dashboard/summary`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch dashboard summary: ${res.status}`);
  return res.json();
}