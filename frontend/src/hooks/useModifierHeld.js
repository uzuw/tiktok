import { useEffect, useState } from "react";

/**
 * True while the platform modifier key (⌘ / Ctrl) is held down — used to make
 * the keyboard hints in the UI visibly depress, as a nudge toward shortcuts.
 */
export default function useModifierHeld() {
  const [held, setHeld] = useState(false);

  useEffect(() => {
    const isModifier = (event) => event.key === "Meta" || event.key === "Control";
    const onDown = (event) => isModifier(event) && setHeld(true);
    const onUp = (event) => isModifier(event) && setHeld(false);
    const onBlur = () => setHeld(false);

    window.addEventListener("keydown", onDown);
    window.addEventListener("keyup", onUp);
    window.addEventListener("blur", onBlur);
    return () => {
      window.removeEventListener("keydown", onDown);
      window.removeEventListener("keyup", onUp);
      window.removeEventListener("blur", onBlur);
    };
  }, []);

  return held;
}
