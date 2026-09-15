import { useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import AuthLayout from "../../layouts/AuthLayout/AuthLayout.jsx";
import Input from "../../components/Input/Input.jsx";
import Button from "../../components/Button/Button.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../services/apiClient.js";
import { isValidEmail } from "../../utils/validation.js";

function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const justRegistered = Boolean(location.state?.justRegistered);

  function validate() {
    const errors = {};
    if (!email.trim()) errors.email = "Email is required.";
    else if (!isValidEmail(email)) errors.email = "Enter a valid email address.";
    if (!password) errors.password = "Password is required.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
      const redirect = searchParams.get("redirect");
      navigate(redirect || "/", { replace: true });
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setFormError("Invalid email or password.");
      } else if (error instanceof ApiError && error.status === 0) {
        setFormError("Unable to connect to the server. Please try again.");
      } else if (error instanceof ApiError) {
        setFormError(error.message);
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to your TaskForge AI workspace">
      {justRegistered && (
        <div className="auth-layout__success" role="status">
          <CheckCircle2 size={16} aria-hidden="true" />
          Account created. Please sign in.
        </div>
      )}

      <form className="auth-layout__form" onSubmit={handleSubmit} noValidate>
        {formError && (
          <div className="auth-layout__error" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            {formError}
          </div>
        )}

        <Input
          type="email"
          label="Email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          error={fieldErrors.email}
        />
        <Input
          type="password"
          label="Password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
        />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={isSubmitting}
          className="auth-layout__submit"
        >
          Sign in
        </Button>
      </form>

      <p className="auth-layout__footer">
        Don't have an account? <Link to="/register">Create one</Link>
      </p>
    </AuthLayout>
  );
}

export default LoginPage;