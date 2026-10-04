import { useId, useState } from "react";
import { ArrowDown } from "@phosphor-icons/react";
import Button from "./Button";
import "./SearchBar.css";

export default function SearchBar({ onResolve, loading, inputRef }) {
  const [url, setUrl] = useState("");
  const hintId = useId();
  const inputId = `${hintId}-field`;

  const handleSubmit = (event) => {
    event.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onResolve(trimmed);
  };

  return (
    <form className="search" onSubmit={handleSubmit}>
      <div className="field">
        <label className="sr-only" htmlFor={inputId}>
          TikTok video link
        </label>
        <input
          ref={inputRef}
          id={inputId}
          type="url"
          className="field-input"
          placeholder="Paste a TikTok video link"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          aria-describedby={hintId}
          autoFocus
          spellCheck="false"
          autoComplete="off"
        />
        <Button
          variant="primary"
          className="search-submit"
          type="submit"
          disabled={loading || !url.trim()}
          aria-label={loading ? "Fetching download options" : "Fetch download options"}
        >
          <ArrowDown size={18} weight="bold" />
          <span className="search-submit-label">Fetch</span>
        </Button>
      </div>

      {/* Indeterminate bar while resolving — replaces the classic spinner */}
      <div className={`search-progress ${loading ? "is-loading" : ""}`} aria-hidden={!loading}>
        {loading && <div className="progress" />}
      </div>

      <p id={hintId} className="search-hint">
        We&apos;ll fetch the available formats before saving anything.
      </p>
    </form>
  );
}
