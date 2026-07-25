import { useId, useState } from "react";
import { FiArrowDown, FiLink, FiLoader } from "react-icons/fi";

export default function SearchBar({ onResolve, loading }) {
  const [url, setUrl] = useState("");
  const hintId = useId();

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onResolve(trimmed);
  };

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <div className="search-input-wrap">
        <FiLink className="search-icon" size={16} aria-hidden="true" />
        <input
          type="url"
          className="search-input"
          placeholder="https://www.tiktok.com/@user/video/..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          aria-describedby={hintId}
          autoFocus
        />
      </div>

      <button
        className="search-btn"
        type="submit"
        disabled={loading || !url.trim()}
        aria-label={loading ? "Resolving video" : "Resolve video"}
      >
        {loading ? <FiLoader className="spin" size={18} /> : <FiArrowDown size={18} />}
      </button>

      <p id={hintId} className="search-hint">
        Paste any TikTok video link and hit enter
      </p>
    </form>
  );
}