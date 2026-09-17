import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext({
  officerId: 'DRO_ERODE_01',
  officerName: 'District Revenue Officer',
  role: 'DRO',
  setOfficerId: () => {},
  setAuthDetails: () => {}
});

export const AuthProvider = ({ children }) => {
  const [officerId, setOfficerIdState] = useState(() => {
    return localStorage.getItem('officer_id') || 'DRO_ERODE_01';
  });
  const [officerName, setOfficerName] = useState(() => {
    return localStorage.getItem('officer_name') || 'District Revenue Officer';
  });
  const [role, setRole] = useState(() => {
    return localStorage.getItem('officer_role') || 'DRO';
  });

  const setOfficerId = (id) => {
    setOfficerIdState(id);
    if (id) {
      localStorage.setItem('officer_id', id);
    } else {
      localStorage.removeItem('officer_id');
    }
  };

  const setAuthDetails = ({ id, name, role: newRole }) => {
    if (id) {
      setOfficerIdState(id);
      localStorage.setItem('officer_id', id);
    }
    if (name) {
      setOfficerName(name);
      localStorage.setItem('officer_name', name);
    }
    if (newRole) {
      setRole(newRole);
      localStorage.setItem('officer_role', newRole);
    }
  };

  return (
    <AuthContext.Provider value={{ officerId, officerName, role, setOfficerId, setAuthDetails }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
