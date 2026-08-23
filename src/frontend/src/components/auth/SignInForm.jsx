import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { useRouter } from "../../context/Router";

export default function SignInForm({ onAuthSuccess }) {
  const { login } = useAuth();
  const { navigate } = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState(0);

  const validate = () => {
    if (!email.trim()) {
      return "OPERATOR EMAIL IS REQUIRED";
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      return "INVALID OPERATOR EMAIL FORMAT";
    }
    if (!password) {
      return "ACCESS KEY / PASSWORD IS REQUIRED";
    }
    if (password.length < 6) {
      return "PASSWORD MUST BE AT LEAST 6 CHARACTERS";
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
    }, 200);

    try {
      const session = await login(email.trim(), password);
      clearInterval(progressInterval);
      setProgress(100);
      onAuthSuccess?.(session);
    } catch (err) {
      clearInterval(progressInterval);
      setIsSubmitting(false);
      setProgress(0);
      setError(err.message || "AUTHENTICATION FAILED: INVALID CREDENTIALS");
    }
  };

  const handleFillDemo = () => {
    setEmail("operator@radar.space");
    setPassword("radar123");
    setError(null);
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      {/* Demo operator fill banner */}
      <div className="auth-demo-banner mono">
        <div style={{ fontSize: 10.5, color: "var(--text-secondary)" }}>
          TESTING CREDENTIALS // DEMO OPERATOR
        </div>
        <button
          type="button"
          className="auth-demo-fill-btn"
          onClick={handleFillDemo}
        >
          [ AUTO-FILL DEMO ]
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="auth-error-banner mono">
          <span className="auth-error-icon">⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Email Input */}
      <div className="auth-field-group">
        <label className="auth-label mono eyebrow" htmlFor="operator-email">
          OPERATOR EMAIL
        </label>
        <input
          id="operator-email"
          type="email"
          className="auth-input mono"
          placeholder="operator@agency.gov or name@company.space"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isSubmitting}
          autoComplete="username"
        />
      </div>

      {/* Password Input */}
      <div className="auth-field-group">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
          <label className="auth-label mono eyebrow" htmlFor="operator-password">
            ACCESS KEY / PASSWORD
          </label>
        </div>
        <input
          id="operator-password"
          type="password"
          className="auth-input mono"
          placeholder="••••••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={isSubmitting}
          autoComplete="current-password"
        />
      </div>

      {/* Submit Button / Progress */}
      {isSubmitting ? (
        <div className="auth-loading-state mono">
          <div className="auth-loading-text">
            <span>AUTHENTICATING SECURE SESSION...</span>
            <span>{progress}%</span>
          </div>
          <div className="auth-progress-bar">
            <div className="auth-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : (
        <button type="submit" className="auth-submit-btn mono">
          [ SIGN IN TO RADAR ] →
        </button>
      )}

      {/* Switch to Sign Up */}
      <div className="auth-switch-prompt mono">
        <span>NEW OPERATOR?</span>
        <button
          type="button"
          className="auth-link-btn"
          onClick={() => navigate("/sign-up")}
          disabled={isSubmitting}
        >
          CREATE ACCOUNT →
        </button>
      </div>
    </form>
  );
}
