/**
 * SaveTok mark — a rounded badge with a downward arrow. Drawn as strokes in
 * currentColor so it works on paper and on ink without a second colour.
 */
export default function BrandMark({ size = 24, className = "" }) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="1.55" y="1.55" width="20.9" height="20.9" rx="6.5" />
      <path d="M12 7.4v8.2" />
      <path d="m15.1 12.4-3.1 3.2-3.1-3.2" />
    </svg>
  );
}
