import { useState } from "react";
import { FiLink, FiArrowDown, FiLoader } from "react-icons/fi";

export default function SearchBar({ onResolve, loading }) {
  const [url, setUrl] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (url.trim()) onResolve(url.trim());
  };

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <div className="search-input-wrap">
        <FiLink className="search-icon" size={16} />
        <input
          type="url"
          className="search-input"
          placeholder="Paste TikTok video or profile URL..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          autoFocus
        />
      </div>
      <button className="search-btn" type="submit" disabled={loading || !url.trim()}>
        {loading ? <FiLoader className="spin" size={18} /> : <FiArrowDown size={18} />}
      </button>
    </form>
  );
}
