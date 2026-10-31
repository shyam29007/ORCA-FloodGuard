import React, { lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ModeProvider } from './context/ModeContext';
import Layout from './components/layout/Layout';
import LoadingSpinner from './components/common/LoadingSpinner';

// Eagerly loaded primary landing view
import Dashboard from './pages/Dashboard';

// Route-level lazy loading for performance & code splitting
const FloodAssessment = lazy(() => import('./pages/FloodAssessment'));
const FloodMap = lazy(() => import('./pages/FloodMap'));
const WeatherMonitoring = lazy(() => import('./pages/WeatherMonitoring'));
const RiverMonitoring = lazy(() => import('./pages/RiverMonitoring'));
const DamInformation = lazy(() => import('./pages/DamInformation'));
const Evacuation = lazy(() => import('./pages/Evacuation'));
const AlertManagement = lazy(() => import('./pages/AlertManagement'));
const CommunityReports = lazy(() => import('./pages/CommunityReports'));
const HistoricalReplay = lazy(() => import('./pages/HistoricalReplay'));
const SystemStatus = lazy(() => import('./pages/SystemStatus'));
const Login = lazy(() => import('./pages/Login'));
const NotFound = lazy(() => import('./pages/NotFound'));

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ModeProvider>
          <Suspense fallback={<LoadingSpinner message="Loading operational module..." />}>
            <Routes>
              <Route path="/" element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="assessment" element={<FloodAssessment />} />
                <Route path="map" element={<FloodMap />} />
                <Route path="weather" element={<WeatherMonitoring />} />
                <Route path="river" element={<RiverMonitoring />} />
                <Route path="dams" element={<DamInformation />} />
                <Route path="evacuation" element={<Evacuation />} />
                <Route path="alerts" element={<AlertManagement />} />
                <Route path="reports" element={<CommunityReports />} />
                <Route path="replay" element={<HistoricalReplay />} />
                <Route path="system" element={<SystemStatus />} />
                <Route path="login" element={<Login />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
          </Suspense>
        </ModeProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

