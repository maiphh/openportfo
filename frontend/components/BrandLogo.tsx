import Link from "next/link";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden>
      <rect x="1" y="1" width="30" height="30" rx="8" fill="#141414" stroke="#30333A" />
      <path d="M8 23 L16 7 L24 23" fill="none" stroke="#F4F7F7" strokeWidth="2.4" strokeLinejoin="round" />
      <path d="M11.4 16.6 H20.6" stroke="#0FEDBE" strokeWidth="2.4" strokeLinecap="round" />
      <path d="M16 23 V27" stroke="#0FEDBE" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function BrandLogo() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <BrandMark className="h-8 w-8" />
      <span className="text-[22px] font-semibold tracking-tight text-gray-100">OpenPortfo</span>
    </Link>
  );
}
