import { useCallback, useEffect, useRef, useState } from "react";
import { FiGithub, FiMonitor, FiShield, FiZap } from "react-icons/fi";
import { authStatus, enqueue, resolveVideo } from "./api";
import Navbar from "./components/Navbar";
import QueuePanel from "./components/QueuePanel";
import SearchBar from "./components/SearchBar";
import SettingsModal from "./components/SettingsModal";
import VideoResult from "./components/VideoResult";

function getInitialTheme() {
  const saved = localStorage.getItem("savetok-theme");
  if (saved) return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export default function App() {
  const [theme, setTheme] = useState(getInitialTheme);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const lastUrl = useRef("");
  const [showSettings, setShowSettings] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("savetok-theme", theme);
  }, [theme]);

  useEffect(() => {
    authStatus()
      .then((r) => setAuthenticated(r.authenticated))
      .catch(() => {});
  }, []);

  const toggleTheme = () => setTheme((t) => (t === "dark" ? "light" : "dark"));

  const handleResolve = useCallback(async (url) => {
    setLoading(true);
    setError("");
    setResult(null);
    lastUrl.current = url;
    try {
      const data = await resolveVideo(url);
      setResult(data);
    } catch (e) {
      setError(e.message);
    }
    setLoading(false);
  }, []);

  const handleQueueVideo = useCallback(async (formatId) => {
    const url = lastUrl.current;
    if (!url) return;
    try {
      await enqueue(url, formatId || "");
    } catch (e) {
      setError(e.message);
    }
  }, []);

  return (
    <div className="app">
      <div className="grid-dots" aria-hidden="true" />
      <div className="glow-blob glow-blob-1" aria-hidden="true" />
      <div className="glow-blob glow-blob-2" aria-hidden="true" />
      <div className="glow-blob glow-blob-3" aria-hidden="true" />

      <Navbar
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenSettings={() => setShowSettings(true)}
        authenticated={authenticated}
      />

      <main className="main">
        <div className="hero">
          <h1 className="hero-title hero-title-gradient">SaveTok</h1>
          <p className="hero-subtitle">
            Download TikTok videos instantly in the best available quality.
            No watermarks, no sign-up, no fuss.
          </p>
          <div className="feature-pills">
            <span className="feature-pill">
              <FiZap size={12} /> Instant resolve
            </span>
            <span className="feature-pill">
              <FiShield size={12} /> No watermarks
            </span>
            <span className="feature-pill">
              <FiMonitor size={12} /> Best quality
            </span>
          </div>
        </div>

        <SearchBar onResolve={handleResolve} loading={loading} />

        {error && <p className="error-msg fade-in">{error}</p>}

        {result && <VideoResult video={result} onQueue={handleQueueVideo} />}

        <div className="how-it-works">
          <h2 className="how-title">How it works</h2>
          <div className="how-steps">
            <div className="how-step">
              <span className="how-step-num">1</span>
              <span className="how-step-text">
                <strong>Paste</strong> any TikTok video link above
              </span>
            </div>
            <div className="how-step">
              <span className="how-step-num">2</span>
              <span className="how-step-text">
                <strong>Resolve</strong> picks the highest quality format
              </span>
            </div>
            <div className="how-step">
              <span className="how-step-num">3</span>
              <span className="how-step-text">
                <strong>Download</strong> or queue it for later
              </span>
            </div>
          </div>
        </div>

        <QueuePanel />
      </main>

      <footer className="footer">
        <a href="https://github.com" target="_blank" rel="noopener" className="footer-link">
          <FiGithub size={14} /> SaveTok
        </a>
        <span className="footer-sep">·</span>
        <span className="footer-text">Built with yt-dlp &amp; Playwright</span>
      </footer>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
        onAuthChange={setAuthenticated}
      />
    </div>
  );
}