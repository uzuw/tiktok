import { useEffect, useMemo, useRef, useState } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import useModifierHeld from "../hooks/useModifierHeld";
import "./CommandPalette.css";

/**
 * ⌘K palette. Arrow keys move, Enter runs, Esc closes. Actions come from the
 * app so the palette stays a view over real functionality.
 */
export default function CommandPalette({ open, onClose, actions = [] }) {
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const inputRef = useRef(null);
  const held = useModifierHeld();

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return actions;
    return actions.filter(
      (action) =>
        action.label.toLowerCase().includes(q) || action.keywords?.some((k) => k.includes(q))
    );
  }, [actions, query]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setIndex(0);
    inputRef.current?.focus();
  }, [open]);

  useEffect(() => {
    setIndex(0);
  }, [query]);

  if (!open) return null;

  const run = (action) => {
    onClose();
    action.run?.();
  };

  const onKeyDown = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setIndex((i) => (results.length ? (i + 1) % results.length : 0));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setIndex((i) => (results.length ? (i - 1 + results.length) % results.length : 0));
    } else if (event.key === "Enter" && results[index]) {
      event.preventDefault();
      run(results[index]);
    }
  };

  return (
    <div className="cmd-overlay" onMouseDown={onClose}>
      <div
        className="cmd"
        role="dialog"
        aria-modal="true"
        aria-label="Command menu"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="cmd-search">
          <MagnifyingGlass size={16} aria-hidden="true" />
          <input
            ref={inputRef}
            className="cmd-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type a command…"
            aria-label="Search commands"
            spellCheck="false"
          />
          <span className={`kbd ${held ? "kbd--held" : ""}`}>esc</span>
        </div>

        <div className="cmd-list" role="listbox" aria-label="Commands">
          {results.length === 0 && <p className="cmd-empty">No matching commands.</p>}
          {results.map((action, i) => (
            <button
              key={action.id}
              type="button"
              role="option"
              aria-selected={i === index}
              data-active={i === index}
              className="cmd-item"
              onMouseMove={() => setIndex(i)}
              onClick={() => run(action)}
            >
              <action.icon size={16} aria-hidden="true" />
              <span className="cmd-item-label">{action.label}</span>
              {action.hint && <span className="kbd">{action.hint}</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
