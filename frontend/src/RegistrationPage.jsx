import { useState } from 'react';
import { registerUser } from './api';

export default function RegistrationPage({
  onBackToLogin,
  onRegistered,
  googleCredential = '',
  googleProfile = {},
  onGoogleRegister
}) {
  const isGoogleRegistration = Boolean(googleCredential);
  const [fullName, setFullName] = useState(googleProfile.full_name || '');
  const [companyName, setCompanyName] = useState('');
  const [email, setEmail] = useState(googleProfile.email || '');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!isGoogleRegistration && password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (!termsAccepted) {
      setError('Please accept the Terms of Service and Privacy Policy to continue.');
      return;
    }

    setLoading(true);
    try {
      if (isGoogleRegistration) {
        await onGoogleRegister(googleCredential, {
          full_name: fullName.trim(),
          company_name: companyName.trim(),
          terms_accepted: termsAccepted
        });
      } else {
        const data = await registerUser({
          password,
          confirm_password: confirmPassword,
          email: email.trim(),
          full_name: fullName.trim(),
          company_name: companyName.trim(),
          terms_accepted: termsAccepted
        });
        onRegistered(data);
      }
    } catch (registrationError) {
      setError(registrationError.message || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="registration-screen">
      <section className="registration-panel" aria-labelledby="registration-title">
        <div className="registration-aside">
          <button type="button" className="registration-brand" onClick={onBackToLogin} aria-label="Back to WareFlow sign in">
            <span className="registration-brand-mark">WF</span>
            <span>WareFlow <strong>AI</strong></span>
          </button>
          <div className="registration-aside-copy">
            <span className="registration-eyebrow">WAREHOUSE OPERATIONS PLATFORM</span>
            <h1>Run your warehouse with clarity.</h1>
            <p>Create your workspace to coordinate your fleet, monitor operations, and keep every workflow moving.</p>
          </div>
          <div className="registration-aside-foot">One connected view of your warehouse operations.</div>
        </div>

        <div className="registration-content">
          <div className="registration-mobile-brand">
            <span className="registration-brand-mark">WF</span>
            <span>WareFlow <strong>AI</strong></span>
          </div>
          <button type="button" className="registration-back-link" onClick={onBackToLogin}>
            <span aria-hidden="true">←</span> Back to sign in
          </button>

          <div className="registration-heading">
            <span className="registration-eyebrow">GET STARTED</span>
            <h2 id="registration-title">{isGoogleRegistration ? 'Complete your account' : 'Create your account'}</h2>
            <p>{isGoogleRegistration ? 'Add your warehouse details and accept the terms to finish signing up with Google.' : 'Set up your warehouse workspace in a few steps.'}</p>
          </div>

          {error && <div className="registration-error" role="alert">{error}</div>}

          <form className="registration-form" onSubmit={handleSubmit}>
            <label>
              Full name
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your full name"
                maxLength={120}
                autoComplete="name"
                required
              />
            </label>

            <label>
              Company / Warehouse name
              <input
                type="text"
                value={companyName}
                onChange={(event) => setCompanyName(event.target.value)}
                placeholder="Your company or warehouse"
                maxLength={120}
                autoComplete="organization"
                required
              />
            </label>

            <label>
              Work email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
                required
                readOnly={isGoogleRegistration}
              />
              <span className="registration-hint">Use this email to sign in to your account.</span>
            </label>

            {!isGoogleRegistration && <div className="registration-password-grid">
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Create a password"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label>
                Confirm password
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  placeholder="Enter it again"
                  minLength={8}
                  autoComplete="new-password"
                  required
                />
              </label>
            </div>}
            {!isGoogleRegistration && <p className="registration-hint registration-password-hint">Use at least 8 characters, including uppercase, lowercase, and a number.</p>}

            <label className="registration-consent">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(event) => setTermsAccepted(event.target.checked)}
                required
              />
              <span>I agree to the <strong>Terms of Service</strong> and <strong>Privacy Policy</strong>.</span>
            </label>

            <button type="submit" className="registration-submit" disabled={loading}>
              {loading ? 'Creating your account…' : isGoogleRegistration ? 'Continue with Google' : 'Create account'}
              {!loading && <span aria-hidden="true">→</span>}
            </button>
          </form>

          <p className="registration-signin-prompt">
            Already have an account? <button type="button" onClick={onBackToLogin}>Sign in</button>
          </p>
        </div>
      </section>
    </main>
  );
}
