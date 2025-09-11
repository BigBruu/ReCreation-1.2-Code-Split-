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
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (token) {
      fetchUser();
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
      const response = await axios.post(`${API}/login`, { username, password });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      return true;
    } catch (error) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const register = async (username, email, password) => {
    setLoading(true);
    try {
      const response = await axios.post(`${API}/register`, { username, email, password });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
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
  };

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Login Component
const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ username: '', email: '', password: '' });
  const { login, register, loading } = useAuth();
  const { toast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isLogin) {
        await login(formData.username, formData.password);
      } else {
        await register(formData.username, formData.email, formData.password);
      }
      toast({ title: "Erfolg!", description: `${isLogin ? 'Angemeldet' : 'Registriert'} - Raumhafen wird zugewiesen...` });
      // Auto-redirect to game
      setTimeout(() => {
        window.location.href = '/game';
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
          <p className="text-xs text-gray-500 mt-2">47x47 Universum • Max 20 Spieler • Runde 10</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
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

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 py-2 rounded font-medium transition-colors"
          >
            {loading ? 'Lade...' : (isLogin ? 'Anmelden' : 'Registrieren')}
          </button>
        </form>

        <div className="text-center mt-4">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            {isLogin ? 'Kein Account? Registrieren' : 'Bereits Account? Anmelden'}
          </button>
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
    weapon_quantity: 10
  });

  const [calculatedStats, setCalculatedStats] = useState({
    speed: 0,
    combat_value: 0,
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
    const totalWeight = driveWeight + shieldWeight + weaponWeight;

    // Calculate speed
    const baseSpeed = driveData.speed_base * design.drive_level * design.drive_quantity;
    const speed = Math.max(1, Math.floor(baseSpeed / Math.max(1, totalWeight / 100)));

    // Calculate combat value
    const attackPower = weaponData.attack_base * design.weapon_level * design.weapon_quantity;
    const defensePower = shieldData.defense_base * design.shield_level * design.shield_quantity;
    const combatValue = attackPower + defensePower;

    // Calculate build costs
    const metalCost = (driveWeight + weaponWeight) * design.drive_level * 10;
    const siliconCost = (shieldWeight + weaponWeight) * design.shield_level * 5;
    const hydrogenCost = weaponWeight * design.weapon_level * 2;

    // Calculate build time
    const buildTime = Math.max(1, Math.floor(totalWeight / 100)) + design.drive_level + design.shield_level + design.weapon_level;

    setCalculatedStats({
      speed,
      combat_value: combatValue,
      total_weight: totalWeight,
      build_cost: {
        food: 0,
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
                placeholder="z.B. Kampfschiff Mk1"
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
          </div>

          <div className="calculated-stats">
            <h4>Berechnete Werte:</h4>
            <table>
              <tbody>
                <tr><td>Beschleunigung:</td><td>{calculatedStats.speed}</td></tr>
                <tr><td>Kampfwert:</td><td>{calculatedStats.combat_value}</td></tr>
                <tr><td>Geschwindigkeit:</td><td>{calculatedStats.speed} pc/tick</td></tr>
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

// Main Game Interface
const GameInterface = () => {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const [gameState, setGameState] = useState(null);
  const [observatoryView, setObservatoryView] = useState({});
  const [centerPosition, setCenterPosition] = useState({ x: 23, y: 23 });
  const [userPlanets, setUserPlanets] = useState([]);
  const [userFleets, setUserFleets] = useState([]);
  const [shipDesigns, setShipDesigns] = useState([]);
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

      const [gameStateRes, planetsRes, fleetsRes, designsRes, componentRes, rankingsRes] = await Promise.all([
        axios.get(`${API}/game/state`, { headers }),
        axios.get(`${API}/game/planets`, { headers }),
        axios.get(`${API}/game/fleets`, { headers }),
        axios.get(`${API}/game/ship-designs`, { headers }),
        axios.get(`${API}/game/component-levels`, { headers }),
        axios.get(`${API}/game/rankings`, { headers })
      ]);

      setGameState(gameStateRes.data);
      setUserPlanets(planetsRes.data);
      setUserFleets(fleetsRes.data);
      setShipDesigns(designsRes.data);
      setComponentLevels(componentRes.data);
      setRankings(rankingsRes.data);
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
                      <div className="stats-row">
                        <span>Geschwindigkeit: {design.calculated_stats.speed} pc/tick</span>
                        <span>Kampfwert: {design.calculated_stats.combat_value}</span>
                        <span>Bauzeit: {design.calculated_stats.build_time_ticks} Ticks</span>
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

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { token } = useAuth();
  
  if (!token) {
    return <Navigate to="/login" replace />;
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
              path="/game" 
              element={
                <ProtectedRoute>
                  <GameInterface />
                </ProtectedRoute>
              } 
            />
            <Route path="/" element={<Navigate to="/game" replace />} />
          </Routes>
          <Toaster />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;