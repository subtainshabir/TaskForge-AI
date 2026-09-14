import "./Card.css";

function Card({
  children,
  padded = true,
  interactive = false,
  as: Component = "div",
  className = "",
  ...rest
}) {
  const classes = [
    "card",
    padded && "card--padded",
    interactive && "card--interactive",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <Component
      className={classes}
      tabIndex={interactive ? 0 : undefined}
      {...rest}
    >
      {children}
    </Component>
  );
}

export default Card;