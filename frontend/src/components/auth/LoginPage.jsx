import { useState, useEffect } from 'react';
import { ArrowRight, Eye, EyeOff } from 'lucide-react';
import './LoginPage.css';

const MOTTO_VARIANTS = [
  {
    lang: 'ta',
    line1: 'மக்களின் குரல்,',
    line2: 'அரசின் செயல்.'
  },
  {
    lang: 'en',
    line1: 'Listening to Citizens,',
    line2: 'Acting with Precision.'
  }
];

export default function LoginPage({ onLogin }) {
  const [role, setRole] = useState('user');
  const [showPassword, setShowPassword] = useState(false);
  const [mottoIndex, setMottoIndex] = useState(0);
  const [isFading, setIsFading] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      setIsFading(true);
      setTimeout(() => {
        setMottoIndex((prev) => (prev === 0 ? 1 : 0));
        setIsFading(false);
      }, 400);
    }, 4500);

    return () => clearInterval(timer);
  }, []);

  function handleSubmit(event) {
    event.preventDefault();
    // Frontend demo only. Never persist credentials or treat this as authorization.
    onLogin({ role });
  }

  const currentMotto = MOTTO_VARIANTS[mottoIndex];

  return (
    <main className="login-page">
      <aside className="login-identity" aria-label="Government of Tamil Nadu">
        <header className="login-brand">
          <h2>Erode Collectorate</h2>
          <p>AI Administrative Co-Pilot</p>
        </header>

        <div className="login-emblem" aria-hidden="true" />

        <section className="login-intro login-intro-right" aria-labelledby="login-intro-title">
          <p className="login-intro-label">Public grievance workspace</p>
          <div className="login-motto-box">
            <h2
              id="login-intro-title"
              className={`login-motto-heading ${isFading ? 'motto-fade-out' : 'motto-fade-in'}`}
              lang={currentMotto.lang}
            >
              {currentMotto.line1}
              <br />
              <span>{currentMotto.line2}</span>
            </h2>
          </div>
        </section>
      </aside>

      <div className="login-content">
        <section className="login-card" aria-labelledby="login-title">
          <div className="login-heading">
            <h1 id="login-title">Sign in</h1>
            <p>Enter your account details to continue.</p>
          </div>

          <form onSubmit={handleSubmit}>
            <fieldset className="login-roles">
              <legend className="visually-hidden">Sign in as</legend>
              {[{ value: 'user', label: 'User' }, { value: 'admin', label: 'Admin' }].map(({ value, label }) => (
                <label key={value} className="login-role">
                  <input type="radio" name="role" value={value} checked={role === value} onChange={() => setRole(value)} />
                  <span>{label}</span>
                </label>
              ))}
            </fieldset>

            <div className="login-field">
              <label htmlFor="login-email">Email address/ மின்னஞ்சல் முகவரி</label>
              <input id="login-email" name="email" type="email" placeholder="you@tn.gov.in" autoComplete="username" required />
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Password/கடவுச்சொல்</label>
              <div className="login-password">
                <input id="login-password" name="password" type={showPassword ? 'text' : 'password'} placeholder="Enter password" autoComplete="current-password" required />
                <button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button className="login-submit" type="submit">Sign in <ArrowRight size={18} aria-hidden="true" /></button>
            <p className="login-demo">Demo mode <span>Any email and password</span></p>
          </form>
        </section>
      </div>
    </main>
  );
}
