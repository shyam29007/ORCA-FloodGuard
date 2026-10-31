import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import authService from '../services/authService';

export function Login() {
  const navigate = useNavigate();
  const { user, login, logout, isOfficial, isAdmin, isDemo } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [demoAccounts, setDemoAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  useEffect(() => {
    async function fetchDemoAccounts() {
      try {
        const accs = await authService.getDemoAccounts();
        setDemoAccounts(accs || []);
      } catch {
        // Fallback demo options without hardcoding official operational credentials
        setDemoAccounts([
          {
            role: 'DEMO',
            email: 'demo@orca.punjab.gov.in',
            password: 'Demo@123',
            label: 'Evaluation Sandbox (Restricted Observer)',
            permissions: ['Explore Public Dashboard', 'Run Simulated Flood Assessments', 'Inspect Multi-Agent Traces', 'Read-Only Advisory Queue (No Broadcast Rights)'],
          },
          {
            role: 'CITIZEN',
            email: 'citizen@orca.punjab.gov.in',
            password: 'Citizen@123',
            label: 'Local Citizen (Public Portal & Incident Reporting)',
            permissions: ['View Public Dashboard', 'Submit Flood Incident Reports', 'View Evacuation Maps'],
          },
        ]);
      }
    }
    fetchDemoAccounts();
  }, []);

  const handleManualLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await login(email, password);
      setSuccessMsg('Authentication successful! Authorized session established.');
      setTimeout(() => navigate('/'), 600);
    } catch (err) {
      setError(err.message || 'Login failed. Verify email and password.');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickSwitch = async (acc) => {
    setLoading(true);
    setError(null);
    setSuccessMsg(null);
    setEmail(acc.email);
    setPassword(acc.password);

    try {
      await login(acc.email, acc.password);
      setSuccessMsg(`Session established as ${acc.label}!`);
      setTimeout(() => navigate('/'), 600);
    } catch (err) {
      setError(err.message || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container-fluid px-0" style={{ maxWidth: '980px' }}>
      {/* Page Title */}
      <div className="mb-4">
        <div className="d-flex align-items-center gap-2">
          <div
            className="rounded-3 d-flex align-items-center justify-content-center text-white"
            style={{ width: '36px', height: '36px', backgroundColor: '#16865F' }}
          >
            <i className="bi bi-shield-lock fs-5"></i>
          </div>
          <h4 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
            Control Room Role & Authentication Gateway
          </h4>
        </div>
        <p className="small mb-0 mt-1" style={{ color: '#687B78' }}>
          Role-Based Access Control (RBAC) securing official early-warning broadcast gates, simulation controls, and telemetry diagnostics.
        </p>
      </div>

      {error && (
        <div
          className="alert p-3 mb-4 d-flex align-items-center gap-2"
          style={{ backgroundColor: '#FDF2F2', borderColor: '#F8CBCB', color: '#D94A4A' }}
        >
          <i className="bi bi-exclamation-triangle-fill fs-5"></i>
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div
          className="alert p-3 mb-4 d-flex align-items-center gap-2"
          style={{ backgroundColor: '#E7F6EF', borderColor: '#BCE3D4', color: '#16865F' }}
        >
          <i className="bi bi-check-circle-fill fs-5"></i>
          <span>{successMsg}</span>
        </div>
      )}

      {/* Active User Card */}
      {user && (
        <div className="orca-card p-4 mb-4">
          <div className="d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-3">
            <div className="d-flex align-items-center gap-3">
              <div
                className="rounded-circle d-flex align-items-center justify-content-center text-white fw-bold"
                style={{ width: '44px', height: '44px', backgroundColor: '#16865F', fontSize: '1.1rem' }}
              >
                {user.full_name?.[0] || 'U'}
              </div>
              <div>
                <div className="d-flex align-items-center gap-2">
                  <h6 className="fw-bold mb-0" style={{ color: '#092F2B' }}>
                    {user.full_name || 'Emergency Official'}
                  </h6>
                  <span
                    className="badge rounded-pill"
                    style={{
                      backgroundColor: user.role === 'ADMIN' ? '#D94A4A' : user.role === 'OFFICIAL' ? '#16865F' : '#687B78',
                      color: '#FFFFFF',
                      fontSize: '0.7rem',
                    }}
                  >
                    {user.role}
                  </span>
                </div>
                <span className="small text-muted">{user.email}</span>
              </div>
            </div>

            <button
              type="button"
              className="btn btn-outline-danger btn-sm d-flex align-items-center gap-1"
              onClick={logout}
            >
              <i className="bi bi-box-arrow-right"></i>
              <span>Sign Out Session</span>
            </button>
          </div>
        </div>
      )}

      {/* Quick Role Switcher Cards */}
      <h6 className="fw-bold mb-3 d-flex align-items-center gap-2" style={{ color: '#092F2B' }}>
        <i className="bi bi-people-fill text-success"></i>
        Instant Demo Role Switcher
      </h6>

      <div className="row g-3 mb-4">
        {demoAccounts.map((acc) => (
          <div key={acc.role} className="col-12 col-md-4">
            <div
              className="orca-card p-3 h-100 d-flex flex-column justify-content-between"
              style={{
                borderTop: `4px solid ${
                  acc.role === 'ADMIN'
                    ? '#D94A4A'
                    : acc.role === 'OFFICIAL'
                    ? '#16865F'
                    : acc.role === 'DEMO'
                    ? '#E99A36'
                    : '#24B6A0'
                }`,
              }}
            >
              <div>
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <span
                    className="badge rounded-pill"
                    style={{
                      backgroundColor:
                        acc.role === 'ADMIN'
                          ? '#FDF2F2'
                          : acc.role === 'OFFICIAL'
                          ? '#E7F6EF'
                          : acc.role === 'DEMO'
                          ? '#FEF7ED'
                          : '#F0FAF5',
                      color:
                        acc.role === 'ADMIN'
                          ? '#D94A4A'
                          : acc.role === 'OFFICIAL'
                          ? '#16865F'
                          : acc.role === 'DEMO'
                          ? '#92400E'
                          : '#24B6A0',
                      border: '1px solid #DFEAE6',
                      fontSize: '0.72rem',
                    }}
                  >
                    {acc.role === 'DEMO' ? 'EVALUATION SANDBOX' : `${acc.role} ROLE`}
                  </span>
                  {user?.role === acc.role && (
                    <span className="badge bg-success" style={{ fontSize: '0.65rem' }}>ACTIVE</span>
                  )}
                </div>

                <h6 className="fw-bold mb-1" style={{ color: '#092F2B' }}>
                  {acc.label}
                </h6>
                <div className="small text-muted font-monospace mb-2" style={{ fontSize: '0.72rem' }}>
                  {acc.email}
                </div>

                <div className="p-2 rounded mb-3 small" style={{ backgroundColor: '#F8FAF9', fontSize: '0.72rem' }}>
                  <strong className="d-block mb-1 text-muted">Role Permissions:</strong>
                  <ul className="mb-0 ps-3 text-muted">
                    {acc.permissions?.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <button
                id={`orca-role-switch-${acc.role.toLowerCase()}`}
                type="button"
                className={`btn btn-sm w-100 fw-semibold ${
                  acc.role === 'DEMO' ? 'btn-outline-warning text-dark' : 'btn-outline-primary'
                }`}
                onClick={() => handleQuickSwitch(acc)}
                disabled={loading || user?.role === acc.role}
              >
                {user?.role === acc.role
                  ? 'Currently Active'
                  : acc.role === 'DEMO'
                  ? 'Launch Demo Evaluation Session'
                  : `Switch to ${acc.role}`}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Manual Login Form */}
      <div className="orca-card p-4">
        <h6 className="fw-bold mb-3" style={{ color: '#092F2B' }}>
          Manual Credential Authentication
        </h6>

        <form onSubmit={handleManualLogin}>
          <div className="row g-3">
            <div className="col-12 col-md-6">
              <label className="form-label small fw-semibold">Official Email Address</label>
              <input
                type="email"
                className="form-control"
                placeholder="official@orca.punjab.gov.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="col-12 col-md-6">
              <label className="form-label small fw-semibold">Security Password</label>
              <input
                type="password"
                className="form-control"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="col-12">
              <button
                id="orca-manual-login-submit-btn"
                type="submit"
                className="btn btn-primary px-4 py-2 fw-semibold"
                disabled={loading}
              >
                {loading ? 'Authenticating...' : 'Sign In with Credentials'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Login;
