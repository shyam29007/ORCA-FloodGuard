import React, { useState } from 'react';
import { useMode } from '../../context/ModeContext';
import { useAuth } from '../../context/AuthContext';
import ModeSwitch from '../common/ModeSwitch';
import { PUNJAB_DISTRICTS } from '../../utils/punjabData';
import { useNavigate } from 'react-router-dom';

export function Navbar({ onToggleSidebar }) {
  const { selectedDistrict, setSelectedDistrict } = useMode();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <header className="top-navbar px-3 px-md-4 d-flex align-items-center justify-content-between">
      {/* Left: Mobile Toggle & Control Room Brand */}
      <div className="d-flex align-items-center gap-3">
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary d-lg-none p-1 px-2"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation"
          style={{ borderColor: '#DFEAE6', color: '#152E2B' }}
        >
          <i className="bi bi-list fs-5"></i>
        </button>

        <div className="d-flex align-items-center gap-2">
          <span
            className="badge rounded-pill d-none d-sm-inline-flex align-items-center gap-1 px-2 py-1"
            style={{
              backgroundColor: '#E7F6EF',
              color: '#16865F',
              border: '1px solid #BCE3D4',
              fontSize: '0.75rem',
              fontWeight: 600,
            }}
          >
            <i className="bi bi-shield-check"></i> PUNJAB DISASTER MANAGEMENT
          </span>
          {user?.role === 'DEMO' && (
            <span
              className="badge rounded-pill d-inline-flex align-items-center gap-1 px-2 py-1"
              style={{
                backgroundColor: '#FEF7ED',
                color: '#92400E',
                border: '1px solid #FCE4C3',
                fontSize: '0.72rem',
                fontWeight: 600,
              }}
            >
              <i className="bi bi-shield-exclamation text-warning"></i> DEMO SESSION (BROADCAST LOCKED)
            </span>
          )}
          <span className="text-muted d-none d-md-inline" style={{ fontSize: '0.8rem' }}>•</span>
          <span className="fw-semibold d-none d-md-inline" style={{ fontSize: '0.88rem', color: '#152E2B' }}>
            Sutlej-Beas Flood Watch
          </span>
        </div>
      </div>

      {/* Right: District Selector, Mode Switcher, Notifications, Profile */}
      <div className="d-flex align-items-center gap-2 gap-md-3">
        {/* District Selector */}
        <div
          className="d-flex align-items-center rounded-3 px-2 py-1"
          style={{
            backgroundColor: '#F4F8F7',
            border: '1px solid #DFEAE6',
          }}
        >
          <i className="bi bi-geo-alt text-muted me-1" style={{ fontSize: '0.85rem', color: '#16865F' }}></i>
          <select
            className="form-select form-select-sm bg-transparent border-0 py-0 ps-1 pe-4 shadow-none fw-medium"
            style={{ fontSize: '0.8rem', color: '#152E2B', cursor: 'pointer' }}
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
          >
            {PUNJAB_DISTRICTS.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>

        {/* Mode Switcher */}
        <ModeSwitch />

        {/* Notification Bell */}
        <div className="position-relative">
          <button
            type="button"
            className="btn btn-sm btn-link p-1 text-decoration-none position-relative rounded-circle"
            style={{ color: '#687B78' }}
            onClick={() => setShowNotifications(!showNotifications)}
            title="Advisory Notifications"
          >
            <i className="bi bi-bell fs-5"></i>
            <span
              className="position-absolute top-0 start-100 translate-middle p-1 rounded-circle"
              style={{ backgroundColor: '#E99A36', width: '8px', height: '8px' }}
            >
              <span className="visually-hidden">New alerts</span>
            </span>
          </button>

          {showNotifications && (
            <div
              className="dropdown-menu dropdown-menu-end show p-3 shadow-lg"
              style={{
                position: 'absolute',
                top: '40px',
                right: '0',
                width: '320px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #DFEAE6',
                borderRadius: '12px',
                zIndex: 1050,
              }}
            >
              <div className="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom">
                <span className="fw-bold small" style={{ color: '#152E2B' }}>Flood Watch Notifications</span>
                <span className="badge bg-light text-muted font-monospace" style={{ fontSize: '0.65rem' }}>SDMA Control</span>
              </div>
              <div className="small text-muted py-2">
                <div className="fw-semibold text-dark mb-1" style={{ fontSize: '0.8rem' }}>
                  <i className="bi bi-info-circle text-primary me-1"></i> Phillaur River Stage Approaching Warning
                </div>
                <div style={{ fontSize: '0.72rem' }}>
                  Sutlej water stage verified at 234.50m (Warning: 235.00m). Continuous monitoring active.
                </div>
              </div>
              <div className="pt-2 border-top text-center">
                <button
                  type="button"
                  className="btn btn-link btn-sm text-decoration-none p-0"
                  style={{ color: '#16865F', fontSize: '0.75rem' }}
                  onClick={() => {
                    setShowNotifications(false);
                    navigate('/alerts');
                  }}
                >
                  View All Alert Drafts &rarr;
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Avatar & Dropdown or Login Gateway */}
        {user ? (
          <div className="position-relative">
            <button
              id="orca-user-profile-menu-btn"
              className="btn btn-sm d-flex align-items-center gap-2 px-2 py-1 rounded-pill"
              type="button"
              style={{
                backgroundColor: '#F4F8F7',
                border: '1px solid #DFEAE6',
              }}
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <div
                className="rounded-circle d-flex align-items-center justify-content-center text-white fw-bold"
                style={{
                  width: '28px',
                  height: '28px',
                  fontSize: '0.75rem',
                  backgroundColor: user?.role === 'DEMO' ? '#E99A36' : '#16865F',
                }}
              >
                {user?.full_name?.[0] || 'U'}
              </div>
              <span className="d-none d-md-inline small fw-semibold" style={{ color: '#152E2B' }}>
                {user?.full_name?.split(' ')[0] || 'User'}
              </span>
              <span
                className="badge rounded-pill"
                style={{
                  fontSize: '0.65rem',
                  backgroundColor:
                    user?.role === 'ADMIN'
                      ? '#D94A4A'
                      : user?.role === 'OFFICIAL'
                      ? '#10483F'
                      : user?.role === 'DEMO'
                      ? '#E99A36'
                      : '#24B6A0',
                  color: '#FFFFFF',
                }}
              >
                {user?.role === 'DEMO' ? 'DEMO OBSERVER' : user?.role}
              </span>
            </button>

          {showUserMenu && (
            <div
              className="dropdown-menu dropdown-menu-end show p-2 shadow-lg"
              style={{
                position: 'absolute',
                top: '44px',
                right: '0',
                width: '240px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #DFEAE6',
                borderRadius: '12px',
                zIndex: 1050,
              }}
            >
              <div className="px-3 py-2 border-bottom mb-1">
                <div className="fw-bold small" style={{ color: '#152E2B' }}>{user?.full_name || 'Emergency Official'}</div>
                <div className="text-muted" style={{ fontSize: '0.72rem' }}>{user?.email || 'district.collector@punjab.gov.in'}</div>
                <span className="badge mt-1" style={{ backgroundColor: '#E7F6EF', color: '#16865F', fontSize: '0.68rem' }}>
                  Role: {user?.role || 'OFFICIAL'}
                </span>
              </div>
              <button
                type="button"
                className="dropdown-item py-2 small d-flex align-items-center gap-2 rounded"
                onClick={() => {
                  setShowUserMenu(false);
                  navigate('/login');
                }}
              >
                <i className="bi bi-person-gear"></i> Role Switcher & Accounts
              </button>
              <button
                type="button"
                className="dropdown-item py-2 small d-flex align-items-center gap-2 rounded"
                onClick={() => {
                  setShowUserMenu(false);
                  navigate('/system');
                }}
              >
                <i className="bi bi-hdd-network"></i> System & Providers
              </button>
              <div className="dropdown-divider my-1" />
              <button
                id="orca-user-logout-btn"
                type="button"
                className="dropdown-item py-2 small text-danger d-flex align-items-center gap-2 rounded"
                onClick={() => {
                  setShowUserMenu(false);
                  logout();
                  navigate('/login');
                }}
              >
                <i className="bi bi-box-arrow-right"></i> Sign Out
              </button>
            </div>
          )}
        </div>
        ) : (
          <button
            className="btn btn-sm px-3 py-1 rounded-pill fw-semibold d-flex align-items-center gap-2"
            type="button"
            style={{
              backgroundColor: '#16865F',
              color: '#FFFFFF',
              border: 'none',
              fontSize: '0.8rem',
            }}
            onClick={() => navigate('/login')}
          >
            <i className="bi bi-box-arrow-in-right"></i> Sign In
          </button>
        )}
      </div>
    </header>
  );
}

export default Navbar;
