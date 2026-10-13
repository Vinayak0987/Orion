// OAuthButtons — the "or, with one of the below" provider list (Google,
// GitHub, Magic). Presentational: clicking a button calls `onProvider(id)`
// so the parent decides what a provider sign-in actually does. `verb` lets
// the label read "Sign up with" vs "Sign in with".

function GoogleIcon() {
  return (
    <svg className="oauth-icon google-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M23.49 12.27c0-.79-.07-1.55-.2-2.27H12v4.3h6.44a5.51 5.51 0 0 1-2.39 3.62v3.01h3.87c2.27-2.09 3.57-5.17 3.57-8.66Z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.95-2.91l-3.87-3.01c-1.07.72-2.44 1.15-4.08 1.15-3.13 0-5.78-2.11-6.73-4.95H1.27v3.1A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 0 1 4.9 12c0-.79.14-1.56.37-2.28v-3.1H1.27A12 12 0 0 0 0 12c0 1.94.46 3.77 1.27 5.38l4-3.1Z" />
      <path fill="#EA4335" d="M12 4.77c1.76 0 3.34.61 4.59 1.81l3.44-3.44C17.95 1.12 15.24 0 12 0A12 12 0 0 0 1.27 6.62l4 3.1C6.22 6.88 8.87 4.77 12 4.77Z" />
    </svg>
  );
}

function GitHubIcon() {
  return (
    <svg className="oauth-icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 .3a12 12 0 0 0-3.8 23.4c.6.1.8-.3.8-.6v-2.2c-3.3.7-4-1.6-4-1.6-.6-1.4-1.3-1.8-1.3-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.4 1 .1-.8.4-1.3.8-1.6-2.7-.3-5.4-1.3-5.4-5.9 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.6 1.7.2 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.6-2.7 5.6-5.4 5.9.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A12 12 0 0 0 12 .3" />
    </svg>
  );
}

function MagicIcon() {
  return (
    <svg className="oauth-icon" viewBox="0 0 24 24" fill="none" stroke="#7a5bff" strokeWidth="1.6" aria-hidden="true">
      <path d="M9 2l1.8 5.2L16 9l-5.2 1.8L9 16l-1.8-5.2L2 9l5.2-1.8L9 2z" />
      <path d="M18.5 14l.9 2.6 2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.6z" />
    </svg>
  );
}

const PROVIDERS = [
  { id: "google", label: "Google", Icon: GoogleIcon, className: "" },
  { id: "github", label: "GitHub", Icon: GitHubIcon, className: "github" },
  { id: "magic", label: "Magic", Icon: MagicIcon, className: "" },
];

export default function OAuthButtons({ verb = "Sign in", onProvider }) {
  return (
    <div className="oauth-list">
      {PROVIDERS.map(({ id, label, Icon, className }) => (
        <button
          key={id}
          type="button"
          className={`oauth-button ${className}`.trim()}
          onClick={() => onProvider?.(id)}
        >
          <Icon />
          {`${verb} with ${label}`}
        </button>
      ))}
    </div>
  );
}
