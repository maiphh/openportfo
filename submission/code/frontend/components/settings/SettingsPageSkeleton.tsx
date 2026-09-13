export default function SettingsPageSkeleton() {
  return (
    <div aria-busy="true" className="mx-auto max-w-5xl animate-pulse space-y-6 px-4">
      <div className="h-8 w-48 rounded bg-gray-700" />
      <div className="h-24 rounded-xl border border-gray-700 bg-gray-800" />
      <div className="h-64 rounded-xl border border-gray-700 bg-gray-800" />
    </div>
  );
}

