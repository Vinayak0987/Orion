// AuthScreen — the auth feature's top-level container. Composes the themed
// background, the streamed OrionAI logo + tagline, the theme switcher, and
// toggles between the Sign Up and Sign In cards.
//
// It owns only UI concerns (which card is shown, the theme, the intro typing).
// Actual authentication is delegated upward via props so this stays decoupled
// from any backend:
//   onAuthenticated({ mode, provider?, ...credentials })
//     called on a successful email submit or an OAuth click. Today the parent
//     just treats any submit as success; wire it to a real API later.

import { useCallback, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import AuthBackground from "./components/AuthBackground";
import OrionLogo from "./components/OrionLogo";
import SignInForm from "./components/SignInForm";
import SignUpForm from "./components/SignUpForm";
import ThemeSwitcher from "./components/ThemeSwitcher";
import VisualLab from "./components/VisualLab";
import { authApi } from "./authApi";
import useAuthTheme from "./useAuthTheme";
import useStreamingText from "./useStreamingText";
import "./auth.css";

const TAGLINE = "The Agentic System for Business planning and Operation";

// AuthScreen is route-driven: the parent route decides the mode ("signup" for
// /signup, "signin" for /login). Switching between the two navigates to the
// other real path rather than toggling internal state.
export default function AuthScreen({ mode = "signup", onAuthenticated, showVisualLab = true }) {
  const navigate = useNavigate();
  const { theme, setTheme } = useAuthTheme();
  const [taglineReady, setTaglineReady] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const logoRef = useRef(null);
  const taglineRef = useRef(null);

  // Stream the wordmark, then chain the tagline once it finishes.
  const onLogoDone = useCallback(() => setTaglineReady(true), []);
  useStreamingText(logoRef, "OrionAI", {
    mode: "char",
    speed: 95,
    jitter: 70,
    onDone: onLogoDone,
  });
  useStreamingText(taglineRef, TAGLINE, {
    enabled: taglineReady,
    mode: "word",
    speed: 110,
    jitter: 60,
  });

  // Email/password submit -> call the real backend. On success the backend sets
  // the refresh cookie and returns an access token + user; we lift the user up.
  const handleEmailSubmit = useCallback(
    async (credentials) => {
      setFormError("");
      setSubmitting(true);
      try {
        const result =
          mode === "signup"
            ? await authApi.signup(credentials)
            : await authApi.login(credentials);
        onAuthenticated?.(result.user);
      } catch (err) {
        setFormError(err?.message || "Something went wrong. Please try again.");
      } finally {
        setSubmitting(false);
      }
    },
    [mode, onAuthenticated]
  );

  // OAuth is intentionally stubbed for now (no provider flow). Surface a clear
  // message rather than silently doing nothing.
  const handleOAuth = useCallback((provider) => {
    setFormError(
      `${provider[0].toUpperCase()}${provider.slice(1)} sign-in isn't available yet — use email for now.`
    );
  }, []);

  const handleForgot = useCallback(() => {
    setFormError("Password reset isn't available yet.");
  }, []);

  const showSignup = mode === "signup";

  const card = useMemo(
    () =>
      showSignup ? (
        <SignUpForm
          onSubmit={handleEmailSubmit}
          onOAuth={handleOAuth}
          onSwitch={() => navigate("/login")}
          submitting={submitting}
          serverError={formError}
        />
      ) : (
        <SignInForm
          onSubmit={handleEmailSubmit}
          onOAuth={handleOAuth}
          onSwitch={() => navigate("/signup")}
          onForgot={handleForgot}
          submitting={submitting}
          serverError={formError}
        />
      ),
    [showSignup, handleEmailSubmit, handleOAuth, handleForgot, navigate, submitting, formError]
  );

  return (
    <div className="auth-page">
      <ThemeSwitcher theme={theme} onChange={setTheme} />
      {showVisualLab && <VisualLab theme={theme} />}

      <AuthBackground />

      <div className="content">
        <div className="left">
          <div className="nebula" aria-hidden="true" />
          <OrionLogo textRef={logoRef} />
          <h2>
            <span ref={taglineRef} />
          </h2>
        </div>

        {card}
      </div>
    </div>
  );
}
