import { Suspense } from "react";
import AdminPageClient from "@/components/admin/AdminPageClient";

function AdminSkeleton() {
  return <div aria-busy="true" className="mx-auto max-w-6xl animate-pulse px-4"><div className="h-8 w-48 rounded bg-gray-700" /><div className="mt-6 h-72 rounded bg-gray-800" /></div>;
}

export default function AdminPage() {
  return <Suspense fallback={<AdminSkeleton />}><AdminPageClient /></Suspense>;
}

