import { useState, useEffect, useCallback, useRef } from "react";
import { FiGithub } from "react-icons/fi";
import { resolveVideo, enqueue, authStatus } from "./api";
import Navbar from "./components/Navbar";
import SearchBar from "./components/SearchBar";
import VideoResult from "./components/VideoResult";

import QueuePanel from "./components/QueuePanel";
import SettingsModal from "./components/SettingsModal";

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
      <Navbar
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenSettings={() => setShowSettings(true)}
        authenticated={authenticated}
      />

      <main className="main">
        <div className="hero">
          <h1 className="hero-title">SaveTok</h1>
          <p className="hero-subtitle">Download TikTok videos in best quality, fast and free.</p>
        </div>

        <SearchBar onResolve={handleResolve} loading={loading} />

        {error && <p className="error-msg fade-in">{error}</p>}

        {result && <VideoResult video={result} onQueue={handleQueueVideo} />}

        <QueuePanel />
      </main>

      <footer className="footer">
        <a href="https://github.com" target="_blank" rel="noopener" className="footer-link">
          <FiGithub size={14} /> SaveTok
        </a>
      </footer>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
        onAuthChange={setAuthenticated}
      />
    </div>
  );
}
