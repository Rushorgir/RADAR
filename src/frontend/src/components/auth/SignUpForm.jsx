import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "../../context/Router";

export default function SignUpForm({ onAuthSuccess }) {
  const { signup } = useAuth();
  const { navigate } = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [organization, setOrganization] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);

  const validate = () => {
    if (!name.trim()) {
      return "OPERATOR FULL NAME IS REQUIRED";
    }
    if (!email.trim()) {
      return "OPERATOR EMAIL IS REQUIRED";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return "INVALID OPERATOR EMAIL FORMAT";
    }
    if (!password) {
      return "PASSWORD IS REQUIRED";
    }
    if (password.length < 6) {
      return "SECURITY POLICY: PASSWORD MUST BE AT LEAST 6 CHARACTERS";
    }
    if (password !== confirmPassword) {
      return "SECURITY REJECTION: PASSWORDS DO NOT MATCH";
    }
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setProgress(20);

    const progressInterval = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 25 : prev));
    }, 250);

    try {
      const session = await signup({
        name: name.trim(),
        email: email.trim(),
        organization: organization.trim() || "ORBITAL DYNAMICS CORP",
        password,
      });
      clearInterval(progressInterval);
      setProgress(100);
      onAuthSuccess?.(session);
    } catch (err) {
      clearInterval(progressInterval);
      setIsSubmitting(false);
      setProgress(0);
      setError(err.message || "REGISTRATION FAILED");
    }
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      {/* Error Message */}
      {error && (
        <div className="auth-error-banner mono">
          <span className="auth-error-icon">⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Full Name */}
      <div className="auth-field-group">
        <label className="auth-label mono eyebrow" htmlFor="operator-name">
          OPERATOR FULL NAME
        </label>
        <input
          id="operator-name"
          type="text"
          className="auth-input mono"
          placeholder="e.g. Commander Sarah Chen"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSubmitting}
        />
      </div>

      {/* Email Input */}
      <div className="auth-field-group">
        <label className="auth-label mono eyebrow" htmlFor="reg-email">
          OPERATOR EMAIL
        </label>
        <input
          id="reg-email"
          type="email"
          className="auth-input mono"
          placeholder="name@organization.space"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isSubmitting}
          autoComplete="username"
        />
      </div>

      {/* Organization */}
      <div className="auth-field-group">
        <label className="auth-label mono eyebrow" htmlFor="reg-org">
          ORGANIZATION / MISSION AFFILIATION
        </label>
        <input
          id="reg-org"
          type="text"
          className="auth-input mono"
          placeholder="e.g. European Space Agency / Planet Labs"
          value={organization}
          onChange={(e) => setOrganization(e.target.value)}
          disabled={isSubmitting}
        />
      </div>

      {/* Password Grid */}
      <div className="auth-field-grid">
        <div className="auth-field-group">
          <label className="auth-label mono eyebrow" htmlFor="reg-password">
            PASSWORD
          </label>
          <input
            id="reg-password"
            type="password"
            className="auth-input mono"
            placeholder="Min. 6 chars"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isSubmitting}
            autoComplete="new-password"
          />
        </div>

        <div className="auth-field-group">
          <label className="auth-label mono eyebrow" htmlFor="reg-confirm-password">
            CONFIRM PASSWORD
          </label>
          <input
            id="reg-confirm-password"
            type="password"
            className="auth-input mono"
            placeholder="Repeat password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            disabled={isSubmitting}
            autoComplete="new-password"
          />
        </div>
      </div>

      {/* Submit Button / Progress */}
      {isSubmitting ? (
        <div className="auth-loading-state mono">
          <div className="auth-loading-text">
            <span>REGISTERING OPERATOR SESSION...</span>
            <span>{progress}%</span>
          </div>
          <div className="auth-progress-bar">
            <div className="auth-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : (
        <button type="submit" className="auth-submit-btn mono">
          [ CREATE RADAR ACCOUNT ] →
        </button>
      )}

      {/* Switch to Sign In */}
      <div className="auth-switch-prompt mono">
        <span>ALREADY REGISTERED?</span>
        <button
          type="button"
          className="auth-link-btn"
          onClick={() => navigate("/sign-in")}
          disabled={isSubmitting}
        >
          SIGN IN →
        </button>
      </div>
    </form>
  );
}
