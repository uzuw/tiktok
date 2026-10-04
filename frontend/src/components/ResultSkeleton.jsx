import "./ResultSkeleton.css";

/**
 * Placeholder shown while /resolve runs — mirrors the result card's geometry so
 * the layout doesn't shift when the real card arrives.
 */
export default function ResultSkeleton() {
  return (
    <div className="result-skeleton panel" role="status" aria-live="polite">
      <div className="result-skeleton-body">
        <div className="skeleton sk-thumb" />
        <div className="sk-meta">
          <div className="skeleton sk-line sk-line--xs" />
          <div className="skeleton sk-line sk-line--lg" />
          <div className="skeleton sk-line" />
          <div className="skeleton sk-line sk-line--sm" />
        </div>
      </div>
      <span className="sr-only">Fetching video details…</span>
    </div>
  );
}
