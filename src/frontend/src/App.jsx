import { useEffect, useState } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { RouterProvider, useRouter } from "./context/Router";
import LandingPage from "./components/landing/LandingPage";
import TrackingPage from "./components/landing/TrackingPage";
import AnalyticsPage from "./components/landing/AnalyticsPage";
import AboutPage from "./components/landing/AboutPage";
import AuthLayout from "./components/auth/AuthLayout";
import SignInForm from "./components/auth/SignInForm";
import SignUpForm from "./components/auth/SignUpForm";
import AuthTransition from "./components/auth/AuthTransition";
import RadarDashboard from "./components/RadarDashboard";
import { mockDashboardStats } from "./data/mockData";
import { loadLiveDashboardData } from "./utils/liveData";
import { useDataset } from "./context/DatasetContext";

function AppContent() {
  const { currentPath } = useRouter();
  const { isAuthenticated } = useAuth();
  const { dataset } = useDataset();

  const [transitioningOperator, setTransitioningOperator] = useState(null);
  const [dashboardStats, setDashboardStats] = useState(mockDashboardStats);
  const [objectsCount, setObjectsCount] = useState(100);

  useEffect(() => {
    let cancelled = false;
    loadLiveDashboardData(dataset)
      .then((live) => {
        if (cancelled) return;
        setDashboardStats(live.dashboardStats);
        setObjectsCount(live.objects?.length || 100);
      })
      .catch((err) => {
        console.warn("[RADAR] AppContent stats load fallback:", err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [dataset]);

  const handleAuthSuccess = (session) => {
    setTransitioningOperator(session);
  };

  const handleTransitionComplete = () => {
    setTransitioningOperator(null);
  };

  // If transition overlay is active
  if (transitioningOperator) {
    return (
      <AuthTransition
        operator={transitioningOperator}
        onComplete={handleTransitionComplete}
      />
    );
  }

  // Handle Route Matching
  if (currentPath === "/sign-in") {
    return (
      <AuthLayout
        title="SYSTEM ACCESS // SIGN IN"
        subtitle="OPERATOR CLEARANCE TERMINAL"
      >
        <SignInForm onAuthSuccess={handleAuthSuccess} />
      </AuthLayout>
    );
  }

  if (currentPath === "/sign-up") {
    return (
      <AuthLayout
        title="OPERATOR REGISTRATION"
        subtitle="NEW CLEARANCE REQUEST"
      >
        <SignUpForm onAuthSuccess={handleAuthSuccess} />
      </AuthLayout>
    );
  }

  if (currentPath === "/dashboard") {
    if (!isAuthenticated) {
      return (
        <AuthLayout
          title="OPERATIONAL CLEARANCE REQUIRED"
          subtitle="AUTHENTICATED SESSION NEEDED"
        >
          <div className="auth-error-banner mono" style={{ marginBottom: 16 }}>
            <span>ACCESS RESTRICTED: PLEASE SIGN IN TO ACCESS THE 3D RADAR CONSOLE</span>
          </div>
          <SignInForm onAuthSuccess={handleAuthSuccess} />
        </AuthLayout>
      );
    }
    return <RadarDashboard />;
  }

  // Standalone info pages
  if (currentPath === "/tracking") {
    return <TrackingPage />;
  }

  if (currentPath === "/analytics") {
    return <AnalyticsPage />;
  }

  if (currentPath === "/about") {
    return <AboutPage />;
  }

  // Default: Landing Page (/)
  return (
    <LandingPage
      dashboardStats={dashboardStats}
      objectsCount={objectsCount}
    />
  );
}

export default function App() {
  return (
    <AuthProvider>
      <RouterProvider>
        <AppContent />
      </RouterProvider>
    </AuthProvider>
  );
}
