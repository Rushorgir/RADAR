import { createContext, useContext, useEffect, useState } from "react";

const AuthContext = createContext(null);

const STORAGE_KEY = "radar_session_v1";

const DEFAULT_OPERATOR = {
  callsign: "OPERATOR // B. GANESH",
  email: "operator@radar.space",
  role: "ORBITAL RISK ANALYST",
  organization: "RADAR FLIGHT DYNAMICS",
  clearance: "LEVEL 2 (OPERATIONAL)",
  authenticatedAt: null,
};

export function AuthProvider({ children }) {
  const [operator, setOperator] = useState(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (operator) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(operator));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, [operator]);

  const login = async (email, password) => {
    setLoading(true);
    // Simulate real aerospace session handshake
    await new Promise((resolve) => setTimeout(resolve, 850));

    if (!email || !password) {
      setLoading(false);
      throw new Error("OPERATOR CREDENTIALS REQUIRED");
    }

    if (password.length < 6) {
      setLoading(false);
      throw new Error("AUTHENTICATION REJECTED: PASSWORD MUST BE AT LEAST 6 CHARACTERS");
    }

    const session = {
      ...DEFAULT_OPERATOR,
      email,
      callsign: `OP // ${email.split("@")[0].toUpperCase()}`,
      authenticatedAt: new Date().toISOString(),
    };

    setOperator(session);
    setLoading(false);
    return session;
  };

  const signup = async ({ name, email, organization, password }) => {
    setLoading(true);
    await new Promise((resolve) => setTimeout(resolve, 1100));

    if (!name || !email || !password) {
      setLoading(false);
      throw new Error("REQUIRED REGISTRATION FIELDS MISSING");
    }

    if (password.length < 6) {
      setLoading(false);
      throw new Error("SECURITY POLICY: PASSWORD MUST BE AT LEAST 6 CHARACTERS");
    }

    const session = {
      callsign: `OP // ${name.toUpperCase()}`,
      email,
      role: "MISSION OPERATOR",
      organization: organization || "SPACE SITUATIONAL AWARENESS",
      clearance: "LEVEL 1 (GENERAL)",
      authenticatedAt: new Date().toISOString(),
    };

    setOperator(session);
    setLoading(false);
    return session;
  };

  const logout = () => {
    setOperator(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <AuthContext.Provider
      value={{
        operator,
        isAuthenticated: Boolean(operator),
        loading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
