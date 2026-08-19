import { logoFor } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export default function CompanyLogo({
  symbol,
  size = 22,
  className,
}: {
  symbol: string;
  size?: number;
  className?: string;
}) {
  const logo = logoFor(symbol);
  const mark = logo.mark || symbol.slice(0, 1);
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold leading-none",
        className,
      )}
      style={{
        width: size,
        height: size,
        background: logo.bg,
        color: logo.fg,
        fontSize: size < 18 ? 8 : size < 24 ? 9 : 11,
      }}
      aria-hidden
    >
      {symbol === "AAPL" ? (
        <svg viewBox="0 0 24 24" width={size * 0.62} height={size * 0.62} fill="currentColor">
          <path d="M16.2 12.3c0-2.3 1.9-3.4 2-3.5-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.2-2.8.8-3.5.8s-1.8-.8-3-.8c-1.5 0-3 .9-3.8 2.3-1.6 2.8-.4 7 1.2 9.3.8 1.1 1.7 2.3 2.9 2.3 1.2 0 1.6-.7 3-.7s1.8.7 3 .7 2-.1 2.9-2.3c.7-1.2 1-2.3 1-2.4-.1 0-2.3-.9-2.3-3.9zM14.4 6.4c.6-.8 1.1-1.9.9-3-1 .1-2.1.7-2.8 1.5-.6.7-1.2 1.8-1 2.9 1.1.1 2.2-.5 2.9-1.4z" />
        </svg>
      ) : (
        mark
      )}
    </span>
  );
}
