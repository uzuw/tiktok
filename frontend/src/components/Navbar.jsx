import { MagnifyingGlass } from "@phosphor-icons/react";
import { GearSix } from "@phosphor-icons/react";
import BrandMark from "./BrandMark";
import Button from "./Button";
import ThemeToggle from "./ThemeToggle";
import useModifierHeld from "../hooks/useModifierHeld";
import "./Navbar.css";

export default function Navbar({
  theme,
  onToggleTheme,
  onOpenSettings,
  onOpenPalette,
  authenticated,
  queueCount = 0,
}) {
  const held = useModifierHeld();

  return (
    <header className="nav">
      <div className="nav-bar">
        <div className="nav-left">
          <a className="brand" href="#top" aria-label="SaveTok, back to top">
            <BrandMark size={20} />
            <span className="brand-word">SaveTok</span>
          </a>
          <nav className="nav-links" aria-label="Sections">
            {queueCount > 0 && (
              <a className="nav-link" href="#queue">
                Queue
              </a>
            )}
          </nav>
        </div>

        <button type="button" className="nav-search" onClick={onOpenPalette}>
          <MagnifyingGlass size={15} aria-hidden="true" />
          <span className="nav-search-label">Search or jump to…</span>
          <span className="nav-search-keys">
            <span className={`kbd ${held ? "kbd--held" : ""}`}>⌘</span>
            <span className={`kbd ${held ? "kbd--held" : ""}`}>K</span>
          </span>
        </button>

        <div className="nav-right">
          <span className="nav-status" role="status">
            <span className={`dot ${authenticated ? "dot--ok" : "dot--idle"}`} aria-hidden="true" />
            <span className="nav-status-text">{authenticated ? "Cookies added" : "No cookies"}</span>
          </span>

          <ThemeToggle theme={theme} onToggle={onToggleTheme} />

          <Button
            variant="icon"
            className="btn--ghost"
            onClick={onOpenSettings}
            aria-label="Settings"
            title="Session cookies"
          >
            <GearSix size={18} />
          </Button>
        </div>
      </div>
    </header>
  );
}
