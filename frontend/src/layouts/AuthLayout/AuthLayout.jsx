import Card from "../../components/Card/Card.jsx";
import "./AuthLayout.css";

function AuthLayout({ title, subtitle, children }) {
  return (
    <div className="auth-layout">
      <div className="auth-layout__panel">
        <div className="auth-layout__brand">
          <span className="auth-layout__brand-mark" aria-hidden="true">
            TF
          </span>
          <span className="auth-layout__brand-name">TaskForge AI</span>
        </div>
        <Card className="auth-layout__card" padded={false}>
          <h1 className="auth-layout__title">{title}</h1>
          {subtitle && <p className="auth-layout__subtitle">{subtitle}</p>}
          {children}
        </Card>
      </div>
    </div>
  );
}

export default AuthLayout;