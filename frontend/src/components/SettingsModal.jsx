import { useState, useEffect } from "react";
import { FiX, FiUpload, FiTrash2, FiCheck } from "react-icons/fi";
import { authStatus, uploadCookies, clearCookies } from "../api";

export default function SettingsModal({ open, onClose, onAuthChange }) {
  const [text, setText] = useState("");
  const [authed, setAuthed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      authStatus().then((r) => setAuthed(r.authenticated)).catch(() => {});
      setText("");
      setError("");
    }
  }, [open]);

  const handleSave = async () => {
    if (!text.trim()) return;
    setSaving(true);
    setError("");
    try {
      await uploadCookies(text);
      setAuthed(true);
      onAuthChange(true);
    } catch (e) {
      setError(e.message);
    }
    setSaving(false);
  };

  const handleClear = async () => {
    try {
      await clearCookies();
      setAuthed(false);
      setText("");
      onAuthChange(false);
    } catch {}
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Settings</span>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <FiX size={18} />
          </button>
        </div>
        <div className="modal-body">
          <div className="setting-group">
            <div className="setting-label">
              <span>Cookies</span>
              <span className={`auth-status ${authed ? "authed" : ""}`}>
                {authed ? "Authenticated" : "Not authenticated"}
              </span>
            </div>
            <p className="setting-desc">
              Export your TikTok cookies in Netscape format and paste them below to access private or restricted content.
            </p>
            <textarea
              className="cookie-input"
              rows={6}
              placeholder="Paste Netscape cookie file contents here..."
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={authed}
            />
            {error && <p className="error-text">{error}</p>}
            <div className="cookie-actions">
              {!authed ? (
                <button className="btn btn-primary" onClick={handleSave} disabled={saving || !text.trim()}>
                  <FiUpload size={14} /> {saving ? "Saving..." : "Upload Cookies"}
                </button>
              ) : (
                <button className="btn btn-danger" onClick={handleClear}>
                  <FiTrash2 size={14} /> Clear Cookies
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
