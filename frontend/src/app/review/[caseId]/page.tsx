/**
 * Client-side case detail page for reviewing and deciding a pending case.
 */

"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getCase, reviewCase, CaseDetail } from "@/lib/api";

/**
 * Loads a case and renders its transaction and investigator proposal, with
 * approve/reject controls that submit the reviewer's decision.
 */
export default function CaseDetailPage() {
  const { caseId } = useParams<{ caseId: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [reviewerRole, setReviewerRole] = useState("accountant");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getCase(caseId).then(setDetail).catch((e) => setError(String(e))); }, [caseId]);

  if (error) return <main className="p-8 text-red-600">{error}</main>;
  if (!detail) return <main className="p-8">Loading…</main>;

  const review = detail.state.pending_review;
  const disposition = review?.proposed_disposition;

  /**
   * Submit an approve/reject decision and navigate back to the queue.
   */
  async function submit(decision: "approve" | "reject") {
    setSubmitting(true);
    try {
      await reviewCase(caseId, decision, reviewerRole, decision === "reject" ? reason : undefined);
      router.push("/review");
    } catch (e) { setError(String(e)); } finally { setSubmitting(false); }
  }

  return (
    <main className="max-w-2xl mx-auto p-8 space-y-6">
      <h1 className="text-xl font-semibold font-mono">{caseId}</h1>
      <section className="rounded-lg border p-4 space-y-1">
        <h2 className="font-medium">Transaction</h2>
        <pre className="text-sm bg-gray-50 p-2 rounded overflow-x-auto">{JSON.stringify(detail.state.transaction, null, 2)}</pre>
      </section>
      {disposition && (
        <section className="rounded-lg border p-4 space-y-2">
          <h2 className="font-medium">Investigator's proposal</h2>
          <p><span className="text-gray-500">Disposition:</span> <span className="font-mono">{disposition.disposition}</span></p>
          <p><span className="text-gray-500">Confidence:</span> {disposition.confidence}</p>
          <p className="text-sm">{disposition.explanation}</p>
          {review && review.rejection_cycle_count > 0 && (
            <p className="text-sm text-amber-600">Rejection cycle {review.rejection_cycle_count} — sent back for re-investigation before.</p>
          )}
        </section>
      )}
      <section className="space-y-3">
        <label className="block"><span className="text-sm text-gray-500">Reviewer role</span>
          <input className="mt-1 block w-full rounded-md border px-3 py-2" value={reviewerRole} onChange={(e) => setReviewerRole(e.target.value)} />
        </label>
        <label className="block"><span className="text-sm text-gray-500">Reason (required if rejecting)</span>
          <textarea className="mt-1 block w-full rounded-md border px-3 py-2" value={reason} onChange={(e) => setReason(e.target.value)} />
        </label>
        <div className="flex gap-3">
          <button disabled={submitting} onClick={() => submit("approve")} className="rounded-md bg-black text-white px-4 py-2 disabled:opacity-50">Approve</button>
          <button disabled={submitting || !reason} onClick={() => submit("reject")} className="rounded-md border px-4 py-2 disabled:opacity-50">Reject</button>
        </div>
      </section>
    </main>
  );
}
