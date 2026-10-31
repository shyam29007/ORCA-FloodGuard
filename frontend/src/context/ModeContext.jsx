import React, { createContext, useContext, useState } from 'react';

const ModeContext = createContext(null);

export function ModeProvider({ children }) {
  // Evaluation default: DEMO mode enabled to explore simulation telemetry seamlessly
  const [mode, setMode] = useState('DEMO');
  const [selectedDistrict, setSelectedDistrict] = useState('All Districts');

  const toggleMode = () => {
    setMode((prev) => (prev === 'DEMO' ? 'OPERATIONAL' : 'DEMO'));
  };

  const isDemoMode = mode === 'DEMO';

  return (
    <ModeContext.Provider
      value={{
        mode,
        isDemoMode,
        toggleMode,
        setMode,
        selectedDistrict,
        setSelectedDistrict,
      }}
    >
      {children}
    </ModeContext.Provider>
  );
}

export function useMode() {
  const context = useContext(ModeContext);
  if (!context) {
    throw new Error('useMode must be used within a ModeProvider');
  }
  return context;
}

