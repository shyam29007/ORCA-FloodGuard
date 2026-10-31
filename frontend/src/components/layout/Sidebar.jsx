import React from 'react';
import { NavLink } from 'react-router-dom';
import { useMode } from '../../context/ModeContext';
import { useAuth } from '../../context/AuthContext';

const NAV_SECTIONS = [
  {
    title: 'HOME',
    items: [
      { path: '/', label: 'Home', icon: 'bi-house-door' },
    ],
  },
  {
    title: 'FLOOD OPERATIONS',
    items: [
      { path: '/assessment', label: 'AI Flood Assessment', icon: 'bi-cpu', badge: 'Agentic' },
      { path: '/map', label: 'Interactive Flood Map', icon: 'bi-map' },
      { path: '/weather', label: 'Weather & Rainfall', icon: 'bi-cloud-rain' },
      { path: '/river', label: 'River Gauges & Stage', icon: 'bi-water' },
      { path: '/dams', label: 'Dams & Reservoirs', icon: 'bi-bounding-box-circles' },
      { path: '/evacuation', label: 'Evacuation & Shelters', icon: 'bi-signpost-2' },
    ],
  },
  {
    title: 'GOVERNANCE & REPORTS',
    items: [
      { path: '/alerts', label: 'Alert Authorization', icon: 'bi-broadcast-pin', badge: 'Official' },
      { path: '/reports', label: 'Citizen Reports', icon: 'bi-chat-left-text' },
      { path: '/replay', label: 'Historical Replay', icon: 'bi-clock-history' },
    ],
  },
  {
    title: 'SYSTEM',
    items: [
      { path: '/system', label: 'System & Providers', icon: 'bi-hdd-network' },
      { path: '/login', label: 'Role & Authentication', icon: 'bi-shield-lock' },
    ],
  },
];

export function Sidebar({ mobileOpen, onCloseMobile, collapsed, onToggleCollapse }) {
  const { isDemoMode } = useMode();
  const { user } = useAuth();

  return (
    <aside
      className={`sidebar-wrapper ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}
      style={{
        backgroundColor: '#092F2B',
        borderRight: '1px solid #16433E',
      }}
    >
      {/* Brand Header */}
      <div
        className="px-3 py-3 border-bottom d-flex align-items-center justify-content-between"
        style={{ borderColor: '#16433E', minHeight: '64px' }}
      >
        <div className="d-flex align-items-center gap-2 overflow-hidden">
          <div
            className="rounded-3 d-flex align-items-center justify-content-center text-white flex-shrink-0"
            style={{
              width: '38px',
              height: '38px',
              background: 'linear-gradient(135deg, #16865F 0%, #24B6A0 100%)',
              boxShadow: '0 2px 8px rgba(36, 182, 160, 0.3)',
            }}
          >
            <i className="bi bi-shield-fill-check" style={{ fontSize: '1.25rem' }}></i>
          </div>

          {!collapsed && (
            <div className="overflow-hidden">
              <h6 className="mb-0 fw-bold text-white text-truncate" style={{ letterSpacing: '0.3px', fontSize: '0.95rem' }}>
                ORCA-FloodGuard
              </h6>
              <span style={{ fontSize: '0.68rem', color: '#8FA9A3' }} className="d-block text-truncate">
                Punjab Flood Early-Warning Advisor
              </span>
            </div>
          )}
        </div>

        {/* Desktop collapse toggle */}
        <button
          type="button"
          className="btn btn-link text-decoration-none p-0 d-none d-lg-block"
          style={{ color: '#8FA9A3' }}
          onClick={onToggleCollapse}
          title={collapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          <i className={`bi ${collapsed ? 'bi-chevron-right' : 'bi-chevron-left'}`} style={{ fontSize: '1rem' }}></i>
        </button>

        {/* Mobile close button */}
        <button
          type="button"
          className="btn btn-link text-decoration-none p-0 d-lg-none"
          style={{ color: '#8FA9A3' }}
          onClick={onCloseMobile}
        >
          <i className="bi bi-x-lg" style={{ fontSize: '1.1rem' }}></i>
        </button>
      </div>

      {/* Navigation Groups */}
      <div className="py-2 flex-grow-1 overflow-auto">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title} className="mb-2">
            {!collapsed ? (
              <div
                className="px-3 pt-2 pb-1 text-uppercase fw-semibold"
                style={{ fontSize: '0.65rem', color: '#8FA9A3', letterSpacing: '0.8px' }}
              >
                {section.title}
              </div>
            ) : (
              <div className="text-center my-1" style={{ borderTop: '1px solid #16433E', width: '60%', margin: '0 auto' }} />
            )}

            <ul className="nav nav-pills flex-column px-2 gap-1 mb-0">
              {section.items.map((item) => (
                <li className="nav-item" key={item.path}>
                  <NavLink
                    to={item.path}
                    onClick={onCloseMobile}
                    className={({ isActive }) =>
                      `nav-link d-flex align-items-center ${collapsed ? 'justify-content-center' : 'justify-content-between'} py-2 px-2 rounded text-decoration-none transition-all ${
                        isActive
                          ? 'text-white'
                          : ''
                      }`
                    }
                    style={({ isActive }) => ({
                      fontSize: '0.84rem',
                      fontWeight: isActive ? '600' : '400',
                      backgroundColor: isActive ? '#16865F' : 'transparent',
                      color: isActive ? '#FFFFFF' : '#8FA9A3',
                    })}
                    title={collapsed ? item.label : undefined}
                  >
                    <div className="d-flex align-items-center gap-2 overflow-hidden">
                      <i className={`bi ${item.icon}`} style={{ fontSize: '1.05rem', minWidth: '20px', textAlign: 'center' }}></i>
                      {!collapsed && <span className="text-truncate">{item.label}</span>}
                    </div>

                    {!collapsed && item.badge && (
                      <span
                        className="badge rounded-pill"
                        style={{
                          fontSize: '0.6rem',
                          backgroundColor: item.badge === 'Official' ? '#E99A36' : '#24B6A0',
                          color: '#FFFFFF',
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {/* Sidebar Footer */}
      <div
        className="p-3 border-top mt-auto"
        style={{
          borderColor: '#16433E',
          backgroundColor: '#072421',
        }}
      >
        {!collapsed ? (
          <div>
            <div className="d-flex justify-content-between align-items-center mb-1">
              <span
                className="badge rounded-pill"
                style={{
                  fontSize: '0.65rem',
                  backgroundColor: isDemoMode ? '#E7F6EF' : '#24B6A0',
                  color: isDemoMode ? '#10483F' : '#FFFFFF',
                  border: isDemoMode ? '1px solid #BCE3D4' : 'none',
                }}
              >
                {isDemoMode ? 'DEMO MODE' : 'OPERATIONAL'}
              </span>
              <span
                className="badge"
                style={{
                  fontSize: '0.65rem',
                  backgroundColor: user?.role === 'ADMIN' ? '#D94A4A' : '#10483F',
                  color: '#FFFFFF',
                }}
              >
                {user?.role || 'CITIZEN'}
              </span>
            </div>
            <div
              className="text-truncate mt-1"
              style={{ fontSize: '0.68rem', color: '#8FA9A3' }}
            >
              Punjab SDMA / CWC / BBMB
            </div>
          </div>
        ) : (
          <div className="text-center">
            <span
              className="d-inline-block rounded-circle"
              style={{
                width: '10px',
                height: '10px',
                backgroundColor: isDemoMode ? '#24B6A0' : '#16865F',
              }}
              title={isDemoMode ? 'Demo Mode' : 'Operational Mode'}
            />
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;
