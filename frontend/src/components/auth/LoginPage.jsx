import { useState, useEffect } from 'react';
import { ArrowRight, Eye, EyeOff, AlertCircle } from 'lucide-react';
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
  const [accounts, setAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('Govt@2024');
  const [showPassword, setShowPassword] = useState(false);
  const [mottoIndex, setMottoIndex] = useState(0);
  const [isFading, setIsFading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetchingAccounts, setFetchingAccounts] = useState(false);
  const [error, setError] = useState('');

  // Fetch official administrative accounts from backend
  useEffect(() => {
    let isMounted = true;
    setFetchingAccounts(true);

    fetch('/api/v1/admin/public-accounts')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!isMounted) return;
        if (Array.isArray(data) && data.length > 0) {
          setAccounts(data);
          const defaultAcc = data.find((a) => (role === 'admin' ? a.is_admin : !a.is_admin));
          if (defaultAcc) {
            setSelectedAccountId(defaultAcc.id || '');
            setEmail(defaultAcc.email || '');
          }
        }
      })
      .catch((err) => {
        console.debug('Public accounts query notice:', err);
      })
      .finally(() => {
        if (isMounted) setFetchingAccounts(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Synchronize selected account when role tab changes
  useEffect(() => {
    if (!accounts.length) return;
    const matched = accounts.find((a) => (role === 'admin' ? a.is_admin : !a.is_admin));
    if (matched) {
      setSelectedAccountId(matched.id || '');
      setEmail(matched.email || '');
      setError('');
    } else {
      setSelectedAccountId('');
      setEmail('');
    }
  }, [role, accounts]);

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

  const selectedAccount = accounts.find((a) => a.id === selectedAccountId);
  const isSuspended = selectedAccount?.status === 'Suspended';

  const handleSelectAccount = (accId) => {
    setSelectedAccountId(accId || '');
    const acc = accounts.find((a) => a.id === accId);
    if (acc) {
      setEmail(acc.email || '');
      setError('');
    }
  };

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedEmail = (email || '').trim().toLowerCase();
    if (!trimmedEmail) {
      setError('Please enter or select your official email address.');
      return;
    }

    const matchedAccount = accounts.find(
      (a) => a.email && a.email.toLowerCase() === trimmedEmail
    ) || selectedAccount;

    if (matchedAccount?.status === 'Suspended') {
      setError('This account has been suspended by District Administration. Sign-in is blocked.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Dynamic authentication without any hardcoded officer ID
      const res = await fetch('/api/v1/admin/session/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: trimmedEmail,
          password: password || '',
          role: matchedAccount?.is_admin ? 'admin' : 'user'
        })
      });

      if (!res.ok) {
        let errDetail = 'Sign in failed.';
        try {
          const errData = await res.json();
          errDetail = errData.detail || errDetail;
        } catch {
          if (res.status === 403) {
            errDetail = 'This account has been suspended by District Administration. Sign-in is blocked.';
          } else if (res.status === 404) {
            errDetail = 'Official account not found. Please verify your email or select an official account.';
          } else if (res.status === 503) {
            errDetail = 'Authentication service is initializing. Please try again in a moment.';
          }
        }
        if (res.status === 403) {
          errDetail = 'This account has been suspended by District Administration. Sign-in is blocked.';
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
  const filteredAccounts = accounts.filter((a) => (role === 'admin' ? a.is_admin : !a.is_admin));

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
            <p>Select your official account or enter your government email.</p>
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

            {/* Suspended Alert */}
            {isSuspended && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '10px 14px',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '6px',
                  color: '#b91c1c',
                  fontSize: '0.8rem',
                  margin: '8px 0'
                }}
              >
                <AlertCircle size={18} style={{ flexShrink: 0 }} />
                <span>
                  <strong>Access Suspended:</strong> This account has been suspended by the District
                  Administrator. Sign in is blocked.
                </span>
              </div>
            )}

            {/* Account Quick Selector Dropdown */}
            {filteredAccounts.length > 0 && (
              <div className="login-field">
                <label htmlFor="login-account-select">
                  Select {role === 'admin' ? 'Administrative Account' : 'Officer Account'}
                </label>
                <select
                  id="login-account-select"
                  value={selectedAccountId ?? ''}
                  onChange={(e) => handleSelectAccount(e.target.value)}
                  disabled={loading}
                >
                  <option value="">-- Choose registered account --</option>
                  {filteredAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.email}) {acc.status === 'Suspended' ? '[SUSPENDED]' : ''}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="login-field">
              <label htmlFor="login-email">Official Email</label>
              <input
                id="login-email"
                type="email"
                value={email ?? ''}
                onChange={(e) => {
                  const val = e.target.value;
                  setEmail(val);
                  const matched = accounts.find(
                    (a) => a.email && a.email.toLowerCase() === val.trim().toLowerCase()
                  );
                  if (matched) {
                    setSelectedAccountId(matched.id || '');
                    setRole(matched.is_admin ? 'admin' : 'user');
                    setError('');
                  }
                }}
                placeholder="you@tn.gov.in"
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
                  value={password ?? ''}
                  onChange={(e) => setPassword(e.target.value ?? '')}
                  placeholder="Enter password"
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
              <p role="alert" style={{ color: '#b91c1c', fontSize: '0.8rem', margin: '6px 0' }}>
                {error}
              </p>
            )}

            <button
              className="login-submit"
              type="submit"
              disabled={loading || isSuspended}
              style={isSuspended ? { opacity: 0.5, cursor: 'not-allowed' } : {}}
            >
              <span>{loading ? 'Authenticating…' : isSuspended ? 'Account Suspended' : 'Sign in'}</span>
              <ArrowRight size={18} aria-hidden="true" />
            </button>
            <p className="login-demo">
              Systematic status tracking <span>Status updates to Active upon login</span>
            </p>
          </form>
        </section>
      </div>
    </main>
  );
}
