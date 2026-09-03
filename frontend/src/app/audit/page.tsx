// frontend/src/app/audit/page.tsx
"use client";
import { useEffect, useState } from "react";
import { listAuditLog, AuditEvent } from "@/lib/api";

export default function AuditLogPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  useEffect(() => { listAuditLog().then(setEvents); }, []);
  return (
    <main className="max-w-4xl mx-auto p-8 space-y-4">
      <h1 className="text-xl font-semibold">Audit log — hash chain</h1>
      <p className="text-sm text-gray-500">Verified server-side, with the exact function that wrote each hash.</p>
      <table className="w-full text-sm border-collapse">
        <thead><tr className="text-left border-b"><th className="py-2">#</th><th>Event</th><th>Case</th><th>Hash</th><th>Verified</th></tr></thead>
        <tbody>
          {events.map((e) => (
            <tr key={e.id} className="border-b">
              <td className="py-2">{e.id}</td><td>{e.event_type}</td>
              <td className="font-mono">{e.case_id}</td>
              <td className="font-mono text-xs">{e.event_hash.slice(0, 12)}…</td>
              <td>{e.verified ? "✅" : "❌"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}