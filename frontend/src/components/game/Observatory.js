import React from 'react';

const Observatory = ({ centerPosition, onPositionChange, view, onFieldClick, userFleets = [], userPlanets = [], onNavigateToSpaceport }) => {
  const renderField = (x, y) => {
    const key = `${x},${y}`;
    const fieldData = view[key] || { planet: null, fleets: [] };
    const { planet, fleets } = fieldData;

    let planetIcon = null;
    if (planet) {
      const planetClass = `planet-${planet.planet_type}`;
      const isOwned = planet.owner_username;
      
      const dominantResource = Math.max(
        planet.resources.food,
        planet.resources.metal, 
        planet.resources.hydrogen
      );
      
      planetIcon = (
        <div className={`planet ${planetClass} ${isOwned ? 'owned' : ''}`}>
          <div className="planet-name">{planet.name}</div>
          {isOwned && <div className="planet-owner">{planet.owner_username}</div>}
          <div className="planet-stats">
            <div className="planet-resources">{dominantResource.toLocaleString()}</div>
          </div>
        </div>
      );
    }

    const hasFleets = fleets.length > 0;
    const centerX = Math.floor(centerPosition.x);
    const centerY = Math.floor(centerPosition.y);
    const isCenter = x === centerX && y === centerY;

    return (
      <div
        key={key}
        className={`observatory-field ${planet ? 'has-planet' : 'empty'} ${hasFleets ? 'has-fleets' : ''} ${isCenter ? 'center-field' : ''}`}
        onClick={() => onFieldClick(x, y, fieldData)}
        title={`(${x}:${y}) ${planet ? planet.name : 'Leerer Raum'} ${hasFleets ? `- ${fleets.length} Flotte(n)` : ''} ${isCenter ? ' [ZENTRUM]' : ''}`}
      >
        <div className="field-coordinates">{x}:{y}</div>
        {planetIcon}
        {hasFleets && (
          <div className="fleet-indicator">
            {fleets.map((fleet, i) => (
              <div key={i} className="fleet-icon" title={`${fleet.name}${fleet.movement_end_time ? ' (bewegend)' : ''}`}>
                {fleet.name}{fleet.movement_end_time ? '*' : ''}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="observatory-container">
      <div className="observatory-header">
        <h3>Observatorium</h3>
        <div className="observatory-controls">
          <div className="fleet-selector">
            <label>Zu Flotte springen:</label>
            <select 
              onChange={(e) => {
                if (e.target.value) {
                  const fleet = userFleets.find(f => f.id === e.target.value);
                  if (fleet) {
                    onPositionChange({ x: fleet.position.x, y: fleet.position.y });
                  }
                }
              }}
              value=""
              className="fleet-select"
            >
              <option value="">Flotte wählen...</option>
              {userFleets.map(fleet => (
                <option key={fleet.id} value={fleet.id}>
                  {fleet.name} ({fleet.position.x}:{fleet.position.y}){fleet.movement_end_time ? '*' : ''}
                </option>
              ))}
            </select>
            <button 
              onClick={() => {
                if (userPlanets.length > 0) {
                  const spaceport = userPlanets[0];
                  onPositionChange({ x: spaceport.position.x, y: spaceport.position.y });
                  if (onNavigateToSpaceport) {
                    onNavigateToSpaceport();
                  }
                }
              }}
              className="btn-secondary spaceport-btn"
            >
              🚀 Raumhafen
            </button>
          </div>
          <div className="current-coordinates">
            ({centerPosition.x}:{centerPosition.y})
          </div>
        </div>
      </div>
      
      <div className="observatory-grid">
        {/* Column headers (X-axis) */}
        <div className="observatory-row">
          <div className="axis-label"></div>
          {Array.from({ length: 7 }, (_, col) => {
            const x = centerPosition.x - 3 + col;
            return <div key={col} className="col-label">{x}</div>;
          })}
        </div>
        
        {/* Grid with Y-axis labels */}
        {Array.from({ length: 7 }, (_, row) => {
          const y = centerPosition.y - 3 + row;
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
          <span>Nahrung</span>
        </div>
        <div className="legend-item">
          <div className="planet planet-blue"></div>
          <span>Wasserstoff</span>
        </div>
        <div className="legend-item">
          <div className="planet planet-brown"></div>
          <span>Metall</span>
        </div>
        <div className="legend-item">
          <div className="planet planet-orange"></div>
          <span>Wasserstoff</span>
        </div>
      </div>
    </div>
  );
};

export default Observatory;
