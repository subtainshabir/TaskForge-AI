import "./PageContainer.css";

function PageContainer({ title, subtitle, actions, children }) {
  return (
    <div className="page">
      {(title || actions) && (
        <div className="page__header">
          <div>
            {title && <h1 className="page__title">{title}</h1>}
            {subtitle && <p className="page__subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="page__actions">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

export default PageContainer;