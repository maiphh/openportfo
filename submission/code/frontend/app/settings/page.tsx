import { Suspense } from "react";
import SettingsPageClient from "@/components/settings/SettingsPageClient";
import SettingsPageSkeleton from "@/components/settings/SettingsPageSkeleton";

export default function SettingsPage() {
  return (
    <Suspense fallback={<SettingsPageSkeleton />}>
      <SettingsPageClient />
    </Suspense>
  );
}

