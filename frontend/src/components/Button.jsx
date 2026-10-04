/**
 * Pill button. The interaction is deliberately small and CSS-driven: a 0.97
 * press, and the leading icon nudging down a pixel on hover.
 *
 * variant: "primary" (solid ink) | "secondary" (white on a panel) | "ghost" | "icon"
 */
export default function Button({
  as: Tag = "button",
  variant = "secondary",
  className = "",
  children,
  ...rest
}) {
  const classes = ["btn", `btn--${variant}`, className].filter(Boolean).join(" ");

  return (
    <Tag
      className={classes}
      {...(Tag === "button" ? { type: rest.type ?? "button" } : null)}
      {...rest}
    >
      {children}
    </Tag>
  );
}
