import { useState } from "react";
import { User, Palette, ShieldCheck, CheckCircle2, AlertCircle, Sun, Moon, Monitor } from "lucide-react";
import PageContainer from "../../components/PageContainer/PageContainer.jsx";
import Card from "../../components/Card/Card.jsx";
import Input from "../../components/Input/Input.jsx";
import Button from "../../components/Button/Button.jsx";
import Badge from "../../components/Badge/Badge.jsx";
import { useAuth } from "../../context/AuthContext.jsx";
import { useTheme } from "../../context/ThemeContext.jsx";
import { userService } from "../../services/userService.js";
import { ApiError } from "../../services/apiClient.js";
import "./SettingsPage.css";

const SECTIONS = [
  { id: "profile", label: "Profile", icon: User },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "account", label: "Account", icon: ShieldCheck },
];

const THEME_OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function ProfileSection() {
  const { user, updateUser } = useAuth();
  const [name, setName] = useState(user?.name || "");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSuccess(false);

    const trimmed = name.trim();
    if (!trimmed) {
      setError("Name cannot be empty.");
      return;
    }

    setIsSaving(true);
    try {
      const updated = await userService.updateProfile(trimmed);
      updateUser(updated);
      setSuccess(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 0) {
        setError("Unable to connect to the server. Please try again.");
      } else if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <>
      <h2 className="settings__section-title">Profile</h2>
      <p className="settings__section-subtitle">Update your name as it appears across TaskForge AI.</p>

      <form className="settings__form" onSubmit={handleSubmit} noValidate>
        {error && (
          <div className="settings__feedback settings__feedback--error" role="alert">
            <AlertCircle size={16} aria-hidden="true" />
            {error}
          </div>
        )}
        {success && !error && (
          <div className="settings__feedback settings__feedback--success" role="status">
            <CheckCircle2 size={16} aria-hidden="true" />
            Profile updated.
          </div>
        )}

        <Input
          label="Name"
          value={name}
          onChange={(event) => {
            setName(event.target.value);
            setSuccess(false);
          }}
        />
        <Input label="Email" value={user?.email || ""} disabled hint="Email cannot be changed yet." />

        <div className="settings__actions">
          <Button type="submit" variant="primary" loading={isSaving}>
            Save changes
          </Button>
        </div>
      </form>
    </>
  );
}

function AppearanceSection() {
  const { theme, setTheme } = useTheme();
  const [savingValue, setSavingValue] = useState(null);
  const [error, setError] = useState("");

  async function handleSelect(value) {
    if (value === theme || savingValue) return;
    setError("");
    setSavingValue(value);
    try {
      await setTheme(value);
    } catch (err) {
      setError("Could not save your theme preference. Please try again.");
    } finally {
      setSavingValue(null);
    }
  }

  return (
    <>
      <h2 className="settings__section-title">Appearance</h2>
      <p className="settings__section-subtitle">Choose how TaskForge AI looks on this device.</p>

      {error && (
        <div className="settings__feedback settings__feedback--error" role="alert" style={{ marginBottom: "var(--space-4)" }}>
          <AlertCircle size={16} aria-hidden="true" />
          {error}
        </div>
      )}

      <div className="settings__theme-options" role="group" aria-label="Theme preference">
        {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            className="settings__theme-option"
            aria-pressed={theme === value}
            disabled={Boolean(savingValue)}
            onClick={() => handleSelect(value)}
          >
            <Icon size={20} aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </div>
    </>
  );
}

function AccountSection() {
  const { user } = useAuth();

  return (
    <>
      <h2 className="settings__section-title">Account</h2>
      <p className="settings__section-subtitle">Information about your TaskForge AI account.</p>

      <div className="settings__account-list">
        <div className="settings__account-row">
          <span className="settings__account-label">Email</span>
          <span className="settings__account-value">{user?.email}</span>
        </div>
        <div className="settings__account-row">
          <span className="settings__account-label">Status</span>
          <Badge variant={user?.is_active ? "success" : "danger"}>
            {user?.is_active ? "Active" : "Inactive"}
          </Badge>
        </div>
        <div className="settings__account-row">
          <span className="settings__account-label">Member since</span>
          <span className="settings__account-value">{formatDate(user?.created_at)}</span>
        </div>
        <div className="settings__account-row">
          <span className="settings__account-label">Last updated</span>
          <span className="settings__account-value">{formatDate(user?.updated_at)}</span>
        </div>
      </div>
    </>
  );
}

function SettingsPage() {
  const [activeSection, setActiveSection] = useState("profile");

  return (
    <PageContainer title="Settings" subtitle="Manage your profile, appearance, and account">
      <div className="settings__nav" role="tablist" aria-label="Settings sections">
        {SECTIONS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            role="tab"
            className="settings__nav-item"
            aria-selected={activeSection === id}
            onClick={() => setActiveSection(id)}
          >
            <Icon size={16} aria-hidden="true" />
            {label}
          </button>
        ))}
      </div>

      <Card>
        {activeSection === "profile" && <ProfileSection />}
        {activeSection === "appearance" && <AppearanceSection />}
        {activeSection === "account" && <AccountSection />}
      </Card>
    </PageContainer>
  );
}

export default SettingsPage;