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
      toast({ title: "Success!", description: `${isLogin ? 'Logged in' : 'Registered'} successfully` });
    } catch (error) {
      toast({ title: "Error", description: error.message, variant: "destructive" });
    }
  };

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
      <div className="bg-gray-900 p-8 rounded-lg border border-gray-700 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-blue-400 mb-2">TheReCreation</h1>
          <p className="text-gray-400">Browser Strategy Game</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Username</label>
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
              <label className="block text-sm font-medium mb-1">Email</label>
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
            <label className="block text-sm font-medium mb-1">Password</label>
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
            {loading ? 'Processing...' : (isLogin ? 'Login' : 'Register')}
          </button>
        </form>

        <div className="text-center mt-4">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            {isLogin ? 'Need an account? Register' : 'Have an account? Login'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Game Field Component
const GameField = ({ field, onFieldClick, selectedPosition }) => {
  const renderField = (x, y) => {
    const key = `${x},${y}`;
    const fieldData = field[key] || { colonies: [], ships: [] };
    const hasColony = fieldData.colonies.length > 0;
    const hasShips = fieldData.ships.length > 0;
    const isSelected = selectedPosition && selectedPosition.x === x && selectedPosition.y === y;

    let bgColor = 'bg-gray-900';
    if (hasColony) bgColor = 'bg-green-800';
    if (hasShips && !hasColony) bgColor = 'bg-blue-800';
    if (hasColony && hasShips) bgColor = 'bg-yellow-800';
    if (isSelected) bgColor += ' ring-2 ring-white';

    return (
      <div
        key={key}
        className={`w-3 h-3 border border-gray-700 cursor-pointer hover:bg-gray-700 ${bgColor}`}
        onClick={() => onFieldClick(x, y, fieldData)}
        title={`(${x},${y}) ${hasColony ? 'Colony' : ''} ${hasShips ? 'Ships' : ''}`}
      />
    );
  };

  return (
    <div className="grid grid-cols-47 gap-0 border border-gray-600 bg-black p-2">
      {Array.from({ length: 47 }, (_, y) =>
        Array.from({ length: 47 }, (_, x) => renderField(x, y))
      )}
    </div>
  );
};

// Game Interface Component
const GameInterface = () => {
  const { user, logout } = useAuth();
  const { toast } = useToast();
  const [gameState, setGameState] = useState(null);
  const [field, setField] = useState({});
  const [colonies, setColonies] = useState([]);
  const [ships, setShips] = useState([]);
  const [rankings, setRankings] = useState([]);
  const [selectedPosition, setSelectedPosition] = useState(null);
  const [selectedFieldData, setSelectedFieldData] = useState(null);
  const [showCreateColony, setShowCreateColony] = useState(false);
  const [showCreateShip, setShowCreateShip] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    fetchGameData();
    const interval = setInterval(fetchGameData, 10000); // Update every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchGameData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [gameStateRes, fieldRes, coloniesRes, shipsRes, rankingsRes] = await Promise.all([
        axios.get(`${API}/game/state`, { headers }),
        axios.get(`${API}/game/field`, { headers }),
        axios.get(`${API}/game/colonies`, { headers }),
        axios.get(`${API}/game/ships`, { headers }),
        axios.get(`${API}/game/rankings`, { headers })
      ]);

      setGameState(gameStateRes.data);
      setField(fieldRes.data.field);
      setColonies(coloniesRes.data);
      setShips(shipsRes.data);
      setRankings(rankingsRes.data);
    } catch (error) {
      console.error('Failed to fetch game data:', error);
    }
  };

  const handleFieldClick = (x, y, fieldData) => {
    setSelectedPosition({ x, y });
    setSelectedFieldData(fieldData);
  };

  const createColony = async (name) => {
    if (!selectedPosition) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/colony`, {
        position: selectedPosition,
        name
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Success", description: "Colony created!" });
      setShowCreateColony(false);
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Error", 
        description: error.response?.data?.detail || 'Failed to create colony',
        variant: "destructive" 
      });
    }
  };

  const createShip = async (colonyId, shipType, name) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/ship`, {
        colony_id: colonyId,
        ship_type: shipType,
        name
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Success", description: "Ship created!" });
      setShowCreateShip(false);
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Error", 
        description: error.response?.data?.detail || 'Failed to create ship',
        variant: "destructive" 
      });
    }
  };

  const moveShip = async (shipId, targetPosition) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/move`, {
        ship_id: shipId,
        target_position: targetPosition
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Success", description: "Ship moved!" });
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Error", 
        description: error.response?.data?.detail || 'Failed to move ship',
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
      
      toast({ title: "Success", description: "Tick processed!" });
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Error", 
        description: error.response?.data?.detail || 'Failed to process tick',
        variant: "destructive" 
      });
    }
  };

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-700 p-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-blue-400">TheReCreation</h1>
            <p className="text-sm text-gray-400">
              Tick: {gameState?.current_tick || 0} | Players: {rankings.length}/20
            </p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm">Welcome, {user?.username}</span>
            <button 
              onClick={processTick}
              className="bg-green-600 hover:bg-green-700 px-3 py-1 rounded text-sm"
            >
              Process Tick
            </button>
            <button 
              onClick={logout}
              className="bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-sm"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <div className="w-80 bg-gray-900 border-r border-gray-700 p-4 h-screen overflow-y-auto">
          {/* Navigation */}
          <div className="flex space-x-2 mb-4">
            {['overview', 'colonies', 'ships', 'rankings'].map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1 rounded text-sm capitalize ${
                  activeTab === tab ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Content based on active tab */}
          {activeTab === 'overview' && (
            <div className="space-y-4">
              <div className="bg-gray-800 p-3 rounded">
                <h3 className="font-semibold mb-2">Player Stats</h3>
                <div className="space-y-1 text-sm">
                  <div>Points: {user?.points || 0}</div>
                  <div>Colonies: {colonies.length}</div>
                  <div>Ships: {ships.length}</div>
                </div>
              </div>

              {selectedFieldData && (
                <div className="bg-gray-800 p-3 rounded">
                  <h3 className="font-semibold mb-2">
                    Selected: ({selectedPosition.x}, {selectedPosition.y})
                  </h3>
                  
                  {selectedFieldData.colonies.map(colony => (
                    <div key={colony.id} className="mb-2 p-2 bg-green-900 rounded">
                      <div className="font-medium">{colony.name}</div>
                      <div className="text-xs text-gray-300">by {colony.username}</div>
                      <div className="text-xs">
                        F:{colony.resources.food} M:{colony.resources.metal} 
                        S:{colony.resources.silicon} H:{colony.resources.hydrogen}
                      </div>
                    </div>
                  ))}

                  {selectedFieldData.ships.map(ship => (
                    <div key={ship.id} className="mb-2 p-2 bg-blue-900 rounded">
                      <div className="font-medium">{ship.name} ({ship.ship_type})</div>
                      <div className="text-xs text-gray-300">by {ship.username}</div>
                      <div className="text-xs">
                        HP:{ship.health} ATK:{ship.attack} DEF:{ship.defense}
                      </div>
                    </div>
                  ))}

                  {selectedFieldData.colonies.length === 0 && selectedFieldData.ships.length === 0 && (
                    <div>
                      <button
                        onClick={() => setShowCreateColony(true)}
                        className="w-full bg-green-600 hover:bg-green-700 py-2 rounded text-sm mb-2"
                      >
                        Create Colony
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {activeTab === 'colonies' && (
            <div className="space-y-2">
              <h3 className="font-semibold">My Colonies ({colonies.length})</h3>
              {colonies.map(colony => (
                <div key={colony.id} className="bg-gray-800 p-3 rounded">
                  <div className="font-medium">{colony.name}</div>
                  <div className="text-xs text-gray-400">
                    Position: ({colony.position.x}, {colony.position.y})
                  </div>
                  <div className="text-xs mt-1">
                    <div>Food: {colony.resources.food}</div>
                    <div>Metal: {colony.resources.metal}</div>
                    <div>Silicon: {colony.resources.silicon}</div>
                    <div>Hydrogen: {colony.resources.hydrogen}</div>
                  </div>
                  <button
                    onClick={() => setShowCreateShip(colony.id)}
                    className="w-full bg-blue-600 hover:bg-blue-700 py-1 rounded text-xs mt-2"
                  >
                    Build Ship
                  </button>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'ships' && (
            <div className="space-y-2">
              <h3 className="font-semibold">My Ships ({ships.length})</h3>
              {ships.map(ship => (
                <div key={ship.id} className="bg-gray-800 p-3 rounded">
                  <div className="font-medium">{ship.name}</div>
                  <div className="text-xs text-gray-400">
                    {ship.ship_type} at ({ship.position.x}, {ship.position.y})
                  </div>
                  <div className="text-xs mt-1">
                    HP:{ship.health} ATK:{ship.attack} DEF:{ship.defense} SPD:{ship.speed}
                  </div>
                  {selectedPosition && (
                    <button
                      onClick={() => moveShip(ship.id, selectedPosition)}
                      className="w-full bg-orange-600 hover:bg-orange-700 py-1 rounded text-xs mt-2"
                      disabled={!selectedPosition}
                    >
                      Move Here
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === 'rankings' && (
            <div className="space-y-1">
              <h3 className="font-semibold">Rankings</h3>
              {rankings.map(player => (
                <div key={player.rank} className="bg-gray-800 p-2 rounded flex justify-between text-sm">
                  <span>#{player.rank} {player.username}</span>
                  <span>{player.points} pts</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Game Field */}
        <div className="flex-1 p-4">
          <div className="bg-gray-900 p-4 rounded">
            <h3 className="font-semibold mb-4">Game Field (47x47)</h3>
            <div className="overflow-auto max-h-[600px]">
              <GameField 
                field={field}
                onFieldClick={handleFieldClick}
                selectedPosition={selectedPosition}
              />
            </div>
            <div className="mt-4 text-xs text-gray-400">
              <div>🟢 Colony  🔵 Ships  🟡 Colony + Ships</div>
              <div>Click any field to select it. Selected: {selectedPosition ? `(${selectedPosition.x}, ${selectedPosition.y})` : 'None'}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Create Colony Modal */}
      {showCreateColony && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-900 p-6 rounded border border-gray-700">
            <h3 className="font-semibold mb-4">Create Colony</h3>
            <p className="text-sm text-gray-400 mb-4">
              Position: ({selectedPosition?.x}, {selectedPosition?.y})
            </p>
            <input
              type="text"
              placeholder="Colony name"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded mb-4"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && e.target.value.trim()) {
                  createColony(e.target.value.trim());
                }
              }}
              autoFocus
            />
            <div className="flex space-x-2">
              <button
                onClick={() => setShowCreateColony(false)}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Ship Modal */}
      {showCreateShip && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-gray-900 p-6 rounded border border-gray-700">
            <h3 className="font-semibold mb-4">Build Ship</h3>
            <div className="space-y-3">
              {['scout', 'fighter', 'colonizer'].map(type => (
                <button
                  key={type}
                  onClick={() => {
                    const name = prompt(`Name for your ${type}:`);
                    if (name) createShip(showCreateShip, type, name);
                  }}
                  className="w-full p-3 bg-gray-800 hover:bg-gray-700 rounded text-left"
                >
                  <div className="font-medium capitalize">{type}</div>
                  <div className="text-xs text-gray-400">
                    {type === 'scout' && 'Fast, weak reconnaissance ship'}
                    {type === 'fighter' && 'Balanced combat ship'}
                    {type === 'colonizer' && 'Can establish new colonies'}
                  </div>
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowCreateShip(false)}
              className="w-full mt-4 px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
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

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
};

export default App;