import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DownloadSimple,
  GearSix,
  LinkSimple,
  LockSimple,
  Moon,
  Question,
  ShieldCheck,
  Sparkle,
  Sun,
  WarningCircle,
} from "@phosphor-icons/react";
import { authStatus, clearQueue, enqueue, resolveVideo } from "./api";
import BrandMark from "./components/BrandMark";
import CommandPalette from "./components/CommandPalette";
import Navbar from "./components/Navbar";
import QueuePanel from "./components/QueuePanel";
import ResultSkeleton from "./components/ResultSkeleton";
import SearchBar from "./components/SearchBar";
import SettingsModal from "./components/SettingsModal";
import VideoResult from "./components/VideoResult";
import "./App.css";

const FACTS = [
  [ShieldCheck, "No watermark"],
  [Sparkle, "Highest quality"],
  [LockSimple, "Stays on your machine"],
];

const STEPS = [
  [LinkSimple, "Paste a link", "Drop in any TikTok video URL. Nothing is saved until you ask for it."],
  [Sparkle, "We find the best copy", "SaveTok reads the format list and keeps the highest resolution that isn't watermarked."],
  [DownloadSimple, "Download or queue", "Take the file straight away, or line up several and let the queue work through them."],
];

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
  const [queueCount, setQueueCount] = useState(0);
  const [showSettings, setShowSettings] = useState(false);
  const [showPalette, setShowPalette] = useState(false);
  const [authenticated, setAuthenticated] = useState(false);
  const lastUrl = useRef("");
  const inputRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("savetok-theme", theme);
  }, [theme]);

  useEffect(() => {
    authStatus()
      .then((r) => setAuthenticated(r.authenticated))
      .catch(() => {});
  }, []);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setShowPalette((open) => !open);
        return;
      }

      // "/" jumps to the paste field, unless the user is already typing
      const typing = /^(input|textarea|select)$/i.test(event.target?.tagName ?? "");
      if (event.key === "/" && !typing && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const toggleTheme = useCallback(() => setTheme((t) => (t === "dark" ? "light" : "dark")), []);

  const focusInput = useCallback(() => {
    inputRef.current?.focus();
    inputRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, []);

  const paletteActions = useMemo(
    () => [
      { id: "paste", label: "Paste a link", hint: "/", icon: LinkSimple, run: focusInput },
      {
        id: "theme",
        label: `Switch to ${theme === "dark" ? "light" : "dark"} mode`,
        keywords: ["dark", "light", "appearance"],
        icon: theme === "dark" ? Sun : Moon,
        run: toggleTheme,
      },
      {
        id: "cookies",
        label: "Session cookies",
        keywords: ["auth", "login"],
        icon: GearSix,
        run: () => setShowSettings(true),
      },
      {
        id: "how",
        label: "How it works",
        icon: Question,
        run: () => document.getElementById("how")?.scrollIntoView({ block: "start" }),
      },
      ...(queueCount > 0
        ? [
            {
              id: "clear-queue",
              label: "Clear the queue",
              keywords: ["reset", "remove"],
              icon: WarningCircle,
              run: () => clearQueue().catch(() => {}),
            },
          ]
        : []),
    ],
    [theme, queueCount, toggleTheme, focusInput]
  );

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

  const status = loading
    ? { dot: "dot--busy", label: "Fetching formats…" }
    : error
      ? { dot: "dot--bad", label: "Couldn't resolve that link" }
      : { dot: "dot--ok", label: "Ready" };

  return (
    <div className="app" id="top">
      <Navbar
        theme={theme}
        onToggleTheme={toggleTheme}
        onOpenSettings={() => setShowSettings(true)}
        onOpenPalette={() => setShowPalette(true)}
        authenticated={authenticated}
        queueCount={queueCount}
      />

      <main>
        <section className="hero">
          <div className="shell hero-inner">
            <span className="badge hero-badge" role="status">
              <span className={`dot ${status.dot}`} aria-hidden="true" />
              {status.label}
            </span>

            <h1 className="display hero-title">Paste a link, keep the video.</h1>
            <p className="lede hero-lede">
              SaveTok runs on your own machine and saves the highest-resolution copy of any TikTok
              video. No watermark, no account, nothing sent anywhere else.
            </p>

            <div className="hero-field">
              <SearchBar onResolve={handleResolve} loading={loading} inputRef={inputRef} />
            </div>

            {error && (
              <p className="error-note" role="alert">
                <WarningCircle size={17} aria-hidden="true" />
                <span>{error}</span>
              </p>
            )}

            <ul className="facts">
              {FACTS.map(([Icon, label]) => (
                <li key={label} className="chip">
                  <Icon size={15} aria-hidden="true" />
                  {label}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <div className="shell result-stack">
          {loading && <ResultSkeleton />}
          {!loading && result && <VideoResult video={result} onQueue={handleQueueVideo} />}
          <QueuePanel onCount={setQueueCount} />
        </div>

        <section className="shell how" id="how">
          <h2 className="h2">How it works</h2>
          <div className="how-grid">
            {STEPS.map(([Icon, title, body]) => (
              <div className="how-item" key={title}>
                <span className="how-icon">
                  <Icon size={18} weight="bold" />
                </span>
                <h3 className="how-title">{title}</h3>
                <p className="how-body">{body}</p>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="foot">
        <div className="shell foot-inner">
          <span className="foot-brand">
            <BrandMark size={16} />
            <span>SaveTok</span>
          </span>
          <p className="foot-note">
            Runs locally with yt-dlp and Playwright. Press{" "}
            <span className="kbd">⌘</span> <span className="kbd">K</span> for commands.
          </p>
        </div>
      </footer>

      <SettingsModal
        open={showSettings}
        onClose={() => setShowSettings(false)}
        onAuthChange={setAuthenticated}
      />

      <CommandPalette
        open={showPalette}
        onClose={() => setShowPalette(false)}
        actions={paletteActions}
      />
    </div>
  );
}
