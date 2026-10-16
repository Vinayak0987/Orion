// Orion frontend — main app shell.
//
// Routing:
//   • /login   → AuthScreen (sign in)
//   • /signup  → AuthScreen (sign up)
//   • /*       → PlatformApp (authenticated) or redirect to /login
//
// Before any route renders, the intro splash plays once per browser session,
// and the landing page shows once per session to logged-out visitors.

import { useCallback, useEffect, useState } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

import AuthScreen from "./auth/AuthScreen";
import {
  hasSeenLanding,
  logout as doLogout,
  markIntroSeen,
  markLandingSeen,
  restoreSession,
} from "./auth/session";
import FadeIn from "./components/FadeIn";
import Loader from "./components/Loader";
import IntroScreen from "./intro/IntroScreen";
import LandingPage from "./landing/LandingPage";
import PlatformApp from "./PlatformApp";

// ============================================================================
// Auth route wrapper
// ============================================================================

function AuthRoute({ mode, isAuthed, onLogin }) {
  const navigate = useNavigate();

  if (isAuthed) {
    return <Navigate to="/" replace />;
  }

  const handleAuthenticated = (user) => {
    onLogin(user);
    navigate("/", { replace: true });
  };

  // key on mode so switching /login <-> /signup remounts and re-runs the fade.
  return (
    <FadeIn key={mode}>
      <AuthScreen mode={mode} onAuthenticated={handleAuthenticated} />
    </FadeIn>
  );
}

// ============================================================================
// App root
// ============================================================================

export default function App() {
  const navigate = useNavigate();

  // Intro splash plays once per browser session, before any route renders.
  const [showIntro, setShowIntro] = useState(
    () => sessionStorage.getItem("orion.introSeen") !== "1"
  );
  const finishIntro = useCallback(() => {
    markIntroSeen();
    setShowIntro(false);
  }, []);

  // Landing page shows once per session after the intro, before the login
  // screen — but only for logged-out visitors. Skipped if the session was
  // already restored (returning user) or the user is deep-linking to /login|/signup.
  const [showLanding, setShowLanding] = useState(() => !hasSeenLanding());
  const dismissLanding = useCallback(() => {
    markLandingSeen();
    setShowLanding(false);
  }, []);

  // Auth state. `authReady` guards against redirecting to /login before we
  // have tried to restore a session from the refresh cookie on a fresh load.
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    restoreSession().then((restored) => {
      if (!cancelled) {
        setUser(restored);
        setAuthReady(true);
      }
    });
    return () => { cancelled = true; };
  }, []);

  const handleLogin = useCallback((loggedInUser) => {
    setUser(loggedInUser ?? { authenticated: true });
  }, []);

  const handleLogout = useCallback(async () => {
    await doLogout();
    setUser(null);
  }, []);

  // Intro gate — renders before anything else, once per browser session.
  if (showIntro) {
    return <IntroScreen onComplete={finishIntro} />;
  }

  const isAuthed = user !== null;

  // Landing page — shown to logged-out visitors once per session, after the
  // intro and before the login screen. Skipped for returning users and
  // anyone deep-linking straight to /login or /signup.
  const onAuthPath =
    window.location.pathname === "/login" ||
    window.location.pathname === "/signup";
  if (authReady && !isAuthed && showLanding && !onAuthPath) {
    const goAuth = (path) => {
      dismissLanding();
      navigate(path);
    };
    return (
      <LandingPage
        onGetStarted={() => goAuth("/signup")}
        onSignIn={() => goAuth("/login")}
      />
    );
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={<AuthRoute mode="signin" isAuthed={isAuthed} onLogin={handleLogin} />}
      />
      <Route
        path="/signup"
        element={<AuthRoute mode="signup" isAuthed={isAuthed} onLogin={handleLogin} />}
      />
      <Route
        path="/*"
        element={
          !authReady ? (
            <AuthLoading />
          ) : isAuthed ? (
            <PlatformApp onLogout={handleLogout} />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
    </Routes>
  );
}

// Brief neutral screen shown only while the initial session restore is in
// flight, so a logged-in user isn't flashed to /login on reload.
function AuthLoading() {
  return <Loader label="Loading" />;
}
