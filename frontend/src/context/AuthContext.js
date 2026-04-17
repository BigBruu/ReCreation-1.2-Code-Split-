import React, { useState, useEffect, createContext, useContext } from 'react';
import axios from 'axios';
import { API } from '../lib/api';

// Auth Context
const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    if (token) {
      validateSession(token);
    } else {
      setIsAdmin(false);
      setUser(null);
      setLoading(false);
    }
  }, [token]);

  const validateSession = async (authToken) => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/auth/session`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const admin = Boolean(response.data.admin);
      setIsAdmin(admin);
      if (admin) {
        setUser(null);
      } else {
        await fetchUser(authToken);
      }
    } catch (error) {
      logout();
    } finally {
      setLoading(false);
    }
  };

  const fetchUser = async (authToken = token) => {
    try {
      const response = await axios.get(`${API}/me`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setUser(response.data);
    } catch (error) {
      logout();
    }
  };

  const login = async (username, password) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/login`, { username, password });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setIsAdmin(false);
      return true;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const adminLogin = async (password) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/admin/login`, { password });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setIsAdmin(true);
      return true;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Admin login failed');
    } finally {
      setLoading(false);
    }
  };

  const register = async (username, email, password, inviteCode) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/register`, { 
        username, 
        email, 
        password, 
        invite_code: inviteCode 
      });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setIsAdmin(false);
      return true;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setIsAdmin(false);
  };

  return (
    <AuthContext.Provider value={{ 
      token, 
      user, 
      isAdmin, 
      login, 
      adminLogin, 
      register, 
      logout, 
      loading 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
