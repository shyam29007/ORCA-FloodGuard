import React, { createContext, useContext, useState, useEffect } from 'react';
import authService from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing valid session in storage
    const savedUser = authService.getCurrentUser();
    const token = localStorage.getItem('orca_token');
    if (savedUser && token) {
      setUser(savedUser);
    } else {
      // Require explicit authentication; do not fabricate or auto-initialize credentials
      setUser(null);
    }
    setLoading(false);

    // Listen for session expiration events dispatched by API interceptor
    const handleAuthExpired = () => {
      authService.logout();
      setUser(null);
    };
    window.addEventListener('orca-auth-expired', handleAuthExpired);
    return () => window.removeEventListener('orca-auth-expired', handleAuthExpired);
  }, []);

  const login = async (email, password) => {
    const data = await authService.login(email, password);
    setUser(data.user);
    return data;
  };

  const register = async (regData) => {
    const data = await authService.register(regData);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  const isOfficial = user?.role === 'OFFICIAL' || user?.role === 'ADMIN';
  const isAdmin = user?.role === 'ADMIN';
  const isDemo = user?.role === 'DEMO';
  const isAuthenticated = !!user && !!localStorage.getItem('orca_token');

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        isAuthenticated,
        isOfficial,
        isAdmin,
        isDemo,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

