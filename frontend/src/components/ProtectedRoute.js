import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export const ProtectedRoute = ({ children }) => {
  const { token, isAdmin } = useAuth();
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  if (isAdmin) {
    return <Navigate to="/admin" replace />;
  }
  
  return children;
};

export const AdminRoute = ({ children }) => {
  const { token, isAdmin } = useAuth();
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  if (!isAdmin) {
    return <Navigate to="/game" replace />;
  }
  
  return children;
};

export default ProtectedRoute;
