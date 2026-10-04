import { Moon, Sun } from "@phosphor-icons/react";
import Button from "./Button";

export default function ThemeToggle({ theme, onToggle }) {
  const dark = theme === "dark";
  const label = dark ? "Switch to light mode" : "Switch to dark mode";
  return (
    <Button
      variant="icon"
      className="btn--ghost"
      onClick={onToggle}
      aria-label={label}
      title={label}
    >
      {dark ? <Sun size={19} /> : <Moon size={19} />}
    </Button>
  );
}
