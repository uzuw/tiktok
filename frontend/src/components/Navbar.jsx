import { FiSettings } from "react-icons/fi";
import ThemeToggle from "./ThemeToggle";

export default function Navbar({ theme, onToggleTheme, onOpenSettings, authenticated }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-title">SaveTok</span>
        <span className="navbar-subtitle">TikTok Video Downloader</span>
      </div>
      <div className="navbar-actions">
        <span className={`auth-dot ${authenticated ? "authed" : ""}`} title={authenticated ? "Cookies loaded" : "No cookies"}>
          <span className="dot" />
        </span>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
        <button className="icon-btn" onClick={onOpenSettings} aria-label="Settings" title="Settings">
          <FiSettings size={18} />
        </button>
      </div>
    </nav>
  );
}
