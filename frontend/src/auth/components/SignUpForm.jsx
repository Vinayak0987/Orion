// SignUpForm — the "Sign Up" glass card. Controlled inputs for full name,
// email, password and confirm-password, with client-side validation that runs
// on submit, on blur, and live (to clear a message once a field is corrected).
// On a valid submit it calls `onSubmit({ fullName, email, password })`.

import { useState } from "react";

import OAuthButtons from "./OAuthButtons";
import PasswordField from "./PasswordField";
import { validateField, validateSignUp } from "../validation";

export default function SignUpForm({ onSubmit, onOAuth, onSwitch, submitting = false, serverError = "" }) {
  const [values, setValues] = useState({
    fullName: "",
    email: "",
    password: "",
    confirm: "",
  });
  const [errors, setErrors] = useState({});

  // Update a field. If it (or a dependent field) was already showing an error,
  // re-validate live so the message clears as soon as the input is valid.
  function setField(field, value) {
    const next = { ...values, [field]: value };
    setValues(next);
    setErrors((prev) => {
      const updated = { ...prev };
      if (prev[field] !== undefined) {
        updated[field] = validateField("signup", field, next);
        if (!updated[field]) delete updated[field];
      }
      // Keep confirm in step with password edits.
      if (field === "password" && prev.confirm !== undefined) {
        updated.confirm = validateField("signup", "confirm", next);
        if (!updated.confirm) delete updated.confirm;
      }
      return updated;
    });
  }

  function handleBlur(field) {
    setTouched((t) => ({ ...t, [field]: true }));
    const message = validateField("signup", field, values);
    setErrors((prev) => {
      const updated = { ...prev };
      if (message) updated[field] = message;
      else delete updated[field];
      return updated;
    });
  }

  function handleSubmit(e) {
    e.preventDefault();
    const found = validateSignUp(values);
    setErrors(found);
    if (Object.keys(found).length === 0) {
      onSubmit?.({
        fullName: values.fullName.trim(),
        email: values.email.trim(),
        password: values.password,
      });
    }
  }

  return (
    <div className="card" id="card-signup">
      <h1>Sign Up</h1>
      <form onSubmit={handleSubmit} noValidate>
        <label>
          <span>Full Name</span>
          <input
            type="text"
            placeholder="John Doe"
            value={values.fullName}
            onChange={(e) => setField("fullName", e.target.value)}
            onBlur={() => handleBlur("fullName")}
            autoComplete="name"
            aria-invalid={errors.fullName ? "true" : undefined}
            aria-describedby={errors.fullName ? "signup-name-error" : undefined}
          />
          {errors.fullName && (
            <span className="field-error" id="signup-name-error" role="alert">
              {errors.fullName}
            </span>
          )}
        </label>
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
            aria-describedby={errors.email ? "signup-email-error" : undefined}
          />
          {errors.email && (
            <span className="field-error" id="signup-email-error" role="alert">
              {errors.email}
            </span>
          )}
        </label>
        <PasswordField
          id="pw-signup"
          value={values.password}
          onChange={(v) => setField("password", v)}
          onBlur={() => handleBlur("password")}
          autoComplete="new-password"
          error={errors.password}
        />
        <PasswordField
          id="pw-signup-confirm"
          label="Confirm Password"
          placeholder="Re-enter your password"
          value={values.confirm}
          onChange={(v) => setField("confirm", v)}
          onBlur={() => handleBlur("confirm")}
          autoComplete="new-password"
          error={errors.confirm}
        />
        <button className="primary" type="submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Sign up with Email"}
        </button>
        {serverError && (
          <div className="field-error" role="alert" style={{ marginTop: 10 }}>
            {serverError}
          </div>
        )}
      </form>

      <div className="or">
        <span>Or, with one of the below</span>
      </div>

      <OAuthButtons verb="Sign up" onProvider={onOAuth} />

      <div className="switch">
        Already have an account?
        <button type="button" onClick={onSwitch}>
          Sign In
        </button>
      </div>

      <div className="legal">
        By creating an account, you acknowledge and agree to our
        <a href="#">Terms of Service</a> and <a href="#">Privacy Policy</a>.
      </div>
    </div>
  );
}
