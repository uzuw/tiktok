import { useEffect, useState } from "react";
import { Trash, UploadSimple, X } from "@phosphor-icons/react";
import { authStatus, clearCookies, uploadCookies } from "../api";
import Button from "./Button";
import "./SettingsModal.css";

export default function SettingsModal({ open, onClose, onAuthChange }) {
  const [text, setText] = useState("");
  const [authed, setAuthed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      authStatus()
        .then((r) => setAuthed(r.authenticated))
        .catch(() => {});
      setText("");
      setError("");
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

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
    } catch {
      // leave state untouched if the request failed
    }
  };

  if (!open) return null;

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div
        className="modal surface"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <h2 className="panel-title" id="settings-title">
            Session cookies
          </h2>
          <Button variant="ghost" className="btn--icon" onClick={onClose} aria-label="Close">
            <X size={17} />
          </Button>
        </div>

        <div className="modal-body">
          <span className="badge modal-status">
            <span className={`dot ${authed ? "dot--ok" : "dot--idle"}`} aria-hidden="true" />
            {authed ? "A cookie file is loaded" : "No cookie file loaded"}
          </span>

          <p className="modal-desc">
            Some videos need a signed-in session before they can be resolved. Export your TikTok
            cookies as a Netscape <code>cookies.txt</code> and paste the contents below.
          </p>

          <label className="sr-only" htmlFor="cookie-input">
            Cookie file contents
          </label>
          <textarea
            id="cookie-input"
            className="cookie-input"
            rows={6}
            placeholder={"# Netscape HTTP Cookie File\n.tiktok.com\tTRUE\t/\tTRUE\t0\tsessionid\t…"}
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={authed}
          />

          {error && (
            <p className="modal-error" role="alert">
              {error}
            </p>
          )}

          <div className="modal-actions">
            {!authed ? (
              <Button variant="primary" onClick={handleSave} disabled={saving || !text.trim()}>
                <UploadSimple size={16} weight="bold" />
                <span>{saving ? "Saving…" : "Save cookies"}</span>
              </Button>
            ) : (
              <Button variant="secondary" onClick={handleClear}>
                <Trash size={16} />
                <span>Remove cookies</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
