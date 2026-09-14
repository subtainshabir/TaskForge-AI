import Spinner from "../Spinner/Spinner.jsx";
import "./Button.css";

function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  type = "button",
  className = "",
  ...rest
}) {
  return (
    <button
      type={type}
      className={`btn btn--${variant} btn--${size} ${className}`.trim()}
      disabled={disabled || loading}
      data-loading={loading}
      aria-busy={loading}
      {...rest}
    >
      {loading && (
        <span className="btn__spinner">
          <Spinner size={size === "lg" ? "md" : "sm"} label="Loading" />
        </span>
      )}
      {children}
    </button>
  );
}

export default Button;