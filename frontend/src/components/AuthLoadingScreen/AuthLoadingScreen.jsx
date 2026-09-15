import Spinner from "../Spinner/Spinner.jsx";
import "./AuthLoadingScreen.css";

function AuthLoadingScreen() {
  return (
    <div className="auth-loading">
      <span className="auth-loading__mark" aria-hidden="true">
        TF
      </span>
      <Spinner size="md" label="Loading your session" />
    </div>
  );
}

export default AuthLoadingScreen;