import React, { useState } from 'react';
import { 
  Zap, 
  Mail, 
  Lock, 
  User, 
  Eye, 
  EyeOff, 
  ArrowRight, 
  ShieldCheck, 
  Sparkles, 
  Check, 
  AlertCircle,
  Layers,
  Database,
  Search
} from 'lucide-react';
import { loginWithCredentials, signupWithCredentials, loginAsDemo } from '../utils/auth';

export default function AuthPage({ onLoginSuccess }) {
  const [mode, setMode] = useState('login'); // 'login' or 'signup'
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isSignup = mode === 'signup';

  const handleDemoLogin = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await loginAsDemo();
      if (res.success && onLoginSuccess) {
        onLoginSuccess(res.user);
      }
    } catch (err) {
      setError('Demo login failed: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim()) {
      setError('Please provide a valid username or email');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    if (isSignup) {
      if (password !== confirmPassword) {
        setError('Passwords do not match');
        return;
      }
      if (email && !email.includes('@')) {
        setError('Please enter a valid email address');
        return;
      }
    }

    setLoading(true);

    try {
      if (isSignup) {
        const res = await signupWithCredentials(username.trim(), email.trim(), password);
        if (res.success) {
          onLoginSuccess(res.user);
        } else {
          setError(res.error || 'Failed to create account');
        }
      } else {
        const res = await loginWithCredentials(username.trim(), password);
        if (res.success) {
          onLoginSuccess(res.user);
        } else {
          setError(res.error || 'Invalid credentials');
        }
      }
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-viewport">
      {/* Dynamic Background Blurs */}
      <div className="auth-glow-orb orb-1" />
      <div className="auth-glow-orb orb-2" />

      <div className="auth-main-card">
        {/* Left Side: Brand Showcase */}
        <div className="auth-brand-side">
          <div className="auth-brand-header">
            <div className="brand-badge-large">
              <Zap size={24} className="fill-current text-white" />
            </div>
            <div>
              <h1 className="brand-hero-title">ZymeRag</h1>
              <p className="brand-hero-tag">Multimodal RAG & Knowledge Engine</p>
            </div>
          </div>

          <div className="auth-feature-list">
            <div className="feature-item">
              <div className="feature-icon-box bg-indigo-subtle">
                <Layers size={18} className="text-indigo" />
              </div>
              <div>
                <h4 className="feature-title">Universal Multimodal Ingestion</h4>
                <p className="feature-desc">Ingest PDFs, Word docs, Images (OCR), Video, Audio & Web URLs directly into vector space.</p>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon-box bg-violet-subtle">
                <Database size={18} className="text-violet" />
              </div>
              <div>
                <h4 className="feature-title">Supabase pgvector Indexed</h4>
                <p className="feature-desc">High-performance vector embedding storage with cosine distance similarity search.</p>
              </div>
            </div>

            <div className="feature-item">
              <div className="feature-icon-box bg-blue-subtle">
                <Search size={18} className="text-blue" />
              </div>
              <div>
                <h4 className="feature-title">Hybrid BM25 + Semantic Search</h4>
                <p className="feature-desc">Combines full-text reciprocal rank fusion with dense semantic representations.</p>
              </div>
            </div>
          </div>

          <div className="auth-side-footer">
            <span className="secure-badge">
              <ShieldCheck size={14} className="text-emerald" />
              <span>JWT & Role-isolated Workspaces</span>
            </span>
          </div>
        </div>

        {/* Right Side: Auth Form */}
        <div className="auth-form-side">
          {/* Quick Demo Access Header */}
          <div className="auth-demo-banner">
            <div className="demo-info">
              <Sparkles size={16} className="text-amber" />
              <span>Want to explore the dashboard immediately?</span>
            </div>
            <button 
              type="button" 
              className="btn-demo-quick" 
              onClick={handleDemoLogin}
              disabled={loading}
            >
              ⚡ Instant Demo Login
            </button>
          </div>

          <div className="auth-tabs-row">
            <button 
              type="button"
              className={`auth-tab-btn ${!isSignup ? 'active' : ''}`}
              onClick={() => { setMode('login'); setError(''); }}
            >
              Sign In
            </button>
            <button 
              type="button"
              className={`auth-tab-btn ${isSignup ? 'active' : ''}`}
              onClick={() => { setMode('signup'); setError(''); }}
            >
              Create Account
            </button>
          </div>

          <div className="auth-form-header">
            <h2 className="auth-form-title">
              {isSignup ? 'Create your workspace' : 'Welcome back'}
            </h2>
            <p className="auth-form-subtitle">
              {isSignup 
                ? 'Register to index and manage multimodal vectors in ZymeRag' 
                : 'Enter your credentials to access your ZymeRag console'}
            </p>
          </div>

          {error && (
            <div className="auth-alert-box error">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form-body">
            <div className="input-group">
              <label htmlFor="auth-username">
                {isSignup ? 'Username' : 'Username or Email'}
              </label>
              <div className="input-field-wrapper">
                <User size={16} className="field-icon" />
                <input 
                  id="auth-username"
                  type="text" 
                  className="auth-input"
                  placeholder={isSignup ? 'e.g. arman_dev' : 'admin or you@zymerag.io'}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoFocus
                  required
                />
              </div>
            </div>

            {isSignup && (
              <div className="input-group">
                <label htmlFor="auth-email">Email Address <span className="optional-tag">(Optional)</span></label>
                <div className="input-field-wrapper">
                  <Mail size={16} className="field-icon" />
                  <input 
                    id="auth-email"
                    type="email" 
                    className="auth-input"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>
            )}

            <div className="input-group">
              <div className="label-row">
                <label htmlFor="auth-password">Password</label>
                {!isSignup && (
                  <span className="demo-hint-text">demo: any password</span>
                )}
              </div>
              <div className="input-field-wrapper">
                <Lock size={16} className="field-icon" />
                <input 
                  id="auth-password"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="At least 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button 
                  type="button" 
                  className="eye-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {isSignup && (
              <div className="input-group">
                <label htmlFor="auth-confirm">Confirm Password</label>
                <div className="input-field-wrapper">
                  <Lock size={16} className="field-icon" />
                  <input 
                    id="auth-confirm"
                    type={showPassword ? 'text' : 'password'}
                    className="auth-input"
                    placeholder="Re-type your password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                </div>
              </div>
            )}

            <button 
              type="submit" 
              className="btn-auth-submit" 
              disabled={loading}
            >
              {loading ? (
                <span className="btn-spinner-content">
                  <span className="btn-spinner" />
                  <span>{isSignup ? 'Creating workspace...' : 'Authenticating...'}</span>
                </span>
              ) : (
                <span className="btn-label-content">
                  <span>{isSignup ? 'Get Started with ZymeRag' : 'Sign In to Dashboard'}</span>
                  <ArrowRight size={16} />
                </span>
              )}
            </button>
          </form>

          <div className="auth-form-footer">
            {isSignup ? (
              <span>
                Already have an account?{' '}
                <button 
                  type="button" 
                  className="link-switch-auth"
                  onClick={() => { setMode('login'); setError(''); }}
                >
                  Sign in here
                </button>
              </span>
            ) : (
              <span>
                Need a new account?{' '}
                <button 
                  type="button" 
                  className="link-switch-auth"
                  onClick={() => { setMode('signup'); setError(''); }}
                >
                  Create one now
                </button>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
