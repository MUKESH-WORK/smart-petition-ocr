import { useState, useEffect } from 'react';
import { ArrowRight, Eye, EyeOff, AlertCircle } from 'lucide-react';
import GeminiLegalModal from '../common/GeminiLegalModal';
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
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [mottoIndex, setMottoIndex] = useState(0);
  const [isFading, setIsFading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [legalModalTab, setLegalModalTab] = useState(null); // 'privacy' | 'terms' | null

  // Rotating bilingual motto
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

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedEmail = (email || '').trim().toLowerCase();
    if (!trimmedEmail) {
      setError('Please enter your official email address.');
      return;
    }
    if (!password) {
      setError('Please enter your password.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Dynamic authentication directly against authoritative Admin DB
      const res = await fetch('/api/v1/admin/session/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: trimmedEmail,
          password: password,
          role: role
        })
      });

      if (!res.ok) {
        let errDetail = 'Sign in failed.';
        try {
          const errData = await res.json();
          errDetail = errData.detail || errDetail;
        } catch {
          if (res.status === 404) {
            errDetail = 'Official account not found. Please verify your email address.';
          } else if (res.status === 401) {
            errDetail = 'Invalid official password. Please verify credentials.';
          } else if (res.status === 503) {
            errDetail = 'Authentication service is initializing. Please try again in a moment.';
          }
        }
        throw new Error(errDetail);
      }

      const sessionData = await res.json();
      const user = sessionData.user || sessionData;
      if (!user || (!user.id && !user.officerId)) {
        throw new Error('Authentication succeeded, but user profile could not be loaded.');
      }

      // Persist live profile and JWT authentication token systematically
      if (sessionData.access_token) {
        localStorage.setItem('auth_token', sessionData.access_token);
        localStorage.setItem('token', sessionData.access_token);
      }
      localStorage.setItem('officer_id', user.id);
      localStorage.setItem('officer_name', user.name);
      if (user.email) localStorage.setItem('officer_email', user.email);
      if (user.mobile) localStorage.setItem('officer_phone', user.mobile);
      localStorage.setItem('officer_role', user.is_admin ? 'admin' : 'user');
      localStorage.setItem('officer_profile', JSON.stringify(user));

      onLogin({
        ...user,
        role: user.is_admin ? 'admin' : 'user',
        user: user,
        profile: user
      });
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }

  const currentMotto = MOTTO_VARIANTS[mottoIndex];

  return (
    <main className="login-page">
      <aside className="login-identity" aria-label="Government of Tamil Nadu">
        <header className="login-brand">
          <img src="/tn-emblem.png" alt="Government of Tamil Nadu" className="login-brand-emblem" />
          <div className="login-brand-text">
            <h2>Erode Collectorate</h2>
            <p>AI Administrative Co-Pilot</p>
          </div>
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
            <p>Enter your official government email and credentials to continue.</p>
          </div>

          <form onSubmit={handleSubmit}>
            <fieldset className="login-roles">
              <legend className="visually-hidden">Sign in as</legend>
              {[
                { value: 'user', label: 'Officers' },
                { value: 'admin', label: 'Admin' }
              ].map(({ value, label }) => (
                <label key={value} className="login-role">
                  <input
                    type="radio"
                    name="role"
                    value={value}
                    checked={role === value}
                    onChange={() => setRole(value)}
                  />
                  <span>{label}</span>
                </label>
              ))}
            </fieldset>

            <div className="login-field">
              <label htmlFor="login-email">Official Email</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@tn.gov.in"
                autoComplete="username"
                required
              />
            </div>

            <div className="login-field">
              <label htmlFor="login-password">Password / கடவுச்சொல்</label>
              <div className="login-password">
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter official password"
                  autoComplete="current-password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {error && (
              <p role="alert" style={{ color: '#b91c1c', fontSize: '0.8rem', margin: '6px 0', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertCircle size={15} />
                {error}
              </p>
            )}

            {/* Anti-bot honeypot field (hidden from real users) */}
            <input
              type="text"
              name="website_url_hp"
              aria-hidden="true"
              style={{ display: 'none', position: 'absolute', left: '-9999px' }}
              tabIndex={-1}
              autoComplete="off"
            />

            <button
              className="login-submit"
              type="submit"
              disabled={loading}
            >
              <span>{loading ? 'Authenticating…' : 'Sign in'}</span>
              <ArrowRight size={18} aria-hidden="true" />
            </button>

            <div className="flex items-center justify-between mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid #e2e8f0', fontSize: '0.75rem', color: '#64748b' }}>
              <button
                type="button"
                onClick={() => setLegalModalTab('privacy')}
                style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', padding: 0, fontSize: '0.75rem', textDecoration: 'none' }}
              >
                Privacy Policy
              </button>
              <span>•</span>
              <button
                type="button"
                onClick={() => setLegalModalTab('terms')}
                style={{ background: 'none', border: 'none', color: '#2563eb', cursor: 'pointer', padding: 0, fontSize: '0.75rem', textDecoration: 'none' }}
              >
                Terms of Operation
              </button>
              <span>•</span>
              <span>TLS 1.3 Encrypted</span>
            </div>

            <p className="login-demo">
              District Administration Portal <span>Erode Collectorate • Revenue & Disaster Management</span>
            </p>
          </form>
        </section>
      </div>

      <GeminiLegalModal
        isOpen={Boolean(legalModalTab)}
        initialTab={legalModalTab || 'privacy'}
        onClose={() => setLegalModalTab(null)}
      />
    </main>
  );
}
