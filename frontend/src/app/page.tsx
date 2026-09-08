/**
 * Dashboard landing page showing held-out benchmark metrics.
 */

import Link from "next/link";
import { getDashboardSummary } from "@/lib/api";

/**
 * Fetches and renders the dashboard summary metrics.
 */
export default async function DashboardPage() {
  const { baseline, agent, comparison } = await getDashboardSummary();
  return (
    <main className="max-w-4xl mx-auto p-8 space-y-8">
      <h1 className="text-2xl font-semibold">Financial Reconciliation Agent</h1>
      <p className="text-gray-600">Held-out benchmark — synthetic data, mock ERP.</p>
      <div className="grid grid-cols-2 gap-4">
        <Metric label="Baseline F1" value={baseline?.f1?.toFixed(3) ?? "—"} />
        <Metric label="Agent F1" value={agent?.f1?.toFixed(3) ?? "—"} />
        <Metric label="Correct disposition rate" value={agent?.correct_disposition_rate?.toFixed(3) ?? "—"} />
        <Metric label="% fewer manual touches" value={comparison?.pct_fewer_manual_touches != null ? `${(comparison.pct_fewer_manual_touches * 100).toFixed(1)}%` : "—"} />
        <Metric label="Avg cost / transaction" value={agent?.avg_cost_per_transaction_usd != null ? `$${agent.avg_cost_per_transaction_usd.toFixed(4)}` : "—"} />
        <Metric label="Avg latency / investigated case" value={agent?.avg_latency_per_investigated_case_s != null ? `${agent.avg_latency_per_investigated_case_s.toFixed(1)}s` : "—"} />
      </div>
      <div className="flex gap-4">
        <Link href="/review" className="rounded-md bg-black text-white px-4 py-2">Review queue</Link>
        <Link href="/audit" className="rounded-md border px-4 py-2">Audit log</Link>
      </div>
    </main>
  );
}

/**
 * Renders a single labeled metric value in a bordered card.
 */
function Metric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border p-4"><div className="text-sm text-gray-500">{label}</div><div className="text-xl font-mono">{value}</div></div>;
}
