// validation — dependency-free validators shared by the auth forms.
//
// Two contexts with deliberately different rules:
//   • Sign up  — creating an account, so enforce a strong password and a
//                sensible name. This is where composition rules belong.
//   • Sign in  — authenticating an existing account. We must NOT re-impose
//                composition rules (the stored password may predate them);
//                a non-empty password is all we check client-side.
//
// Every validator returns "" when valid, or a human-readable message.

// Pragmatic email check: non-empty local part, single @, dotted domain, no
// spaces. Not RFC-5322-exhaustive on purpose — catches common mistakes without
// rejecting valid addresses. Also guards against a trailing dot / consecutive
// dots in the domain.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email) {
  const value = (email || "").trim();
  if (!value) return "Email is required.";
  if (value.length > 254) return "Email is too long.";
  if (!EMAIL_RE.test(value)) return "Enter a valid email address.";
  if (/\.\./.test(value) || value.endsWith(".")) {
    return "Enter a valid email address.";
  }
  return "";
}

export function validateFullName(name) {
  const value = (name || "").trim();
  if (!value) return "Full name is required.";
  if (value.length < 2) return "Please enter your full name.";
  if (value.length > 80) return "Name is too long.";
  return "";
}

// Sign-up password: strength rules.
export function validateNewPassword(password) {
  const value = password || "";
  if (!value) return "Password is required.";
  if (value.length < 8) return "Password must be at least 8 characters.";
  if (value.length > 128) return "Password is too long.";
  if (!/[a-z]/.test(value)) return "Add at least one lowercase letter.";
  if (!/[A-Z]/.test(value)) return "Add at least one uppercase letter.";
  if (!/[0-9]/.test(value)) return "Add at least one number.";
  return "";
}

// Sign-in password: presence only — do not re-check composition here.
export function validateExistingPassword(password) {
  if (!password) return "Password is required.";
  return "";
}

export function validateConfirmPassword(password, confirm) {
  if (!confirm) return "Please confirm your password.";
  if (password !== confirm) return "Passwords do not match.";
  return "";
}

// ---------------------------------------------------------------- form-level
// Compact helpers that validate a whole form's values and return a map of
// { field: message } containing only the failing fields.

function pruneEmpty(map) {
  Object.keys(map).forEach((k) => {
    if (!map[k]) delete map[k];
  });
  return map;
}

export function validateSignUp({ fullName, email, password, confirm }) {
  return pruneEmpty({
    fullName: validateFullName(fullName),
    email: validateEmail(email),
    password: validateNewPassword(password),
    confirm: validateConfirmPassword(password, confirm),
  });
}

export function validateSignIn({ email, password }) {
  return pruneEmpty({
    email: validateEmail(email),
    password: validateExistingPassword(password),
  });
}

// Validate a single named field within a form context ("signup" | "signin").
// Used for on-blur / live validation so messages appear and clear per field.
export function validateField(context, field, values) {
  switch (field) {
    case "fullName":
      return validateFullName(values.fullName);
    case "email":
      return validateEmail(values.email);
    case "password":
      return context === "signup"
        ? validateNewPassword(values.password)
        : validateExistingPassword(values.password);
    case "confirm":
      return validateConfirmPassword(values.password, values.confirm);
    default:
      return "";
  }
}
