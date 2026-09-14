import "./StatePanel.css";

function StatePanel({ variant = "empty", icon, title, description, action }) {
  return (
    <div className={`state-panel ${variant === "error" ? "state-panel--error" : ""}`}>
      {icon && (
        <span className="state-panel__icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <h3 className="state-panel__title">{title}</h3>
      {description && <p className="state-panel__description">{description}</p>}
      {action}
    </div>
  );
}

export function EmptyState(props) {
  return <StatePanel variant="empty" {...props} />;
}

export function ErrorState(props) {
  return <StatePanel variant="error" {...props} />;
}

export default StatePanel;