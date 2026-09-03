// frontend/src/app/review/page.tsx
import Link from "next/link";
import { listCases } from "@/lib/api";

export default async function ReviewQueuePage() {
  const cases = await listCases("pending_review");
  return (
    <main className="max-w-3xl mx-auto p-8 space-y-4">
      <h1 className="text-xl font-semibold">Pending review ({cases.length})</h1>
      {cases.length === 0 && <p className="text-gray-500">Nothing pending.</p>}
      <ul className="divide-y">
        {cases.map((c) => (
          <li key={c.case_id} className="py-3">
            <Link href={`/review/${c.case_id}`} className="font-mono hover:underline">{c.case_id}</Link>
            <span className="ml-3 text-sm text-gray-500">updated {new Date(c.updated_at * 1000).toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </main>
  );
}