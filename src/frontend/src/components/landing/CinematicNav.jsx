import { useRouter } from "../../context/Router";
import { useAuth } from "../../context/AuthContext";
import RadarLogo from "../shared/RadarLogo";

const NAV_ITEMS = [
  { label: "TRACKING",  route: "/tracking" },
  { label: "ANALYTICS", route: "/analytics" },
  { label: "ABOUT",     route: "/about" },
];

export default function CinematicNav() {
  const { navigate, currentPath } = useRouter();
  const { isAuthenticated } = useAuth();

  const handleNav = (item) => {
    if (item.route) {
      navigate(item.route);
    }
  };

  const handleSignIn = () => navigate("/sign-in");
  const handleDashboard = () => navigate("/dashboard");

  return (
    <nav className="cine-nav" aria-label="Primary navigation">
      {/* Left: RADAR logo */}
      <div
        className="cine-nav-logo"
        onClick={() => navigate("/")}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && navigate("/")}
        aria-label="RADAR home"
      >
        <RadarLogo height={52} className="cine-logo-img" />
      </div>

      {/* Right: nav links + auth action */}
      <div className="cine-nav-right">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.label}
            type="button"
            className={`cine-nav-link${currentPath === item.route ? " cine-nav-link--active" : ""}`}
            onClick={() => handleNav(item)}
          >
            {item.label}
          </button>
        ))}

        <div className="cine-nav-divider-v" aria-hidden="true" />

        {isAuthenticated ? (
          <button type="button" className="cine-nav-link cine-nav-link--auth" onClick={handleDashboard}>
            ENTER RADAR
          </button>
        ) : (
          <button type="button" className="cine-nav-link cine-nav-link--auth" onClick={handleSignIn}>
            SIGN IN
          </button>
        )}
      </div>
    </nav>
  );
}
