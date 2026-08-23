import { useEffect, useState } from "react";
import { useRouter } from "../../context/Router";
import RadarLogo from "../shared/RadarLogo";

export default function AuthTransition({ operator, onComplete }) {
  const { navigate } = useRouter();
  const [step, setStep] = useState(1);

  useEffect(() => {
    const t1 = setTimeout(() => setStep(2), 350);
    const t2 = setTimeout(() => setStep(3), 750);
    const t3 = setTimeout(() => {
      onComplete?.();
      navigate("/dashboard");
    }, 1150);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, [navigate, onComplete]);

  return (
    <div className="auth-transition-overlay">
      <div className="auth-transition-card hud-frame mono">
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}>
          <RadarLogo height={48} className="auth-transition-radar-logo" />
        </div>


        <div className="eyebrow" style={{ color: "var(--signal)", textAlign: "center", fontSize: 11 }}>
          ✓ AUTHENTICATION VERIFIED
        </div>

        <div className="transition-meta-box">
          <div className="transition-row">
            <span className="eyebrow">OPERATOR</span>
            <strong>{operator?.callsign || "OP // AUTHORIZED"}</strong>
          </div>
          <div className="transition-row">
            <span className="eyebrow">CLEARANCE</span>
            <span>{operator?.clearance || "LEVEL 2 (OPERATIONAL)"}</span>
          </div>
          <div className="transition-row">
            <span className="eyebrow">NODE STATUS</span>
            <span style={{ color: "var(--risk-nominal)" }}>CONNECTED // SGP4 STREAM ACTIVE</span>
          </div>
        </div>

        <div className="transition-status-log">
          <div style={{ color: step >= 1 ? "var(--signal)" : "var(--text-dim)" }}>
            [1/3] VERIFYING CRYPTOGRAPHIC HANDSHAKE... {step >= 1 ? "OK" : ""}
          </div>
          <div style={{ color: step >= 2 ? "var(--signal)" : "var(--text-dim)" }}>
            [2/3] ALLOCATING ORBITAL TELEMETRY CHANNELS... {step >= 2 ? "OK" : ""}
          </div>
          <div style={{ color: step >= 3 ? "var(--signal)" : "var(--text-dim)" }}>
            [3/3] INITIALIZING 3D CESIUM ENVIRONMENT... {step >= 3 ? "READY" : ""}
          </div>
        </div>

        <div className="auth-progress-bar" style={{ marginTop: 14 }}>
          <div
            className="auth-progress-fill"
            style={{
              width: step === 1 ? "35%" : step === 2 ? "70%" : "100%",
              transition: "width 0.3s ease",
            }}
          />
        </div>
      </div>
    </div>
  );
}
