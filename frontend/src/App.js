import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/toaster';
import { useToast } from './hooks/use-toast';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = React.createContext();

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false); // Start with false, not from localStorage
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Only check localStorage for admin status if we have a token
    if (token) {
      const storedIsAdmin = localStorage.getItem('isAdmin') === 'true';
      setIsAdmin(storedIsAdmin);
      
      if (!storedIsAdmin) {
        // For normal users, fetch user data
        fetchUser();
      }
    } else {
      // No token, clear admin status
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
      // Clear any existing admin status
      localStorage.removeItem('isAdmin');
      
      const response = await axios.post(`${API}/login`, { username, password });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      setIsAdmin(false); // Explicitly set to false for normal users
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
      // Clear any existing admin status
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
      setIsAdmin(false); // Explicitly set to false for new users
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

// Login Component
const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [isAdmin, setIsAdminMode] = useState(false);
  const [formData, setFormData] = useState({ 
    username: '', 
    email: '', 
    password: '', 
    inviteCode: '',
    adminPassword: ''
  });
  const { login, adminLogin, register, loading } = useAuth();
  const { toast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isAdmin) {
        await adminLogin(formData.adminPassword);
        toast({ title: "Erfolg!", description: "Admin-Login erfolgreich" });
      } else if (isLogin) {
        await login(formData.username, formData.password);
        toast({ title: "Erfolg!", description: "Anmeldung erfolgreich" });
      } else {
        if (!formData.inviteCode.trim()) {
          toast({ title: "Fehler", description: "Einladungscode erforderlich", variant: "destructive" });
          return;
        }
        await register(formData.username, formData.email, formData.password, formData.inviteCode);
        toast({ title: "Erfolg!", description: "Registrierung erfolgreich - Raumhafen wird zugewiesen..." });
      }
      
      // Auto-redirect
      setTimeout(() => {
        window.location.href = isAdmin ? '/admin' : '/game';
      }, 1500);
    } catch (error) {
      toast({ title: "Fehler", description: error.message, variant: "destructive" });
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4 starfield">
      <div className="bg-gray-900 p-8 rounded-lg border border-blue-500 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-blue-400 mb-2">TheReCreation</h1>
          <p className="text-gray-400">Authentisches Browser-Strategiespiel</p>
          <p className="text-xs text-gray-500 mt-2">47x47 Universum • Einladung erforderlich • Runde 10</p>
        </div>

        {/* Mode Selection */}
        <div className="flex space-x-2 mb-6">
          <button
            onClick={() => { setIsAdminMode(false); setIsLogin(true); }}
            className={`flex-1 py-2 px-3 rounded text-sm ${!isAdmin ? 'bg-blue-600' : 'bg-gray-700'}`}
          >
            Spieler
          </button>
          <button
            onClick={() => setIsAdminMode(true)}
            className={`flex-1 py-2 px-3 rounded text-sm ${isAdmin ? 'bg-red-600' : 'bg-gray-700'}`}
          >
            Admin
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isAdmin ? (
            <div>
              <label className="block text-sm font-medium mb-1">Admin-Passwort</label>
              <input
                type="password"
                value={formData.adminPassword}
                onChange={(e) => setFormData({...formData, adminPassword: e.target.value})}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                placeholder="Admin-Passwort eingeben"
                required
              />
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium mb-1">Spielername</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                  required
                />
              </div>

              {!isLogin && (
                <div>
                  <label className="block text-sm font-medium mb-1">E-Mail</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                    required
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-1">Passwort</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                  required
                />
              </div>

              {!isLogin && (
                <div>
                  <label className="block text-sm font-medium mb-1">Einladungscode *</label>
                  <input
                    type="text"
                    value={formData.inviteCode}
                    onChange={(e) => setFormData({...formData, inviteCode: e.target.value.toUpperCase()})}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:border-blue-400 focus:outline-none"
                    placeholder="8-stelliger Code"
                    maxLength="8"
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Erforderlich für Registrierung</p>
                </div>
              )}
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-2 rounded font-medium transition-colors"
          >
            {loading ? 'Lade...' : (isAdmin ? 'Admin-Login' : (isLogin ? 'Anmelden' : 'Registrieren'))}
          </button>
        </form>

        {!isAdmin && (
          <div className="text-center mt-4">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-blue-400 hover:text-blue-300 text-sm"
            >
              {isLogin ? 'Kein Account? Registrieren' : 'Bereits Account? Anmelden'}
            </button>
          </div>
        )}

        <div className="text-center mt-4 text-xs text-gray-500">
          <p>🔒 Geschlossenes Spiel - Nur mit Einladung</p>
        </div>
      </div>
    </div>
  );
};

// Admin Panel Component
const AdminPanel = () => {
  const { logout } = useAuth();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [config, setConfig] = useState(null);
  const [users, setUsers] = useState([]);
  const [inviteCodes, setInviteCodes] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [statsRes, configRes, usersRes, codesRes] = await Promise.all([
        axios.get(`${API}/admin/stats`, { headers }),
        axios.get(`${API}/admin/config`, { headers }),
        axios.get(`${API}/admin/users`, { headers }),
        axios.get(`${API}/admin/invite-codes`, { headers })
      ]);

      setStats(statsRes.data);
      setConfig(configRes.data);
      setUsers(usersRes.data);
      setInviteCodes(codesRes.data);
    } catch (error) {
      toast({ title: "Fehler", description: "Admin-Daten konnten nicht geladen werden", variant: "destructive" });
    }
  };

  const createInviteCode = async (maxUses = 1, expiresInHours = 24) => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/admin/invite-codes`, {
        max_uses: maxUses,
        expires_in_hours: expiresInHours
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast({ title: "Erfolg", description: `Einladungscode erstellt: ${response.data.code}` });
      fetchAdminData();
    } catch (error) {
      toast({ title: "Fehler", description: "Code konnte nicht erstellt werden", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const deleteUser = async (userId, username) => {
    if (!window.confirm(`Spieler "${username}" wirklich löschen?`)) return;

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/admin/users/${userId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast({ title: "Erfolg", description: `Spieler "${username}" gelöscht` });
      fetchAdminData();
    } catch (error) {
      toast({ title: "Fehler", description: "Spieler konnte nicht gelöscht werden", variant: "destructive" });
    }
  };

  const resetGame = async () => {
    if (!window.confirm('ACHTUNG: Spiel komplett zurücksetzen? Alle Spieler und Daten werden gelöscht!')) return;

    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/admin/reset-game`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast({ title: "Erfolg", description: "Spiel wurde zurückgesetzt" });
      fetchAdminData();
    } catch (error) {
      toast({ title: "Fehler", description: "Spiel konnte nicht zurückgesetzt werden", variant: "destructive" });
    }
  };

  const updateConfig = async (newConfig) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/admin/config`, newConfig, {
        headers: { Authorization: `Bearer ${token}` }
      });

      toast({ title: "Erfolg", description: "Konfiguration aktualisiert" });
      fetchAdminData();
    } catch (error) {
      toast({ title: "Fehler", description: "Konfiguration konnte nicht aktualisiert werden", variant: "destructive" });
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="bg-red-900 border-b-2 border-red-500 p-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-red-400">TheReCreation - Admin Panel</h1>
            <p className="text-sm text-gray-400">Vollzugriff auf Spielkonfiguration</p>
          </div>
          <button onClick={logout} className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded">
            Logout
          </button>
        </div>
      </div>

      <div className="flex">
        <div className="w-64 bg-gray-900 border-r-2 border-red-500 h-screen p-4">
          <div className="space-y-2">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: '📊' },
              { id: 'config', label: 'Konfiguration', icon: '⚙️' },
              { id: 'users', label: 'Spieler', icon: '👥' },
              { id: 'invites', label: 'Einladungen', icon: '🎫' },
              { id: 'actions', label: 'Aktionen', icon: '🛠️' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full text-left p-3 rounded transition-colors ${
                  activeTab === tab.id ? 'bg-red-600' : 'bg-gray-800 hover:bg-gray-700'
                }`}
              >
                <span className="mr-2">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 p-6">
          {activeTab === 'dashboard' && stats && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold">Dashboard</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-gray-800 p-6 rounded border border-gray-700">
                  <h3 className="text-lg font-semibold text-blue-400">Spieler</h3>
                  <p className="text-2xl font-bold">{stats.players.current}/{stats.players.max}</p>
                </div>
                <div className="bg-gray-800 p-6 rounded border border-gray-700">
                  <h3 className="text-lg font-semibold text-green-400">Planeten</h3>
                  <p className="text-2xl font-bold">{stats.planets.occupied}/{stats.planets.total}</p>
                </div>
                <div className="bg-gray-800 p-6 rounded border border-gray-700">
                  <h3 className="text-lg font-semibold text-purple-400">Flotten</h3>
                  <p className="text-2xl font-bold">{stats.fleets}</p>
                </div>
                <div className="bg-gray-800 p-6 rounded border border-gray-700">
                  <h3 className="text-lg font-semibold text-yellow-400">Einladungen</h3>
                  <p className="text-2xl font-bold">{stats.invite_codes}</p>
                </div>
              </div>
              <div className="bg-gray-800 p-6 rounded border border-gray-700">
                <h3 className="text-lg font-semibold mb-4">Spiel-Infos</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>Universum: {stats.universe_size}</div>
                  <div>Tick-Dauer: {stats.tick_duration}</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'config' && config && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold">Spielkonfiguration</h2>
              <div className="bg-gray-800 p-6 rounded border border-gray-700">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">Max. Spieler (5-30)</label>
                    <input
                      type="number"
                      min="5"
                      max="30"
                      value={config.max_players}
                      onChange={(e) => setConfig({...config, max_players: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Universum-Größe (35-50)</label>
                    <input
                      type="number"
                      min="35"
                      max="50"
                      value={config.universe_size}
                      onChange={(e) => setConfig({...config, universe_size: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Tick-Dauer (1-60s)</label>
                    <input
                      type="number"
                      min="1"
                      max="60"
                      value={config.tick_duration}
                      onChange={(e) => setConfig({...config, tick_duration: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Mining-Effizienz (0.1-3.0)</label>
                    <input
                      type="number"
                      min="0.1"
                      max="3.0"
                      step="0.1"
                      value={config.mining_efficiency}
                      onChange={(e) => setConfig({...config, mining_efficiency: parseFloat(e.target.value)})}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">Kolonisierungszeit (1-168h)</label>
                    <input
                      type="number"
                      min="1"
                      max="168"
                      value={config.colonization_time_hours}
                      onChange={(e) => setConfig({...config, colonization_time_hours: parseInt(e.target.value)})}
                      className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded"
                    />
                  </div>
                </div>
                <button
                  onClick={() => updateConfig(config)}
                  className="mt-4 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
                >
                  Konfiguration speichern
                </button>
              </div>
            </div>
          )}

          {activeTab === 'users' && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold">Spielerverwaltung ({users.length})</h2>
              <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-2 text-left">Spielername</th>
                        <th className="px-4 py-2 text-left">E-Mail</th>
                        <th className="px-4 py-2 text-left">Planeten</th>
                        <th className="px-4 py-2 text-left">Flotten</th>
                        <th className="px-4 py-2 text-left">Registriert</th>
                        <th className="px-4 py-2 text-left">Aktionen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map(user => (
                        <tr key={user.id} className="border-t border-gray-700">
                          <td className="px-4 py-2 font-semibold">{user.username}</td>
                          <td className="px-4 py-2 text-sm text-gray-400">{user.email}</td>
                          <td className="px-4 py-2">{user.planets}</td>
                          <td className="px-4 py-2">{user.fleets}</td>
                          <td className="px-4 py-2 text-sm">
                            {new Date(user.created_at).toLocaleDateString('de-DE')}
                          </td>
                          <td className="px-4 py-2">
                            <button
                              onClick={() => deleteUser(user.id, user.username)}
                              className="bg-red-600 hover:bg-red-700 px-2 py-1 rounded text-xs"
                            >
                              Löschen
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'invites' && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold">Einladungscodes</h2>
              <div className="flex space-x-4">
                <button
                  onClick={() => createInviteCode(1, 24)}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-4 py-2 rounded"
                >
                  1x Code (24h)
                </button>
                <button
                  onClick={() => createInviteCode(5, 168)}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-4 py-2 rounded"
                >
                  5x Code (7 Tage)
                </button>
                <button
                  onClick={() => createInviteCode(1, null)}
                  disabled={loading}
                  className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 px-4 py-2 rounded"
                >
                  Permanent
                </button>
              </div>
              <div className="bg-gray-800 rounded border border-gray-700 overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-700">
                      <tr>
                        <th className="px-4 py-2 text-left">Code</th>
                        <th className="px-4 py-2 text-left">Verwendet</th>
                        <th className="px-4 py-2 text-left">Benutzer</th>
                        <th className="px-4 py-2 text-left">Läuft ab</th>
                        <th className="px-4 py-2 text-left">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {inviteCodes.map(code => (
                        <tr key={code.id} className="border-t border-gray-700">
                          <td className="px-4 py-2 font-mono font-bold text-green-400">{code.code}</td>
                          <td className="px-4 py-2">{code.current_uses}/{code.max_uses}</td>
                          <td className="px-4 py-2 text-sm">
                            {code.used_by_username || '-'}
                          </td>
                          <td className="px-4 py-2 text-sm">
                            {code.expires_at ? new Date(code.expires_at).toLocaleDateString('de-DE') : 'Nie'}
                          </td>
                          <td className="px-4 py-2">
                            <span className={`px-2 py-1 rounded text-xs ${
                              code.current_uses >= code.max_uses ? 'bg-red-600' : 
                              (code.expires_at && new Date(code.expires_at) < new Date()) ? 'bg-orange-600' :
                              'bg-green-600'
                            }`}>
                              {code.current_uses >= code.max_uses ? 'Aufgebraucht' : 
                               (code.expires_at && new Date(code.expires_at) < new Date()) ? 'Abgelaufen' :
                               'Aktiv'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'actions' && (
            <div className="space-y-6">
              <h2 className="text-xl font-bold">Aktionen</h2>
              <div className="bg-gray-800 p-6 rounded border border-gray-700 space-y-4">
                <div>
                  <h3 className="text-lg font-semibold text-red-400 mb-2">⚠️ Gefährliche Aktionen</h3>
                  <button
                    onClick={resetGame}
                    className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded"
                  >
                    Spiel komplett zurücksetzen
                  </button>
                  <p className="text-sm text-gray-500 mt-2">
                    Löscht alle Spieler, Planeten, Flotten und startet neu
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Ship Design Calculator (Rechner)
const ShipDesignCalculator = ({ onClose, onSave, componentLevels }) => {
  const [design, setDesign] = useState({
    name: '',
    drive_type: 'segel',
    drive_level: 1,
    drive_quantity: 88,
    shield_type: 'quarz',
    shield_level: 6,
    shield_quantity: 110,
    weapon_type: 'laser',
    weapon_level: 1,
    weapon_quantity: 10,
    mining_units: 0,
    colony_units: 0
  });

  const [calculatedStats, setCalculatedStats] = useState({
    speed: 0,
    combat_value: 0,
    mining_capacity: 0,
    total_weight: 0,
    build_cost: { food: 0, metal: 0, silicon: 0, hydrogen: 0 },
    build_time_ticks: 0
  });

  // Recalculate stats when design changes
  useEffect(() => {
    calculateStats();
  }, [design, componentLevels]);

  const calculateStats = () => {
    if (!componentLevels?.drives || !componentLevels?.shields || !componentLevels?.weapons) return;

    const driveData = componentLevels.drives[design.drive_type];
    const shieldData = componentLevels.shields[design.shield_type];
    const weaponData = componentLevels.weapons[design.weapon_type];

    if (!driveData || !shieldData || !weaponData) return;

    // Calculate weight
    const driveWeight = driveData.weight * design.drive_quantity;
    const shieldWeight = shieldData.weight * design.shield_quantity;
    const weaponWeight = weaponData.weight * design.weapon_quantity;
    const miningWeight = componentLevels.mining?.abbaueinheit ? 
      componentLevels.mining.abbaueinheit.weight * design.mining_units : 0;
    const colonyWeight = componentLevels.special?.kolonieeinheit ? 
      componentLevels.special.kolonieeinheit.weight * design.colony_units : 0;
    const totalWeight = driveWeight + shieldWeight + weaponWeight + miningWeight + colonyWeight;

    // Calculate speed
    const baseSpeed = driveData.speed_base * design.drive_level * design.drive_quantity;
    const speed = Math.max(1, Math.floor(baseSpeed / Math.max(1, totalWeight / 100)));

    // Calculate combat value
    const attackPower = weaponData.attack_base * design.weapon_level * design.weapon_quantity;
    const defensePower = shieldData.defense_base * design.shield_level * design.shield_quantity;
    const combatValue = attackPower + defensePower;

    // Calculate mining capacity
    const miningCapacity = componentLevels.mining?.abbaueinheit ? 
      componentLevels.mining.abbaueinheit.mining_base * design.mining_units : 0;

    // Calculate build costs
    const foodCost = colonyWeight * 4;
    const metalCost = (driveWeight + weaponWeight + miningWeight) * design.drive_level * 10;
    const siliconCost = (shieldWeight + weaponWeight) * design.shield_level * 5;
    const hydrogenCost = weaponWeight * design.weapon_level * 2;

    // Calculate build time
    let buildTime = Math.max(1, Math.floor(totalWeight / 100)) + design.drive_level + design.shield_level + design.weapon_level;
    if (design.mining_units > 0) buildTime += design.mining_units * 2;
    if (design.colony_units > 0) buildTime += design.colony_units * 5;

    setCalculatedStats({
      speed,
      combat_value: combatValue,
      mining_capacity: miningCapacity,
      total_weight: totalWeight,
      build_cost: {
        food: foodCost,
        metal: metalCost,
        silicon: siliconCost,
        hydrogen: hydrogenCost
      },
      build_time_ticks: buildTime
    });
  };

  const handleSave = () => {
    if (!design.name.trim()) {
      alert('Bitte geben Sie einen Namen für den Prototyp ein');
      return;
    }
    onSave(design);
  };

  return (
    <div className="modal-backdrop">
      <div className="ship-calculator">
        <div className="calculator-header">
          <h3>Rechner - Prototypen entwerfen</h3>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="calculator-content">
          <div className="design-inputs">
            <div className="input-group">
              <label>Prototyp Name:</label>
              <input
                type="text"
                value={design.name}
                onChange={(e) => setDesign({...design, name: e.target.value})}
                placeholder="z.B. Miner Mk1"
              />
            </div>

            <div className="component-section">
              <h4>Antrieb:</h4>
              <select value={design.drive_type} onChange={(e) => setDesign({...design, drive_type: e.target.value})}>
                {componentLevels?.drives && Object.keys(componentLevels.drives).map(type => (
                  <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                ))}
              </select>
              <span>(L{design.drive_level})</span>
              <input type="number" min="1" max="7" value={design.drive_level} 
                     onChange={(e) => setDesign({...design, drive_level: parseInt(e.target.value)})} />
              <span>Anzahl:</span>
              <input type="number" min="1" value={design.drive_quantity}
                     onChange={(e) => setDesign({...design, drive_quantity: parseInt(e.target.value)})} />
            </div>

            <div className="component-section">
              <h4>Schild:</h4>
              <select value={design.shield_type} onChange={(e) => setDesign({...design, shield_type: e.target.value})}>
                {componentLevels?.shields && Object.keys(componentLevels.shields).map(type => (
                  <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                ))}
              </select>
              <span>(L{design.shield_level})</span>
              <input type="number" min="1" max="6" value={design.shield_level}
                     onChange={(e) => setDesign({...design, shield_level: parseInt(e.target.value)})} />
              <span>Anzahl:</span>
              <input type="number" min="1" value={design.shield_quantity}
                     onChange={(e) => setDesign({...design, shield_quantity: parseInt(e.target.value)})} />
            </div>

            <div className="component-section">
              <h4>Waffe:</h4>
              <select value={design.weapon_type} onChange={(e) => setDesign({...design, weapon_type: e.target.value})}>
                {componentLevels?.weapons && Object.keys(componentLevels.weapons).map(type => (
                  <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>
                ))}
              </select>
              <span>(L{design.weapon_level})</span>
              <input type="number" min="1" max="6" value={design.weapon_level}
                     onChange={(e) => setDesign({...design, weapon_level: parseInt(e.target.value)})} />
              <span>Anzahl:</span>
              <input type="number" min="1" value={design.weapon_quantity}
                     onChange={(e) => setDesign({...design, weapon_quantity: parseInt(e.target.value)})} />
            </div>

            <div className="component-section">
              <h4>⛏️ Abbaueinheiten:</h4>
              <span>Anzahl:</span>
              <input 
                type="number" 
                min="0" 
                max="100" 
                value={design.mining_units}
                onChange={(e) => setDesign({...design, mining_units: parseInt(e.target.value)})} 
              />
              <span className="text-xs text-gray-400">
                (Summe aller Schiffe = Abbaukapazität/Tick)
              </span>
            </div>

            <div className="component-section">
              <h4>🏭 Kolonieeinheiten:</h4>
              <span>Anzahl:</span>
              <input 
                type="number" 
                min="0" 
                max="10" 
                value={design.colony_units}
                onChange={(e) => setDesign({...design, colony_units: parseInt(e.target.value)})} 
              />
              <span className="text-xs text-gray-400">
                (Für Planetenkolonisierung)
              </span>
            </div>
          </div>

          <div className="calculated-stats">
            <h4>Berechnete Werte:</h4>
            <table>
              <tbody>
                <tr><td>Beschleunigung:</td><td>{calculatedStats.speed}</td></tr>
                <tr><td>Kampfwert:</td><td>{calculatedStats.combat_value}</td></tr>
                <tr><td>Geschwindigkeit:</td><td>{calculatedStats.speed} pc/tick</td></tr>
                <tr><td>Abbaukapazität:</td><td className="resource-metal">{calculatedStats.mining_capacity} Ressourcen/Tick</td></tr>
                <tr><td>Gewicht:</td><td>{calculatedStats.total_weight}</td></tr>
                <tr><td>Bauzeit:</td><td>{calculatedStats.build_time_ticks} Ticks</td></tr>
              </tbody>
            </table>

            <h4>Baukosten:</h4>
            <table>
              <tbody>
                <tr><td>Nahrung:</td><td className="resource-food">{calculatedStats.build_cost.food.toLocaleString()}</td></tr>
                <tr><td>Metall:</td><td className="resource-metal">{calculatedStats.build_cost.metal.toLocaleString()}</td></tr>
                <tr><td>Silizium:</td><td className="resource-silicon">{calculatedStats.build_cost.silicon.toLocaleString()}</td></tr>
                <tr><td>Wasserstoff:</td><td className="resource-hydrogen">{calculatedStats.build_cost.hydrogen.toLocaleString()}</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="calculator-actions">
          <button onClick={handleSave} className="btn-primary">Prototyp speichern</button>
          <button onClick={onClose} className="btn-secondary">Abbrechen</button>
        </div>
      </div>
    </div>
  );
};

// Observatory Component (7x7 View)
const Observatory = ({ centerPosition, onPositionChange, view, onFieldClick }) => {
  const renderField = (x, y) => {
    const key = `${x},${y}`;
    const fieldData = view[key] || { planet: null, fleets: [] };
    const { planet, fleets } = fieldData;

    let planetIcon = null;
    if (planet) {
      const planetClass = `planet-${planet.planet_type}`;
      const isOwned = planet.owner_username;
      planetIcon = (
        <div className={`planet ${planetClass} ${isOwned ? 'owned' : ''}`}>
          <div className="planet-name">{planet.name}</div>
          {isOwned && <div className="planet-owner">{planet.owner_username}</div>}
        </div>
      );
    }

    const hasFleets = fleets.length > 0;

    return (
      <div
        key={key}
        className={`observatory-field ${planet ? 'has-planet' : 'empty'} ${hasFleets ? 'has-fleets' : ''}`}
        onClick={() => onFieldClick(x, y, fieldData)}
        title={`(${x},${y}) ${planet ? planet.name : 'Leerer Raum'} ${hasFleets ? `- ${fleets.length} Flotte(n)` : ''}`}
      >
        <div className="field-coordinates">{x},{y}</div>
        {planetIcon}
        {hasFleets && (
          <div className="fleet-indicator">
            {fleets.map((fleet, i) => (
              <div key={i} className="fleet-icon">🚀</div>
            ))}
          </div>
        )}
      </div>
    );
  };

  const handleNavigation = (direction) => {
    const newPos = { ...centerPosition };
    switch (direction) {
      case 'up': newPos.y = Math.max(3, newPos.y - 1); break;
      case 'down': newPos.y = Math.min(43, newPos.y + 1); break;
      case 'left': newPos.x = Math.max(3, newPos.x - 1); break;
      case 'right': newPos.x = Math.min(43, newPos.x + 1); break;
    }
    onPositionChange(newPos);
  };

  return (
    <div className="observatory-container">
      <div className="observatory-header">
        <h3>Observatorium</h3>
        <div className="observatory-nav">
          <button onClick={() => handleNavigation('up')}>↑</button>
          <div>
            <button onClick={() => handleNavigation('left')}>←</button>
            <span className="coordinates">({centerPosition.x}, {centerPosition.y})</span>
            <button onClick={() => handleNavigation('right')}>→</button>
          </div>
          <button onClick={() => handleNavigation('down')}>↓</button>
        </div>
      </div>
      
      <div className="observatory-grid">
        {Array.from({ length: 7 }, (_, row) => {
          const y = centerPosition.y - 3 + row; // -3 to +3
          return (
            <div key={row} className="observatory-row">
              <div className="row-label">{y}</div>
              {Array.from({ length: 7 }, (_, col) => {
                const x = centerPosition.x - 3 + col;
                if (x >= 0 && x < 47 && y >= 0 && y < 47) {
                  return renderField(x, y);
                }
                return <div key={col} className="observatory-field empty"></div>;
              })}
            </div>
          );
        })}
      </div>
      
      <div className="observatory-legend">
        <div className="legend-item">
          <div className="planet planet-green"></div>
          <span>Grüner Planet</span>
        </div>
        <div className="legend-item">
          <div className="planet planet-blue"></div>
          <span>Blauer Planet</span>
        </div>
        <div className="legend-item">
          <div className="planet planet-brown"></div>
          <span>Brauner Planet</span>
        </div>
        <div className="legend-item">
          <div className="planet planet-orange"></div>
          <span>Oranger Planet</span>
        </div>
      </div>
    </div>
  );
};

// Game Interface (FULL VERSION)
const GameInterface = () => {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const [gameState, setGameState] = useState(null);
  const [observatoryView, setObservatoryView] = useState({});
  const [centerPosition, setCenterPosition] = useState({ x: 23, y: 23 });
  const [userPlanets, setUserPlanets] = useState([]);
  const [userFleets, setUserFleets] = useState([]);
  const [shipDesigns, setShipDesigns] = useState([]);
  const [spaceportShips, setSpaceportShips] = useState({});
  const [userResearch, setUserResearch] = useState(null);
  const [researchCosts, setResearchCosts] = useState(null);
  const [componentLevels, setComponentLevels] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [activeTab, setActiveTab] = useState('observatorium');
  const [selectedField, setSelectedField] = useState(null);
  const [showShipCalculator, setShowShipCalculator] = useState(false);

  useEffect(() => {
    fetchGameData();
    const interval = setInterval(fetchGameData, 15000); // Update every 15 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (user?.spaceport_position && user.spaceport_position.x !== -1) {
      setCenterPosition(user.spaceport_position);
    }
  }, [user]);

  useEffect(() => {
    if (centerPosition.x !== -1) {
      fetchObservatoryView();
    }
  }, [centerPosition]);

  const fetchGameData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [gameStateRes, planetsRes, fleetsRes, designsRes, componentRes, rankingsRes, researchRes, costsRes, spaceportRes] = await Promise.all([
        axios.get(`${API}/game/state`, { headers }),
        axios.get(`${API}/game/planets`, { headers }),
        axios.get(`${API}/game/fleets`, { headers }),
        axios.get(`${API}/game/ship-designs`, { headers }),
        axios.get(`${API}/game/component-levels`, { headers }),
        axios.get(`${API}/game/rankings`, { headers }),
        axios.get(`${API}/game/research`, { headers }),
        axios.get(`${API}/game/research/costs`, { headers }),
        axios.get(`${API}/game/spaceport-ships`, { headers })
      ]);

      setGameState(gameStateRes.data);
      setUserPlanets(planetsRes.data);
      setUserFleets(fleetsRes.data);
      setShipDesigns(designsRes.data);
      setComponentLevels(componentRes.data);
      setRankings(rankingsRes.data);
      setUserResearch(researchRes.data);
      setResearchCosts(costsRes.data);
      setSpaceportShips(spaceportRes.data);
    } catch (error) {
      console.error('Failed to fetch game data:', error);
    }
  };

  const fetchObservatoryView = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/game/observatory`, {
        center_x: centerPosition.x,
        center_y: centerPosition.y
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setObservatoryView(response.data.view);
    } catch (error) {
      console.error('Failed to fetch observatory view:', error);
    }
  };

  const handleFieldClick = (x, y, fieldData) => {
    setSelectedField({ x, y, ...fieldData });
  };

  const handlePositionChange = (newPosition) => {
    setCenterPosition(newPosition);
  };

  const handleSaveShipDesign = async (designData) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/ship-design`, designData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast({ title: "Erfolg", description: "Prototyp erstellt!" });
      setShowShipCalculator(false);
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: error.response?.data?.detail || 'Fehler beim Erstellen des Prototyps',
        variant: "destructive" 
      });
    }
  };

  const handleBuildShips = async (designId) => {
    try {
      const planetSelect = document.getElementById(`planet-${designId}`);
      const quantityInput = document.getElementById(`quantity-${designId}`);
      
      const planetId = planetSelect.value;
      const quantity = parseInt(quantityInput.value);
      
      if (!planetId) {
        toast({ title: "Fehler", description: "Bitte wählen Sie einen Planeten", variant: "destructive" });
        return;
      }
      
      if (!quantity || quantity < 1) {
        toast({ title: "Fehler", description: "Bitte geben Sie eine gültige Anzahl ein", variant: "destructive" });
        return;
      }

      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/game/build-ships`, {
        planet_id: planetId,
        design_id: designId,
        quantity: quantity
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Erfolg", description: `${quantity} Schiffe im Raumhafen produziert!` });
      
      // Reset form
      planetSelect.value = '';
      quantityInput.value = '';
      
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: error.response?.data?.detail || 'Schiffsproduktion fehlgeschlagen',
        variant: "destructive" 
      });
    }
  };

  const processTick = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/tick`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast({ title: "Erfolg", description: "Tick verarbeitet!" });
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: 'Fehler beim Verarbeiten des Ticks',
        variant: "destructive" 
      });
    }
  };

  const formatNextTick = () => {
    if (!gameState?.next_tick_time) return 'Unbekannt';
    const nextTick = new Date(gameState.next_tick_time);
    const now = new Date();
    const diff = Math.max(0, Math.floor((nextTick - now) / 1000));
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const calculateResearchCost = (baseCost, currentLevel) => {
    const reductionFactor = Math.pow(0.85, currentLevel); // 15% reduction per level
    return Math.floor(baseCost * reductionFactor * (currentLevel + 1));
  };

  const startResearch = async (category, technology) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/game/research/start`, {
        category,
        technology
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ 
        title: "Forschung gestartet!", 
        description: `${technology} wird erforscht. Kosten: ${response.data.cost.toLocaleString()} Nahrung` 
      });
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: error.response?.data?.detail || 'Forschung konnte nicht gestartet werden',
        variant: "destructive" 
      });
    }
  };

  return (
    <div className="game-layout starfield">
      {/* Authentic Header */}
      <div className="game-header authentic-header">
        <div className="header-left">
          <div className="game-info">
            <div>Uhrzeit: {new Date().toLocaleString('de-DE')}</div>
            <div>nexttick: {gameState?.next_tick_time ? new Date(gameState.next_tick_time).toLocaleString('de-DE') : 'Lade...'}</div>
            <div>Tickdauer: {formatNextTick()}</div>
          </div>
        </div>
        
        <div className="header-center">
          <h1 className="game-title">TheReCreation</h1>
          <div className="game-subtitle">Runde 10 • Tick: {gameState?.current_tick || 0}</div>
        </div>

        <div className="header-right">
          <div className="user-resources">
            {userPlanets.length > 0 && (
              <div className="resource-display">
                <div className="resource-item">
                  <span className="resource-label">Nahrung</span>
                  <span className="resource-value resource-food">
                    {userPlanets.reduce((sum, p) => sum + p.resources.food, 0).toLocaleString()}
                  </span>
                </div>
                <div className="resource-item">
                  <span className="resource-label">Metall</span>
                  <span className="resource-value resource-metal">
                    {userPlanets.reduce((sum, p) => sum + p.resources.metal, 0).toLocaleString()}
                  </span>
                </div>
                <div className="resource-item">
                  <span className="resource-label">Silizium</span>
                  <span className="resource-value resource-silicon">
                    {userPlanets.reduce((sum, p) => sum + p.resources.silicon, 0).toLocaleString()}
                  </span>
                </div>
                <div className="resource-item">
                  <span className="resource-label">Wasserstoff</span>
                  <span className="resource-value resource-hydrogen">
                    {userPlanets.reduce((sum, p) => sum + p.resources.hydrogen, 0).toLocaleString()}
                  </span>
                </div>
              </div>
            )}
          </div>
          <button onClick={logout} className="logout-btn">Logout</button>
        </div>
      </div>

      <div className="game-main-layout">
        {/* Sidebar Navigation */}
        <div className="game-sidebar authentic-sidebar">
          <div className="sidebar-nav">
            {[
              { id: 'observatorium', label: 'Observatorium' },
              { id: 'raumhafen', label: 'Raumhafen' },
              { id: 'einrichtungen', label: 'Einrichtungen' },
              { id: 'technologie', label: 'Technologie' },
              { id: 'werft', label: 'Werft' },
              { id: 'handelszentrum', label: 'Handelszentrum' },
              { id: 'allianzen', label: 'Allianzen' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`sidebar-tab ${activeTab === tab.id ? 'active' : ''}`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="sidebar-secondary">
            <button className="sidebar-link">Startseite</button>
            <button className="sidebar-link">Forum</button>
            <button className="sidebar-link">Rangliste</button>
            <button className="sidebar-link">Hall of Fame</button>
            <button className="sidebar-link">Statistiken</button>
            <button className="sidebar-link">Release Info</button>
            <button className="sidebar-link">Hilfe</button>
          </div>

          <div className="sidebar-actions">
            <button onClick={processTick} className="btn-primary">Tick verarbeiten</button>
          </div>
        </div>

        {/* Main Content */}
        <div className="game-content">
          {activeTab === 'raumhafen' && (
            <div className="spaceport-content">
              <h3>🚀 Raumhafen - Schiffe & Flotten</h3>
              
              {/* Ships in Spaceport */}
              <div className="spaceport-ships">
                <h4>Schiffe im Raumhafen</h4>
                {Object.keys(spaceportShips).length > 0 ? (
                  Object.entries(spaceportShips).map(([planetKey, planetData]) => (
                    <div key={planetKey} className="spaceport-planet">
                      <h5>{planetData.planet_name} ({planetData.position.x}, {planetData.position.y})</h5>
                      <div className="spaceport-ships-list">
                        {planetData.ships.map(ship => (
                          <div key={ship.id} className="spaceport-ship">
                            <span className="ship-design">{ship.design_name}</span>
                            <span className="ship-quantity">x{ship.quantity}</span>
                            <span className="ship-date">
                              {new Date(ship.created_at).toLocaleDateString('de-DE')}
                            </span>
                          </div>
                        ))}
                      </div>
                      
                      {/* Fleet Creation */}
                      <div className="fleet-creation">
                        <h6>Flotte erstellen:</h6>
                        <input
                          type="text"
                          placeholder="Flottenname"
                          id={`fleet-name-${planetData.planet_id}`}
                          className="fleet-name-input"
                        />
                        <div className="ship-selection">
                          {planetData.ships.map(ship => (
                            <div key={ship.id} className="ship-selector">
                              <label>{ship.design_name}:</label>
                              <input
                                type="number"
                                min="0"
                                max={ship.quantity}
                                placeholder="0"
                                id={`ship-${ship.id}-quantity`}
                                className="ship-quantity-input"
                              />
                              <span className="max-available">/{ship.quantity}</span>
                            </div>
                          ))}
                        </div>
                        <button
                          onClick={() => createFleet(planetData)}
                          className="btn-primary create-fleet-btn"
                        >
                          Flotte erstellen
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-400">Keine Schiffe im Raumhafen. Produzieren Sie Schiffe in der Werft.</p>
                )}
              </div>

              {/* Active Fleets */}
              <div className="active-fleets">
                <h4>Aktive Flotten ({userFleets.length})</h4>
                {userFleets.map(fleet => (
                  <div key={fleet.id} className="fleet-card">
                    <h5>{fleet.name}</h5>
                    <div className="fleet-position">
                      Position: ({fleet.position.x}, {fleet.position.y})
                    </div>
                    <div className="fleet-ships">
                      {fleet.ships.map((shipGroup, i) => {
                        const design = shipDesigns.find(d => d.id === shipGroup.design_id);
                        return (
                          <div key={i} className="fleet-ship-group">
                            {design?.name || 'Unbekanntes Design'}: {shipGroup.quantity}
                          </div>
                        );
                      })}
                    </div>
                    <div className="fleet-stats">
                      Geschwindigkeit: {fleet.fleet_speed} pc/tick
                      {fleet.movement_end_time && (
                        <div className="movement-info">
                          Ankunft: {new Date(fleet.movement_end_time).toLocaleString('de-DE')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'observatorium' && (
            <Observatory
              centerPosition={centerPosition}
              onPositionChange={handlePositionChange}
              view={observatoryView}
              onFieldClick={handleFieldClick}
            />
          )}

          {activeTab === 'werft' && (
            <div className="werft-content">
              <div className="werft-header">
                <h3>Werft - Raumschiff-Prototypen</h3>
                <button 
                  onClick={() => setShowShipCalculator(true)}
                  className="btn-primary"
                >
                  Rechner - Prototypen entwerfen
                </button>
              </div>

              <div className="prototypes-list">
                <h4>Ihre Prototypen ({shipDesigns.length})</h4>
                {shipDesigns.map(design => (
                  <div key={design.id} className="prototype-card">
                    <h5>{design.name}</h5>
                    <div className="prototype-stats">
                      <div>Antrieb: {design.drive.component_name} (L{design.drive.level}) x{design.drive.quantity}</div>
                      <div>Schild: {design.shield.component_name} (L{design.shield.level}) x{design.shield.quantity}</div>
                      <div>Waffe: {design.weapon.component_name} (L{design.weapon.level}) x{design.weapon.quantity}</div>
                      {design.mining_units > 0 && <div>⛏️ Abbaueinheiten: {design.mining_units}</div>}
                      {design.colony_units > 0 && <div>🏭 Kolonieeinheiten: {design.colony_units}</div>}
                      <div className="stats-row">
                        <span>Geschwindigkeit: {design.calculated_stats.speed} pc/tick</span>
                        <span>Kampfwert: {design.calculated_stats.combat_value}</span>
                        {design.calculated_stats.mining_capacity > 0 && 
                          <span>Abbau: {design.calculated_stats.mining_capacity}/tick</span>}
                        <span>Bauzeit: {design.calculated_stats.build_time_ticks} Ticks</span>
                      </div>
                    </div>
                    
                    {/* Ship Production Section */}
                    <div className="production-section">
                      <h6>Schiffe produzieren:</h6>
                      <div className="production-controls">
                        {userPlanets.length > 0 ? (
                          <div className="production-form">
                            <select 
                              id={`planet-${design.id}`}
                              className="production-select"
                            >
                              <option value="">Planet wählen...</option>
                              {userPlanets.map(planet => (
                                <option key={planet.id} value={planet.id}>
                                  {planet.name} ({planet.position.x}, {planet.position.y})
                                </option>
                              ))}
                            </select>
                            <input
                              type="number"
                              placeholder="Anzahl"
                              min="1"
                              max="1000"
                              id={`quantity-${design.id}`}
                              className="production-input"
                            />
                            <button
                              onClick={() => handleBuildShips(design.id)}
                              className="btn-success production-btn"
                            >
                              Im Raumhafen bauen
                            </button>
                          </div>
                        ) : (
                          <p className="text-sm text-gray-400">
                            Keine Planeten verfügbar für Produktion
                          </p>
                        )}
                      </div>
                      
                      {/* Show build costs */}
                      <div className="build-costs">
                        <h6>Baukosten pro Schiff:</h6>
                        <div className="cost-display">
                          <span className="resource-food">🌾 {design.calculated_stats.build_cost?.food || 0}</span>
                          <span className="resource-metal">⚙️ {design.calculated_stats.build_cost?.metal || 0}</span>
                          <span className="resource-silicon">💎 {design.calculated_stats.build_cost?.silicon || 0}</span>
                          <span className="resource-hydrogen">⚡ {design.calculated_stats.build_cost?.hydrogen || 0}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'einrichtungen' && (
            <div className="facilities-content">
              <h3>Planeten & Einrichtungen</h3>
              <div className="planets-list">
                {userPlanets.map(planet => (
                  <div key={planet.id} className={`planet-card planet-${planet.planet_type}`}>
                    <h4>{planet.name}</h4>
                    <div className="planet-position">Position: ({planet.position.x}, {planet.position.y})</div>
                    <div className="planet-resources">
                      <div>🌾 Nahrung: {planet.resources.food.toLocaleString()}</div>
                      <div>⚙️ Metall: {planet.resources.metal.toLocaleString()}</div>
                      <div>💎 Silizium: {planet.resources.silicon.toLocaleString()}</div>
                      <div>⚡ Wasserstoff: {planet.resources.hydrogen.toLocaleString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'technologie' && (
            <div className="research-content">
              <h3>Forschung - Alle starten bei Level 0</h3>
              <div className="research-categories">
                {['drives', 'shields', 'weapons'].map(category => (
                  <div key={category} className="research-category">
                    <h4>
                      {category === 'drives' ? '🚀 Antriebe' : 
                       category === 'shields' ? '🛡️ Schilde' : 
                       '⚔️ Waffen'}
                    </h4>
                    <div className="research-techs">
                      {userResearch?.research_levels
                        .filter(tech => tech.category === category)
                        .map(tech => {
                          const baseCost = researchCosts?.[category]?.[tech.technology]?.base_cost || 0;
                          const actualCost = calculateResearchCost(baseCost, tech.level);
                          const isResearching = tech.researching;
                          
                          return (
                            <div key={tech.technology} className="research-tech">
                              <div className="tech-header">
                                <span className="tech-name">
                                  {tech.technology.charAt(0).toUpperCase() + tech.technology.slice(1)}
                                </span>
                                <span className="tech-level">Level {tech.level}</span>
                              </div>
                              
                              <div className="tech-details">
                                <div className="tech-cost">
                                  Kosten: <span className="resource-food">{actualCost.toLocaleString()} Nahrung</span>
                                </div>
                                {tech.level > 0 && (
                                  <div className="tech-reduction">
                                    15% Kostenreduktion erreicht
                                  </div>
                                )}
                              </div>
                              
                              {isResearching ? (
                                <div className="research-progress">
                                  <span className="researching-indicator">🔬 Erforscht...</span>
                                  <div className="research-time">
                                    Fertig: {tech.research_end_time ? 
                                      new Date(tech.research_end_time).toLocaleString('de-DE') : 'Berechne...'
                                    }
                                  </div>
                                </div>
                              ) : (
                                <button
                                  onClick={() => startResearch(category, tech.technology)}
                                  className="btn-primary research-btn"
                                  disabled={userResearch?.research_levels.some(r => r.researching)}
                                >
                                  Erforschen
                                </button>
                              )}
                            </div>
                          );
                        })}
                    </div>
                  </div>
                ))}
              </div>
              
              <div className="research-info">
                <h4>📚 Forschungs-Regeln:</h4>
                <ul>
                  <li>• Alle Technologien starten bei Level 0</li>
                  <li>• Nur eine Forschung gleichzeitig möglich</li>
                  <li>• Kostenverringerung pro Level: 15%</li>
                  <li>• Forschung kostet nur Nahrung</li>
                  <li>• Forschungszeit steigt mit Level</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Field Info Panel */}
        {selectedField && (
          <div className="field-info-panel">
            <h4>Feld ({selectedField.x}, {selectedField.y})</h4>
            {selectedField.planet ? (
              <div className="planet-info">
                <h5>{selectedField.planet.name}</h5>
                <div>Typ: {selectedField.planet.planet_type}</div>
                {selectedField.planet.owner_username && (
                  <div>Besitzer: {selectedField.planet.owner_username}</div>
                )}
                <div className="planet-resources">
                  <div>🌾 {selectedField.planet.resources.food.toLocaleString()}</div>
                  <div>⚙️ {selectedField.planet.resources.metal.toLocaleString()}</div>
                  <div>💎 {selectedField.planet.resources.silicon.toLocaleString()}</div>
                  <div>⚡ {selectedField.planet.resources.hydrogen.toLocaleString()}</div>
                </div>
              </div>
            ) : (
              <div>Leerer Raum</div>
            )}
            
            {selectedField.fleets?.length > 0 && (
              <div className="fleets-info">
                <h5>Flotten ({selectedField.fleets.length})</h5>
                {selectedField.fleets.map((fleet, i) => (
                  <div key={i} className="fleet-info">
                    <div>{fleet.name}</div>
                    <div>von {fleet.username}</div>
                  </div>
                ))}
              </div>
            )}

            <button onClick={() => setSelectedField(null)} className="close-panel">×</button>
          </div>
        )}
      </div>

      {/* Ship Calculator Modal */}
      {showShipCalculator && (
        <ShipDesignCalculator
          onClose={() => setShowShipCalculator(false)}
          onSave={handleSaveShipDesign}
          componentLevels={componentLevels}
        />
      )}
    </div>
  );
};

// Protected Route Components
const ProtectedRoute = ({ children }) => {
  const { token, isAdmin } = useAuth();
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  // Admin users should stay in admin panel
  if (isAdmin) {
    return <Navigate to="/admin" replace />;
  }
  
  return children;
};

const AdminRoute = ({ children }) => {
  const { token, isAdmin } = useAuth();
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  if (!isAdmin) {
    return <Navigate to="/game" replace />;
  }
  
  return children;
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="App">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route 
              path="/admin" 
              element={
                <AdminRoute>
                  <AdminPanel />
                </AdminRoute>
              } 
            />
            <Route 
              path="/game" 
              element={
                <ProtectedRoute>
                  <GameInterface />
                </ProtectedRoute>
              } 
            />
            <Route path="/" element={<Navigate to="/login" replace />} />
          </Routes>
          <Toaster />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;