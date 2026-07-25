import { useState, useEffect, useRef } from "react";
import { FiX, FiDownload, FiLoader, FiCheck, FiAlertCircle } from "react-icons/fi";
import { listQueue, removeQueueItem, downloadUrl } from "../api";

const STATUS_ICONS = {
  pending: null,
  downloading: <FiLoader className="spin" size={14} />,
  completed: <FiCheck size={14} />,
  failed: <FiAlertCircle size={14} />,
};

export default function QueuePanel() {
  const [items, setItems] = useState([]);
  const polling = useRef(null);
  const hasActive = items.some((i) => i.status === "pending" || i.status === "downloading");

  const fetchItems = async () => {
    try {
      const data = await listQueue();
      setItems(data.items || []);
    } catch {
      // silently fail
    }
  };

  useEffect(() => {
    fetchItems();
    const interval = setInterval(fetchItems, hasActive ? 2000 : 10000);
    polling.current = interval;
    return () => clearInterval(interval);
  }, [hasActive]);

  const handleRemove = async (id) => {
    try {
      await removeQueueItem(id);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } catch {}
  };

  const pendingCount = items.filter((i) => i.status === "pending").length;
  const downloadingCount = items.filter((i) => i.status === "downloading").length;
  const completedCount = items.filter((i) => i.status === "completed").length;
  const failedCount = items.filter((i) => i.status === "failed").length;

  if (items.length === 0) return null;

  return (
    <div className="queue-panel fade-in">
      <div className="queue-header">
        <span className="queue-title">Queue</span>
        <div className="queue-badges">
          {pendingCount > 0 && <span className="badge badge-pending">{pendingCount} pending</span>}
          {downloadingCount > 0 && <span className="badge badge-downloading">{downloadingCount} downloading</span>}
          {completedCount > 0 && <span className="badge badge-completed">{completedCount} done</span>}
          {failedCount > 0 && <span className="badge badge-failed">{failedCount} failed</span>}
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
                {STATUS_ICONS[item.status] || null}
              </span>
              <span className="status-text">{item.status}</span>
            </div>
            <div className="queue-item-action">
              {item.status === "completed" && item.file ? (
                <a className="download-link" href={`/queue/${item.id}/file`} title="Download file">
                  <FiDownload size={14} />
                </a>
              ) : item.status === "pending" ? (
                <button className="btn-icon danger" onClick={() => handleRemove(item.id)} title="Remove">
                  <FiX size={14} />
                </button>
              ) : item.status === "failed" ? (
                <button className="btn-icon" onClick={() => handleRemove(item.id)} title="Dismiss">
                  <FiX size={14} />
                </button>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
