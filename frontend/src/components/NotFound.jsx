import { useEffect } from "react";
import { ArrowLeft } from "@phosphor-icons/react";
import BrandMark from "./BrandMark";
import Button from "./Button";
import ThemeToggle from "./ThemeToggle";
import "./NotFound.css";

export default function NotFound({ theme, onToggleTheme }) {
  useEffect(() => {
    const previous = document.title;
    document.title = "Page not found — SaveTok";
    return () => {
      document.title = previous;
    };
  }, []);

  return (
    <div className="nf">
      <header className="nf-top">
        <a className="nf-brand" href="/">
          <BrandMark size={20} />
          <span>SaveTok</span>
        </a>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </header>

      <main className="nf-main">
        <p className="nf-code" aria-hidden="true">
          404
        </p>
        <h1 className="nf-title">This page doesn&apos;t exist.</h1>
        <p className="nf-body">
          The link may be mistyped, or the page may have been removed. SaveTok only has one page —
          paste a link and it handles the rest.
        </p>
        <Button as="a" variant="primary" href="/">
          <ArrowLeft size={16} weight="bold" />
          <span>Back to SaveTok</span>
        </Button>
      </main>
    </div>
  );
}
