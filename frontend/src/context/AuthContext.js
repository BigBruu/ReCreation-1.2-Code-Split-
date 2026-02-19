import React, { useState, useEffect, createContext, useContext } from 'react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) {
      const storedIsAdmin = localStorage.getItem('isAdmin') === 'true';
      setIsAdmin(storedIsAdmin);
      
      if (!storedIsAdmin) {
        fetchUser();
      }
    } else {
      setIsAdmin(false);
      localStorage.removeItem('isAdmin');
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      logout();
    }
  };

  const login = async (username, password) => {
    setLoading(true);
    try {
      localStorage.removeItem('isAdmin');
      
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
      localStorage.setItem('isAdmin', 'true');
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
      localStorage.removeItem('isAdmin');
      
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
    localStorage.removeItem('isAdmin');
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
