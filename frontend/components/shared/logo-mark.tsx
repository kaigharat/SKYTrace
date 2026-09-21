import { cn } from "@/lib/utils";

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={cn("size-6", className)}
    >
      <rect width="32" height="32" rx="8" className="fill-primary" />
      <circle cx="10" cy="11" r="2.4" fill="white" fillOpacity="0.95" />
      <circle cx="22" cy="9" r="2" fill="white" fillOpacity="0.75" />
      <circle cx="22" cy="22" r="2.4" fill="white" fillOpacity="0.95" />
      <circle cx="10" cy="21" r="1.8" fill="white" fillOpacity="0.6" />
      <path
        d="M10 11 L22 9 M10 11 L22 22 M10 11 L10 21 M22 22 L10 21"
        stroke="white"
        strokeOpacity="0.55"
        strokeWidth="1.2"
      />
    </svg>
  );
}
