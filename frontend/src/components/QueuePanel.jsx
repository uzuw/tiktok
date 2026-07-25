import { useEffect, useMemo, useState } from "react";
import { FiAlertCircle, FiCheck, FiDownload, FiLoader, FiTrash2, FiX } from "react-icons/fi";
import { clearQueue, listQueue, removeQueueItem } from "../api";

const STATUS_ICONS = {
  pending: null,
  downloading: <FiLoader className="spin" size={14} />,
  completed: <FiCheck size={14} />,
  failed: <FiAlertCircle size={14} />,
};

const ACTIVE_STATUSES = new Set(["pending", "downloading"]);

export default function QueuePanel() {
  const [items, setItems] = useState([]);
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

  const handleRemove = async (id) => {
    try {
      await removeQueueItem(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
    } catch {
      // leave item in place if removal failed
    }
  };

  const handleClear = async () => {
    try {
      await clearQueue();
      setItems([]);
    } catch {
      // leave items in place if clear failed
    }
  };

  const counts = useMemo(() => {
    return items.reduce(
      (acc, item) => {
        acc[item.status] = (acc[item.status] || 0) + 1;
        return acc;
      },
      { pending: 0, downloading: 0, completed: 0, failed: 0 }
    );
  }, [items]);

  if (items.length === 0) return null;

  return (
    <div className="queue-panel fade-in">
      <div className="queue-header">
        <span className="queue-title">Queue</span>
        <div className="queue-badges">
          {counts.pending > 0 && (
            <span className="badge badge-pending">{counts.pending} pending</span>
          )}
          {counts.downloading > 0 && (
            <span className="badge badge-downloading">{counts.downloading} downloading</span>
          )}
          {counts.completed > 0 && (
            <span className="badge badge-completed">{counts.completed} done</span>
          )}
          {counts.failed > 0 && (
            <span className="badge badge-failed">{counts.failed} failed</span>
          )}
          <button className="btn-icon danger" onClick={handleClear} aria-label="Clear all" title="Clear all">
            <FiTrash2 size={14} />
          </button>
        </div>
      </div>

      <div className="queue-list">
        {items.map((item) => (
          <div className={`queue-item queue-${item.status}`} key={item.id}>
            <div className="queue-item-id" title={item.id}>
              {item.video_id || item.id.slice(0, 8)}
            </div>

            <div className="queue-item-status">
              <span className={`status-icon status-${item.status}`}>
                {STATUS_ICONS[item.status]}
              </span>
              <span className="status-text">{item.status}</span>
            </div>

            <div className="queue-item-action">
              {item.status === "completed" && item.file_path && (
                <a className="download-link" href={`/queue/${item.id}/file`} aria-label="Download file" title="Download file">
                  <FiDownload size={14} />
                </a>
              )}
              {item.status === "pending" && (
                <button className="btn-icon danger" onClick={() => handleRemove(item.id)} aria-label="Remove" title="Remove">
                  <FiX size={14} />
                </button>
              )}
              {item.status === "failed" && (
                <button className="btn-icon" onClick={() => handleRemove(item.id)} aria-label="Dismiss" title="Dismiss">
                  <FiX size={14} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}