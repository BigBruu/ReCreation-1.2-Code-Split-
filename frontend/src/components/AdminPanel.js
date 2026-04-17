import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../hooks/use-toast';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DEFAULT_NEW_ROUND = {
  resources_per_planet: 50000000,
  planet_count: 180,
  universe_size: 47,
  tick_duration: 60,
  max_players: 20,
};

const AdminPanel = () => {
  const { logout } = useAuth();
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState(null);
  const [config, setConfig] = useState(null);
  const [users, setUsers] = useState([]);
  const [inviteCodes, setInviteCodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [newRound, setNewRound] = useState(DEFAULT_NEW_ROUND);
  const [newRoundResult, setNewRoundResult] = useState(null);

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

  const startNewRound = async () => {
    if (!window.confirm(
      `ACHTUNG: Neue Runde starten?\n\n` +
      `Spielfeld: ${newRound.universe_size}x${newRound.universe_size}\n` +
      `Planeten: ${newRound.planet_count}\n` +
      `Ressourcen/Planet: ${Number(newRound.resources_per_planet).toLocaleString('de-DE')}\n` +
      `Tick-Dauer: ${newRound.tick_duration}s\n` +
      `Max. Spieler: ${newRound.max_players}\n\n` +
      `Alle aktuellen Daten (Spieler, Planeten, Flotten) werden gelöscht!`
    )) return;

    try {
      setLoading(true);
      setNewRoundResult(null);
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/admin/new-round`, {
        resources_per_planet: Number(newRound.resources_per_planet),
        planet_count:         Number(newRound.planet_count),
        universe_size:        Number(newRound.universe_size),
        tick_duration:        Number(newRound.tick_duration),
        max_players:          Number(newRound.max_players),
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setNewRoundResult(response.data);
      toast({ title: "Erfolg", description: response.data.message });
      fetchAdminData();
    } catch (error) {
      const detail = error.response?.data?.detail || "Neue Runde konnte nicht gestartet werden";
      toast({ title: "Fehler", description: detail, variant: "destructive" });
    } finally {
      setLoading(false);
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

  const fieldCls = "w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white";
  const labelCls = "block text-sm font-medium mb-1 text-gray-300";

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
              { id: 'dashboard',   label: 'Dashboard',    icon: '📊' },
              { id: 'neue-runde',  label: 'Neue Runde',   icon: '🚀' },
              { id: 'config',      label: 'Konfiguration', icon: '⚙️' },
              { id: 'users',       label: 'Spieler',       icon: '👥' },
              { id: 'invites',     label: 'Einladungen',   icon: '🎫' },
              { id: 'actions',     label: 'Aktionen',      icon: '🛠️' }
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

          {/* ── DASHBOARD ── */}
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

          {/* ── NEUE RUNDE ── */}
          {activeTab === 'neue-runde' && (
            <div className="space-y-6 max-w-2xl">
              <h2 className="text-xl font-bold">Neue Runde starten</h2>
              <p className="text-sm text-gray-400">
                Alle laufenden Daten (Spieler, Planeten, Flotten) werden gelöscht und das Universum
                mit den unten angegebenen Einstellungen neu generiert.
              </p>

              <div className="bg-gray-800 p-6 rounded border border-gray-700 space-y-5">

                {/* Ressourcen pro Planet */}
                <div>
                  <label className={labelCls}>
                    Ressourcen pro Planet
                  </label>
                  <input
                    type="number"
                    min="1000000"
                    max="500000000"
                    step="1000000"
                    value={newRound.resources_per_planet}
                    onChange={e => setNewRound({ ...newRound, resources_per_planet: e.target.value })}
                    className={fieldCls}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Empfehlung: 10.000.000 – 100.000.000 · Aktuell: {Number(newRound.resources_per_planet).toLocaleString('de-DE')}
                  </p>
                </div>

                {/* Anzahl Planeten */}
                <div>
                  <label className={labelCls}>
                    Anzahl Planeten mit Ressourcen
                  </label>
                  <input
                    type="number"
                    min="1"
                    max={newRound.universe_size * newRound.universe_size}
                    value={newRound.planet_count}
                    onChange={e => setNewRound({ ...newRound, planet_count: e.target.value })}
                    className={fieldCls}
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Max. bei {newRound.universe_size}×{newRound.universe_size}: {newRound.universe_size * newRound.universe_size} Felder
                  </p>
                </div>

                {/* Spielfeldgröße */}
                <div>
                  <label className={labelCls}>
                    Spielfeldgröße: {newRound.universe_size}×{newRound.universe_size}
                  </label>
                  <input
                    type="range"
                    min="15"
                    max="50"
                    value={newRound.universe_size}
                    onChange={e => setNewRound({ ...newRound, universe_size: Number(e.target.value) })}
                    className="w-full accent-red-500"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>15×15 (klein)</span>
                    <span>50×50 (groß)</span>
                  </div>
                </div>

                {/* Tick-Dauer */}
                <div>
                  <label className={labelCls}>
                    Tick-Dauer: {newRound.tick_duration} Sekunden
                  </label>
                  <input
                    type="range"
                    min="10"
                    max="60"
                    step="5"
                    value={newRound.tick_duration}
                    onChange={e => setNewRound({ ...newRound, tick_duration: Number(e.target.value) })}
                    className="w-full accent-red-500"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>10s (schnell)</span>
                    <span>60s (langsam)</span>
                  </div>
                </div>

                {/* Maximale Spieleranzahl */}
                <div>
                  <label className={labelCls}>Maximale Spieleranzahl</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={newRound.max_players}
                    onChange={e => setNewRound({ ...newRound, max_players: e.target.value })}
                    className={fieldCls}
                  />
                </div>

                {/* Zusammenfassung */}
                <div className="bg-gray-900 rounded p-4 text-sm space-y-1 border border-gray-600">
                  <p className="font-semibold text-gray-300 mb-2">Zusammenfassung der neuen Runde:</p>
                  <p>🗺️ Spielfeld: <span className="text-white font-mono">{newRound.universe_size}×{newRound.universe_size}</span></p>
                  <p>🪐 Planeten: <span className="text-white font-mono">{Number(newRound.planet_count).toLocaleString('de-DE')}</span></p>
                  <p>💎 Ressourcen/Planet: <span className="text-white font-mono">{Number(newRound.resources_per_planet).toLocaleString('de-DE')}</span></p>
                  <p>⏱️ Tick-Dauer: <span className="text-white font-mono">{newRound.tick_duration}s</span></p>
                  <p>👥 Max. Spieler: <span className="text-white font-mono">{newRound.max_players}</span></p>
                </div>

                <button
                  onClick={startNewRound}
                  disabled={loading}
                  className="w-full bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed px-6 py-3 rounded font-bold text-lg transition-colors"
                >
                  {loading ? '⏳ Wird gestartet...' : '🚀 Neue Runde starten'}
                </button>
              </div>

              {/* Ergebnis nach Start */}
              {newRoundResult && (
                <div className="bg-green-900 border border-green-500 rounded p-4 space-y-1 text-sm">
                  <p className="font-bold text-green-400 text-base">✅ {newRoundResult.message}</p>
                  <p>Spielfeld: {newRoundResult.universe_size}</p>
                  <p>Erstellte Planeten: <span className="font-mono text-white">{newRoundResult.planets_created}</span></p>
                  <p>Ressourcen pro Planet: <span className="font-mono text-white">{Number(newRoundResult.resources_per_planet).toLocaleString('de-DE')}</span></p>
                  <p>Tick-Dauer: {newRoundResult.tick_duration}</p>
                  <p>Max. Spieler: {newRoundResult.max_players}</p>
                </div>
              )}
            </div>
          )}

          {/* ── KONFIGURATION ── */}
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

          {/* ── SPIELER ── */}
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

          {/* ── EINLADUNGEN ── */}
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

          {/* ── AKTIONEN ── */}
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

export default AdminPanel;
