import { useEffect, useMemo, useState } from "react";
import { DownloadSimple, Trash, X } from "@phosphor-icons/react";
import { clearQueue, listQueue, removeQueueItem } from "../api";
import Button from "./Button";
import "./QueuePanel.css";

const ACTIVE_STATUSES = new Set(["pending", "downloading"]);

const STATUS_LABEL = {
  pending: "Waiting",
  downloading: "Downloading",
  completed: "Saved",
  failed: "Failed",
};

const STATUS_DOT = {
  pending: "dot--idle",
  downloading: "dot--busy",
  completed: "dot--ok",
  failed: "dot--bad",
};

const REMOVE_MS = 170;

export default function QueuePanel({ onCount }) {
  const [items, setItems] = useState([]);
  const [removingId, setRemovingId] = useState(null);
  const hasActive = items.some((item) => ACTIVE_STATUSES.has(item.status));

  useEffect(() => {
    let cancelled = false;

    const fetchItems = async () => {
      try {
        const data = await listQueue();
        if (!cancelled) setItems(data.items || []);
      } catch {
        // silently fail — next poll will retry
      }
    };

    fetchItems();
    const interval = setInterval(fetchItems, hasActive ? 2000 : 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [hasActive]);

  useEffect(() => {
    onCount?.(items.length);
  }, [items.length, onCount]);

  // Collapse the row first, then drop it. The poll resyncs if the delete failed.
  const handleRemove = (id) => {
    if (removingId) return;
    setRemovingId(id);
    removeQueueItem(id).catch(() => {});
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id));
      setRemovingId(null);
    }, REMOVE_MS);
  };

  const handleClear = async () => {
    try {
      await clearQueue();
      setItems([]);
    } catch {
      // leave items in place if clear failed
    }
  };

  const activeCount = useMemo(
    () => items.filter((item) => ACTIVE_STATUSES.has(item.status)).length,
    [items]
  );

  if (items.length === 0) return null;

  return (
    <section className="queue panel" id="queue" aria-label="Download queue">
      <div className="panel-head">
        <div className="queue-heading">
          <h2 className="panel-title">Queue</h2>
          <span className="chip queue-count">
            {activeCount > 0 ? `${activeCount} in progress` : `${items.length} waiting`}
          </span>
        </div>
        <Button variant="ghost" className="queue-clear" onClick={handleClear}>
          <Trash size={15} />
          <span>Clear</span>
        </Button>
      </div>

      <ul className="queue-list">
        {items.map((item) => (
          <li
            key={item.id}
            className={`qrow surface ${removingId === item.id ? "is-removing" : ""}`}
          >
            <span className={`dot ${STATUS_DOT[item.status] ?? ""}`} aria-hidden="true" />

            <span className="qrow-main">
              <span className="qrow-name mono">{item.video_id || item.id.slice(0, 8)}</span>
              {item.status === "failed" && item.error ? (
                <span className="qrow-error" title={item.error}>
                  {item.error}
                </span>
              ) : (
                <span className="qrow-status">{STATUS_LABEL[item.status] ?? item.status}</span>
              )}
            </span>

            <span className="qrow-actions row-actions">
              {item.status === "completed" && item.file_path && (
                <Button
                  as="a"
                  variant="secondary"
                  className="qrow-btn"
                  href={`/queue/${item.id}/file`}
                  aria-label="Download file"
                >
                  <DownloadSimple size={15} />
                  <span>Save</span>
                </Button>
              )}
              {(item.status === "pending" || item.status === "failed") && (
                <Button
                  variant="ghost"
                  className="qrow-btn btn--icon"
                  onClick={() => handleRemove(item.id)}
                  aria-label={item.status === "failed" ? "Dismiss" : "Remove from queue"}
                >
                  <X size={15} />
                </Button>
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
