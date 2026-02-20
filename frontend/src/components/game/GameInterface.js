import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../hooks/use-toast';
import Observatory from './Observatory';
import ShipDesignCalculator from './ShipDesignCalculator';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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
  const [targetCoordinates, setTargetCoordinates] = useState(null);
  const [showShipCalculator, setShowShipCalculator] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [userBuildings, setUserBuildings] = useState([]);

  useEffect(() => {
    fetchGameData();
    const interval = setInterval(fetchGameData, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const clockInterval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(clockInterval);
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

  useEffect(() => {
    if (targetCoordinates && activeTab === 'raumhafen') {
      setTimeout(() => {
        userFleets.forEach(fleet => {
          if (!fleet.movement_end_time) {
            const xInput = document.getElementById(`fleet-${fleet.id}-x`);
            const yInput = document.getElementById(`fleet-${fleet.id}-y`);
            if (xInput && yInput) {
              xInput.value = targetCoordinates.x;
              yInput.value = targetCoordinates.y;
            }
          }
        });
      }, 100);
    }
  }, [targetCoordinates, activeTab, userFleets]);

  const fetchGameData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [gameStateRes, planetsRes, fleetsRes, designsRes, componentRes, rankingsRes, researchRes, costsRes, spaceportRes, buildingsRes] = await Promise.all([
        axios.get(`${API}/game/state`, { headers }),
        axios.get(`${API}/game/planets`, { headers }),
        axios.get(`${API}/game/fleets`, { headers }),
        axios.get(`${API}/game/ship-designs`, { headers }),
        axios.get(`${API}/game/component-levels`, { headers }),
        axios.get(`${API}/game/rankings`, { headers }),
        axios.get(`${API}/game/research`, { headers }),
        axios.get(`${API}/game/research/costs`, { headers }),
        axios.get(`${API}/game/spaceport-ships`, { headers }),
        axios.get(`${API}/game/buildings`, { headers })
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
      setUserBuildings(buildingsRes.data);
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
    setActiveTab('raumhafen');
    setTargetCoordinates({ x, y });
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
      await axios.post(`${API}/game/build-ships`, {
        planet_id: planetId,
        design_id: designId,
        quantity: quantity
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Erfolg", description: `${quantity} Schiffe im Raumhafen produziert!` });
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
    const now = currentTime;
    const diff = Math.max(0, Math.floor((nextTick - now) / 1000));
    const minutes = Math.floor(diff / 60);
    const seconds = diff % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatTickDuration = () => {
    if (!gameState?.tick_duration) return '0:00';
    const duration = gameState.tick_duration;
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatCurrentTime = () => {
    return currentTime.toLocaleString('de-DE');
  };

  const calculateResearchCost = (baseCost, currentLevel) => {
    const reductionFactor = Math.pow(0.85, currentLevel);
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

  const upgradeBuilding = async (buildingType) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API}/game/buildings/upgrade`, {
        building_type: buildingType
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ 
        title: "Ausbau gestartet!", 
        description: response.data.message 
      });
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: error.response?.data?.detail || 'Gebäude konnte nicht ausgebaut werden',
        variant: "destructive" 
      });
    }
  };

  const moveFleet = async (fleetId) => {
    try {
      const xInput = document.getElementById(`fleet-${fleetId}-x`);
      const yInput = document.getElementById(`fleet-${fleetId}-y`);
      
      const x = parseInt(xInput.value);
      const y = parseInt(yInput.value);
      
      if (isNaN(x) || isNaN(y) || x < 0 || x > 46 || y < 0 || y > 46) {
        toast({ title: "Fehler", description: "Bitte geben Sie gültige Koordinaten ein (0-46)", variant: "destructive" });
        return;
      }

      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/move-fleet`, {
        fleet_id: fleetId,
        target_position: { x, y }
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Erfolg", description: `Flotte bewegt sich zu (${x}:${y})!` });
      setTargetCoordinates(null);
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: error.response?.data?.detail || 'Flottenbewegung fehlgeschlagen',
        variant: "destructive" 
      });
    }
  };

  const createFleet = async (planetData) => {
    try {
      const fleetNameInput = document.getElementById(`fleet-name-${planetData.planet_id}`);
      const fleetName = fleetNameInput.value.trim();
      
      if (!fleetName) {
        toast({ title: "Fehler", description: "Bitte geben Sie einen Flottennamen ein", variant: "destructive" });
        return;
      }

      const ships = [];
      let hasSelection = false;
      
      for (const ship of planetData.ships) {
        const quantityInput = document.getElementById(`ship-${ship.id}-quantity`);
        const quantity = parseInt(quantityInput.value) || 0;
        
        if (quantity > 0) {
          ships.push({
            design_id: ship.design_id,
            quantity: quantity
          });
          hasSelection = true;
        }
      }
      
      if (!hasSelection) {
        toast({ title: "Fehler", description: "Bitte wählen Sie mindestens ein Schiff für die Flotte", variant: "destructive" });
        return;
      }

      const token = localStorage.getItem('token');
      await axios.post(`${API}/game/create-fleet`, {
        planet_id: planetData.planet_id,
        fleet_name: fleetName,
        ships: ships
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast({ title: "Erfolg", description: `Flotte "${fleetName}" erstellt!` });
      fetchGameData();
    } catch (error) {
      toast({ 
        title: "Fehler", 
        description: error.response?.data?.detail || 'Flottenerstellung fehlgeschlagen',
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
            <div>Uhrzeit: {formatCurrentTime()}</div>
            <div>nexttick: {gameState?.next_tick_time ? new Date(gameState.next_tick_time).toLocaleString('de-DE') : 'Lade...'} ({formatNextTick()})</div>
            <div>Tickdauer: {formatTickDuration()}</div>
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
                      <h5>{planetData.planet_name} ({planetData.position.x}:{planetData.position.y})</h5>
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
                                defaultValue="0"
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
                    <h5>{fleet.name}{fleet.movement_end_time ? '*' : ''}</h5>
                    <div className="fleet-position">
                      Position: ({fleet.position.x}:{fleet.position.y})
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
                    
                    {/* Fleet Movement Controls */}
                    {!fleet.movement_end_time && (
                      <div className="fleet-movement">
                        <h6>Flotte bewegen:</h6>
                        <div className="movement-controls">
                          <input
                            type="number"
                            placeholder="X"
                            min="0"
                            max="46"
                            id={`fleet-${fleet.id}-x`}
                            className="coordinate-input"
                            key={`${fleet.id}-x-${targetCoordinates?.x || 'empty'}`}
                            defaultValue={targetCoordinates?.x || ''}
                          />
                          <span>:</span>
                          <input
                            type="number"
                            placeholder="Y"
                            min="0"
                            max="46"
                            id={`fleet-${fleet.id}-y`}
                            className="coordinate-input"
                            key={`${fleet.id}-y-${targetCoordinates?.y || 'empty'}`}
                            defaultValue={targetCoordinates?.y || ''}
                          />
                          <button
                            onClick={() => moveFleet(fleet.id)}
                            className="btn-primary move-fleet-btn"
                          >
                            Bewegen
                          </button>
                        </div>
                      </div>
                    )}
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
              userFleets={userFleets}
              userPlanets={userPlanets}
              onNavigateToSpaceport={() => setActiveTab('raumhafen')}
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
                                  {planet.name} ({planet.position.x}:{planet.position.y})
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
              <h3>🏗️ Gebäude & Einrichtungen</h3>
              
              {/* Total Metal Display */}
              <div className="total-resources-display">
                <span>Verfügbares Metall: </span>
                <span className="resource-metal">
                  ⚙️ {userPlanets.reduce((sum, p) => sum + p.resources.metal, 0).toLocaleString()}
                </span>
              </div>
              
              {/* Resource Buildings */}
              <div className="buildings-section">
                <h4>📦 Ressourcen-Gebäude</h4>
                <div className="buildings-grid">
                  {userBuildings.filter(b => b.category === 'resource').map(building => {
                    const totalMetal = userPlanets.reduce((sum, p) => sum + p.resources.metal, 0);
                    const canAfford = totalMetal >= building.upgrade_cost_metal;
                    const anyUpgrading = userBuildings.some(b => b.upgrading);
                    
                    return (
                      <div key={building.building_type} className="building-card">
                        <div className="building-header">
                          <span className="building-name">
                            {building.building_type === 'plantage' && '🌾'}
                            {building.building_type === 'erzmine' && '⚙️'}
                            {building.building_type === 'elektrolysator' && '⚡'}
                            {' '}{building.name}
                          </span>
                          <span className="building-level">Level {building.level}</span>
                        </div>
                        <div className="building-description">{building.description}</div>
                        
                        <div className="building-bonus">
                          {building.current_bonus.resource_per_tick > 0 ? (
                            <span className="bonus-active">
                              +{building.current_bonus.resource_per_tick} {building.current_bonus.resource_type === 'food' ? 'Nahrung' : building.current_bonus.resource_type === 'metal' ? 'Metall' : 'Wasserstoff'}/Tick
                            </span>
                          ) : (
                            <span className="bonus-inactive">Kein Bonus (Level 0)</span>
                          )}
                        </div>
                        
                        <div className="building-upgrade">
                          <div className="upgrade-cost">
                            Kosten: <span className={canAfford ? 'resource-metal' : 'resource-insufficient'}>
                              ⚙️ {building.upgrade_cost_metal.toLocaleString()} Metall
                            </span>
                          </div>
                          <div className="upgrade-time">
                            Bauzeit: {building.upgrade_time_ticks} Ticks
                          </div>
                          
                          {building.upgrading ? (
                            <div className="upgrading-indicator">
                              🔨 Ausbau läuft...
                              <div className="upgrade-completion">
                                Fertig: {new Date(building.upgrade_end_time).toLocaleString('de-DE')}
                              </div>
                            </div>
                          ) : (
                            <button
                              onClick={() => upgradeBuilding(building.building_type)}
                              disabled={!canAfford || anyUpgrading}
                              className="btn-primary upgrade-btn"
                            >
                              Ausbauen → Level {building.level + 1}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              
              {/* Special Buildings */}
              <div className="buildings-section">
                <h4>🏛️ Spezial-Gebäude</h4>
                <div className="buildings-grid">
                  {userBuildings.filter(b => b.category === 'special').map(building => {
                    const totalMetal = userPlanets.reduce((sum, p) => sum + p.resources.metal, 0);
                    const canAfford = totalMetal >= building.upgrade_cost_metal;
                    const anyUpgrading = userBuildings.some(b => b.upgrading);
                    
                    return (
                      <div key={building.building_type} className={`building-card building-special building-${building.building_type}`}>
                        <div className="building-header">
                          <span className="building-name">
                            {building.building_type === 'werft' && '🔧'}
                            {building.building_type === 'raumhafen' && '🚀'}
                            {building.building_type === 'forschungslabor' && '🔬'}
                            {' '}{building.name}
                          </span>
                          <span className="building-level">Level {building.level}</span>
                        </div>
                        <div className="building-description">{building.description}</div>
                        
                        <div className="building-bonus">
                          {building.building_type === 'werft' && (
                            <span className="bonus-active">
                              Max. Prototypen: {building.current_bonus.prototype_slots || 0}
                            </span>
                          )}
                          {building.building_type === 'raumhafen' && (
                            <span className="bonus-active">
                              Max. Flotten: {building.current_bonus.fleet_slots || 0}
                            </span>
                          )}
                          {building.building_type === 'forschungslabor' && (
                            <span className="bonus-active">
                              Forschungszeit: -{building.current_bonus.research_time_reduction || 0}%
                            </span>
                          )}
                        </div>
                        
                        <div className="building-upgrade">
                          <div className="upgrade-cost">
                            Kosten: <span className={canAfford ? 'resource-metal' : 'resource-insufficient'}>
                              ⚙️ {building.upgrade_cost_metal.toLocaleString()} Metall
                            </span>
                          </div>
                          <div className="upgrade-time">
                            Bauzeit: {building.upgrade_time_ticks} Ticks
                          </div>
                          
                          {building.upgrading ? (
                            <div className="upgrading-indicator">
                              🔨 Ausbau läuft...
                              <div className="upgrade-completion">
                                Fertig: {new Date(building.upgrade_end_time).toLocaleString('de-DE')}
                              </div>
                            </div>
                          ) : (
                            <button
                              onClick={() => upgradeBuilding(building.building_type)}
                              disabled={!canAfford || anyUpgrading}
                              className="btn-primary upgrade-btn"
                            >
                              Ausbauen → Level {building.level + 1}
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              
              {/* Planets Overview */}
              <div className="planets-section">
                <h4>🌍 Ihre Planeten</h4>
                <div className="planets-list">
                  {userPlanets.map(planet => (
                    <div key={planet.id} className={`planet-card planet-${planet.planet_type}`}>
                      <h5>{planet.name}</h5>
                      <div className="planet-position">({planet.position.x}:{planet.position.y})</div>
                      <div className="planet-resources">
                        <span>🌾 {planet.resources.food.toLocaleString()}</span>
                        <span>⚙️ {planet.resources.metal.toLocaleString()}</span>
                        <span>⚡ {planet.resources.hydrogen.toLocaleString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
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
            <h4>Feld ({selectedField.x}:{selectedField.y})</h4>
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
          userResearch={userResearch}
        />
      )}
    </div>
  );
};

export default GameInterface;
