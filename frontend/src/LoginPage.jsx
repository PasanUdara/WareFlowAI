import { useEffect, useRef } from 'react';

const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';
const googleScriptUrl = 'https://accounts.google.com/gsi/client';

function GoogleMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 48 48" width="18" height="18">
      <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z" />
      <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.91c-.58 2.96-2.26 5.48-4.75 7.18l7.73 6C44.4 37.97 46.98 31.88 46.98 24.55Z" />
      <path fill="#FBBC05" d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.89.93 7.58 2.56 10.78l7.97-6.19Z" />
      <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.8l-7.73-6c-2.14 1.44-4.88 2.3-8.17 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z" />
    </svg>
  );
}

export default function LoginPage({
  loginError,
  loginLoading,
  googleError,
  googleLoading,
  onLogin,
  onGoogleCredential,
  onOpenRegistration
}) {
  const googleButtonRef = useRef(null);
  const googleCallbackRef = useRef(onGoogleCredential);

  useEffect(() => {
    googleCallbackRef.current = onGoogleCredential;
  }, [onGoogleCredential]);

  useEffect(() => {
    if (!googleClientId || !googleButtonRef.current) return undefined;

    let initialized = false;
    const renderGoogleButton = () => {
      const googleIdentity = window.google?.accounts?.id;
      const button = googleButtonRef.current;
      if (!googleIdentity || !button || initialized) return;

      initialized = true;
      googleIdentity.initialize({
        client_id: googleClientId,
        callback: (response) => {
          if (response.credential) {
            googleCallbackRef.current(response.credential);
          }
        }
      });
      googleIdentity.renderButton(button, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'continue_with',
        shape: 'rectangular',
        logo_alignment: 'left',
        width: Math.min(button.clientWidth || 360, 400)
      });
    };

    const existingScript = document.querySelector(`script[src="${googleScriptUrl}"]`);
    if (existingScript) {
      renderGoogleButton();
      existingScript.addEventListener('load', renderGoogleButton);
      return () => existingScript.removeEventListener('load', renderGoogleButton);
    }

    const script = document.createElement('script');
    script.src = googleScriptUrl;
    script.async = true;
    script.defer = true;
    script.addEventListener('load', renderGoogleButton);
    document.head.appendChild(script);

    return () => script.removeEventListener('load', renderGoogleButton);
  }, []);

  return (
    <main className="registration-screen">
      <section className="registration-panel" aria-labelledby="login-title">
        <div className="registration-aside">
          <button type="button" className="registration-brand" onClick={onOpenRegistration} aria-label="Go to WareFlow account registration">
            <span className="registration-brand-mark">WF</span>
            <span>WareFlow <strong>AI</strong></span>
          </button>
          <div className="registration-aside-copy">
            <span className="registration-eyebrow">WAREHOUSE OPERATIONS PLATFORM</span>
            <h1>Your warehouse, in sync.</h1>
            <p>Sign in to coordinate your fleet, monitor live operations, and keep every workflow moving.</p>
          </div>
          <div className="registration-aside-foot">One connected view of your warehouse operations.</div>
        </div>

        <div className="registration-content login-content">
          <div className="registration-mobile-brand">
            <span className="registration-brand-mark">WF</span>
            <span>WareFlow <strong>AI</strong></span>
          </div>

          <div className="registration-heading">
            <span className="registration-eyebrow">WELCOME BACK</span>
            <h2 id="login-title">Sign in to WareFlow</h2>
            <p>Enter your account details to open your workspace.</p>
          </div>

          {loginError && <div className="registration-error" role="alert">{loginError}</div>}
          {googleError && <div className="registration-error" role="alert">{googleError}</div>}

          <form className="registration-form" onSubmit={onLogin}>
            <label>
              Work email or username
              <input
                type="text"
                name="username"
                placeholder="you@company.com"
                autoComplete="username"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                name="password"
                placeholder="Enter your password"
                autoComplete="current-password"
                required
              />
            </label>

            <button type="submit" className="registration-submit" disabled={loginLoading || googleLoading}>
              {loginLoading ? 'Signing in…' : 'Sign in'}
              {!loginLoading && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <div className="login-divider"><span>OR CONTINUE WITH</span></div>

          {googleClientId ? (
            <div className={`google-signin-slot ${googleLoading ? 'is-loading' : ''}`}>
              <div ref={googleButtonRef} />
              {googleLoading && <span className="google-loading-label">Verifying your Google account…</span>}
            </div>
          ) : (
            <button type="button" className="google-signin-unconfigured" disabled>
              <GoogleMark />
              <span>Continue with Google</span>
            </button>
          )}
          {!googleClientId && (
            <p className="google-setup-hint">Google sign-in is unavailable until an OAuth Client ID is configured.</p>
          )}

          <p className="registration-signin-prompt">
            Don’t have an account? <button type="button" onClick={onOpenRegistration}>Create an account</button>
          </p>
        </div>
      </section>
    </main>
  );
}
