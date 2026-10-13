// SignInForm — the "Welcome" glass card. Controlled inputs for email and
// password, with client-side validation on submit, on blur, and live (to clear
// a message once corrected). Note: sign-in only checks that the password is
// present — it must NOT re-impose sign-up composition rules. On a valid submit
// it calls `onSubmit({ email, password })`.

import { useState } from "react";

import OAuthButtons from "./OAuthButtons";
import PasswordField from "./PasswordField";
import { validateField, validateSignIn } from "../validation";

export default function SignInForm({ onSubmit, onOAuth, onSwitch, onForgot, submitting = false, serverError = "" }) {
  const [values, setValues] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});

  function setField(field, value) {
    const next = { ...values, [field]: value };
    setValues(next);
    setErrors((prev) => {
      if (prev[field] === undefined) return prev;
      const updated = { ...prev };
      updated[field] = validateField("signin", field, next);
      if (!updated[field]) delete updated[field];
      return updated;
    });
  }

  function handleBlur(field) {
    const message = validateField("signin", field, values);
    setErrors((prev) => {
      const updated = { ...prev };
      if (message) updated[field] = message;
      else delete updated[field];
      return updated;
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    const found = validateSignIn(values);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      onSubmit?.({ email: values.email.trim(), password: values.password });
    }
  }

  return (
    <div className="card signin-card" id="card-signin">
      <h1>Welcome</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          <span>Email</span>
          <input
            type="email"
            placeholder="name@example.com"
            value={values.email}
            onChange={(e) => setField("email", e.target.value)}
            onBlur={() => handleBlur("email")}
            autoComplete="email"
            aria-invalid={errors.email ? "true" : undefined}
            aria-describedby={errors.email ? "signin-email-error" : undefined}
          />
          {errors.email && (
            <span className="field-error" id="signin-email-error" role="alert">
              {errors.email}
            </span>
          )}
        </label>
        <PasswordField
          id="pw-signin"
          value={values.password}
          onChange={(v) => setField("password", v)}
          onBlur={() => handleBlur("password")}
          autoComplete="current-password"
          error={errors.password}
        />
        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Login"}
        </button>
        {serverError && (
          <div className="field-error" role="alert" style={{ marginTop: 10 }}>
            {serverError}
          </div>
        )}
      </form>

      <div className="forgot">
        Can&apos;t remember your password?
        <button type="button" onClick={onForgot}>
          Reset now
        </button>
      </div>

      <div className="or">
        <span>Or, with one of the below</span>
      </div>

      <OAuthButtons verb="Sign in" onProvider={onOAuth} />

      <div className="switch">
        Don&apos;t have an account?
        <button type="button" onClick={onSwitch}>
          Sign Up
        </button>
      </div>

      <div className="legal">
        By creating an account, you acknowledge and agree to our
        <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>.
      </div>
    </div>
  );
}
