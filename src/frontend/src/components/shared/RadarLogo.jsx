import radarLogoUrl from "../../assets/radar-logo.png";

export default function RadarLogo({ height = 38, className = "", style = {}, alt = "RADAR — Risk Assessment & Debris Avoidance Routing", ...props }) {
  return (
    <img
      src={radarLogoUrl}
      alt={alt}
      className={`radar-brand-logo ${className}`}
      style={{
        height: typeof height === "number" ? `${height}px` : height,
        width: "auto",
        maxWidth: "100%",
        objectFit: "contain",
        display: "block",
        ...style,
      }}
      {...props}
    />
  );
}
