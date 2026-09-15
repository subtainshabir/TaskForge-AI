import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import AuthLayout from "../../layouts/AuthLayout/AuthLayout.jsx";
import Input from "../../components/Input/Input.jsx";
import Button from "../../components/Button/Button.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { ApiError } from "../../services/apiClient.js";
import { isValidEmail } from "../../utils/validation.js";

function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  function validate() {
    const errors = {};
    if (!name.trim()) errors.name = "Name is required.";
    else if (name.trim().length > 255) errors.name = "Name is too long.";

    if (!email.trim()) errors.email = "Email is required.";
    else if (!isValidEmail(email)) errors.email = "Enter a valid email address.";

    if (!password) errors.password = "Password is required.";
    else if (password.length < 8) errors.password = "Password must be at least 8 characters.";

    if (!confirmPassword) errors.confirmPassword = "Please confirm your password.";
    else if (confirmPassword !== password) errors.confirmPassword = "Passwords do not match.";

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setFormError("");
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await register(name.trim(), email.trim().toLowerCase(), password);
      navigate("/login", { replace: true, state: { justRegistered: true } });
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        setFormError("An account with this email already exists.");
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
    <AuthLayout title="Create your account" subtitle="Start organizing your work with TaskForge AI">
      <form className="auth-layout__form" onSubmit={handleSubmit} noValidate>
        {formError && (
          <div className="auth-layout__error" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            {formError}
          </div>
        )}

        <Input
          type="text"
          label="Name"
          autoComplete="name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          error={fieldErrors.name}
        />
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
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
          hint={!fieldErrors.password ? "At least 8 characters." : undefined}
        />
        <Input
          type="password"
          label="Confirm password"
          autoComplete="new-password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          error={fieldErrors.confirmPassword}
        />

        <Button
          type="submit"
          variant="primary"
          size="lg"
          loading={isSubmitting}
          className="auth-layout__submit"
        >
          Create account
        </Button>
      </form>

      <p className="auth-layout__footer">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </AuthLayout>
  );
}

export default RegisterPage;