import React, { useState, useEffect } from 'react';
import { useToast } from '../../hooks/use-toast';

const ShipDesignCalculator = ({ onClose, onSave, componentLevels, userResearch }) => {
  const { toast } = useToast();
  
  const getMaxResearchedLevel = (category, technology) => {
    if (!userResearch?.research_levels) return 0;
    const tech = userResearch.research_levels.find(
      t => t.category === category && t.technology === technology
    );
    return tech ? tech.level : 0;
  };

  const getFirstResearchedComponent = (category) => {
    if (!userResearch?.research_levels) return null;
    const techs = userResearch.research_levels.filter(
      t => t.category === category && t.level > 0
    );
    if (techs.length === 0) return null;
    const bestTech = techs.reduce((best, current) => 
      current.level > best.level ? current : best
    );
    return { type: bestTech.technology, level: bestTech.level };
  };

  const hasAnyResearch = () => {
    if (!userResearch?.research_levels) return false;
    return userResearch.research_levels.some(t => t.level > 0);
  };

  const initialDrive = getFirstResearchedComponent('drives');
  const initialShield = getFirstResearchedComponent('shields');
  const initialWeapon = getFirstResearchedComponent('weapons');

  const [design, setDesign] = useState({
    name: '',
    drive_type: initialDrive?.type || 'impuls',
    drive_level: initialDrive?.level || 1,
    drive_quantity: 1,
    shield_type: initialShield?.type || 'standard',
    shield_level: initialShield?.level || 1,
    shield_quantity: 1,
    weapon_type: initialWeapon?.type || 'laser',
    weapon_level: initialWeapon?.level || 1,
    weapon_quantity: 1
  });

  useEffect(() => {
    const newDriveLevel = getMaxResearchedLevel('drives', design.drive_type);
    const newShieldLevel = getMaxResearchedLevel('shields', design.shield_type);
    const newWeaponLevel = getMaxResearchedLevel('weapons', design.weapon_type);
    
    setDesign(prev => ({
      ...prev,
      drive_level: Math.max(1, newDriveLevel),
      shield_level: Math.max(1, newShieldLevel),
      weapon_level: Math.max(1, newWeaponLevel)
    }));
  }, [design.drive_type, design.shield_type, design.weapon_type, userResearch]);

  const getComponentStats = (category, type, level) => {
    const categoryData = componentLevels?.[category];
    if (!categoryData) return null;
    const typeData = categoryData[type];
    if (!typeData) return null;
    return typeData[level] || typeData[1];
  };

  const calculateStats = () => {
    const driveStats = getComponentStats('drives', design.drive_type, design.drive_level);
    const shieldStats = getComponentStats('shields', design.shield_type, design.shield_level);
    const weaponStats = getComponentStats('weapons', design.weapon_type, design.weapon_level);

    if (!driveStats || !shieldStats || !weaponStats) {
      return {
        speed: 0,
        combat_value: 0,
        mining_capacity: 0,
        total_weight: 0,
        build_time_ticks: 0,
        build_cost: { food: 0, metal: 0, hydrogen: 0 }
      };
    }

    const totalDriveSpeed = driveStats.speed * design.drive_quantity;
    const totalShieldDefense = shieldStats.defense * design.shield_quantity;
    const totalWeaponAttack = weaponStats.attack * design.weapon_quantity;
    const miningCapacity = design.weapon_type === 'abbaueinheit' ? 
      (weaponStats.mining_bonus || 0) * design.weapon_quantity : 0;

    const totalWeight = 
      driveStats.weight * design.drive_quantity +
      shieldStats.weight * design.shield_quantity +
      weaponStats.weight * design.weapon_quantity;

    const buildCost = {
      food: (driveStats.cost.food * design.drive_quantity) +
            (shieldStats.cost.food * design.shield_quantity) +
            (weaponStats.cost.food * design.weapon_quantity),
      metal: (driveStats.cost.metal * design.drive_quantity) +
             (shieldStats.cost.metal * design.shield_quantity) +
             (weaponStats.cost.metal * design.weapon_quantity),
      hydrogen: (driveStats.cost.hydrogen * design.drive_quantity) +
                (shieldStats.cost.hydrogen * design.shield_quantity) +
                (weaponStats.cost.hydrogen * design.weapon_quantity)
    };

    const buildTimeTicks = Math.ceil(totalWeight / 10);

    return {
      speed: Math.max(1, Math.floor(totalDriveSpeed / Math.max(1, totalWeight / 100))),
      combat_value: totalWeaponAttack + Math.floor(totalShieldDefense / 2),
      mining_capacity: miningCapacity,
      total_weight: totalWeight,
      build_time_ticks: buildTimeTicks,
      build_cost: buildCost
    };
  };

  const calculatedStats = calculateStats();

  const handleSave = () => {
    if (!design.name.trim()) {
      toast({ title: "Fehler", description: "Bitte geben Sie einen Namen ein", variant: "destructive" });
      return;
    }
    
    if (!hasAnyResearch()) {
      toast({ title: "Fehler", description: "Keine Technologien erforscht!", variant: "destructive" });
      return;
    }
    
    onSave({
      name: design.name,
      drive: { type: design.drive_type, level: design.drive_level, quantity: design.drive_quantity },
      shield: { type: design.shield_type, level: design.shield_level, quantity: design.shield_quantity },
      weapon: { type: design.weapon_type, level: design.weapon_level, quantity: design.weapon_quantity }
    });
  };

  if (!hasAnyResearch()) {
    return (
      <div className="modal-backdrop">
        <div className="ship-calculator">
          <div className="calculator-header">
            <h3>Werft - Raumschiff-Rechner</h3>
            <button onClick={onClose} className="close-btn">×</button>
          </div>
          <div className="no-research-warning">
            <h4>⚠️ Keine Technologien erforscht!</h4>
            <p>Um Raumschiffe zu entwerfen, müssen Sie zuerst Technologien erforschen.</p>
            <p>Gehen Sie zum Tab "Technologie" und erforschen Sie:</p>
            <ul>
              <li>• Mindestens einen Antrieb (z.B. Impuls)</li>
              <li>• Mindestens ein Schild (z.B. Standard)</li>
              <li>• Mindestens eine Waffe (z.B. Laser oder Abbaueinheit)</li>
            </ul>
          </div>
          <div className="calculator-actions">
            <button onClick={onClose} className="btn-secondary">Schließen</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop">
      <div className="ship-calculator">
        <div className="calculator-header">
          <h3>Werft - Raumschiff-Rechner</h3>
          <button onClick={onClose} className="close-btn">×</button>
        </div>

        <div className="calculator-content">
          <div className="design-inputs">
            <div className="input-group">
              <label>Prototyp-Name:</label>
              <input
                type="text"
                value={design.name}
                onChange={(e) => setDesign({...design, name: e.target.value})}
                placeholder="z.B. Jäger Mk1"
              />
            </div>

            {/* Drive Component */}
            <div className="component-section">
              <h4>🚀 Antrieb</h4>
              <div className="component-row">
                <div className="component-input-group">
                  <label>Typ:</label>
                  <select 
                    value={design.drive_type}
                    onChange={(e) => setDesign({...design, drive_type: e.target.value})}
                  >
                    {['impuls', 'warp', 'hyperraum'].map(type => {
                      const maxLevel = getMaxResearchedLevel('drives', type);
                      if (maxLevel === 0) return null;
                      return (
                        <option key={type} value={type}>
                          {type.charAt(0).toUpperCase() + type.slice(1)} (Max L{maxLevel})
                        </option>
                      );
                    }).filter(Boolean)}
                  </select>
                </div>
                <div className="component-input-group">
                  <label>Level (automatisch):</label>
                  <div className="level-display">L{design.drive_level}</div>
                </div>
                <div className="component-input-group">
                  <label>Anzahl:</label>
                  <input 
                    type="number" 
                    min="1" 
                    value={design.drive_quantity}
                    onChange={(e) => setDesign({...design, drive_quantity: parseInt(e.target.value)})} 
                  />
                </div>
              </div>
            </div>

            {/* Shield Component */}
            <div className="component-section">
              <h4>🛡️ Schild</h4>
              <div className="component-row">
                <div className="component-input-group">
                  <label>Typ:</label>
                  <select 
                    value={design.shield_type}
                    onChange={(e) => setDesign({...design, shield_type: e.target.value})}
                  >
                    {['standard', 'deflektor', 'phasen'].map(type => {
                      const maxLevel = getMaxResearchedLevel('shields', type);
                      if (maxLevel === 0) return null;
                      return (
                        <option key={type} value={type}>
                          {type.charAt(0).toUpperCase() + type.slice(1)} (Max L{maxLevel})
                        </option>
                      );
                    }).filter(Boolean)}
                  </select>
                </div>
                <div className="component-input-group">
                  <label>Level (automatisch):</label>
                  <div className="level-display">L{design.shield_level}</div>
                </div>
                <div className="component-input-group">
                  <label>Anzahl:</label>
                  <input 
                    type="number" 
                    min="1" 
                    value={design.shield_quantity}
                    onChange={(e) => setDesign({...design, shield_quantity: parseInt(e.target.value)})} 
                  />
                </div>
              </div>
            </div>

            {/* Weapon Component */}
            <div className="component-section">
              <h4>⚔️ Waffe</h4>
              <div className="component-row">
                <div className="component-input-group">
                  <label>Typ:</label>
                  <select 
                    value={design.weapon_type}
                    onChange={(e) => setDesign({...design, weapon_type: e.target.value})}
                  >
                    {['laser', 'rakete', 'ion', 'abbaueinheit'].map(type => {
                      const maxLevel = getMaxResearchedLevel('weapons', type);
                      if (maxLevel === 0) return null;
                      return (
                        <option key={type} value={type}>
                          {type.charAt(0).toUpperCase() + type.slice(1)} (Max L{maxLevel})
                        </option>
                      );
                    }).filter(Boolean)}
                  </select>
                </div>
                <div className="component-input-group">
                  <label>Level (automatisch):</label>
                  <div className="level-display">L{design.weapon_level}</div>
                </div>
                <div className="component-input-group">
                  <label>Anzahl:</label>
                  <input 
                    type="number" 
                    min="1" 
                    value={design.weapon_quantity}
                    onChange={(e) => setDesign({...design, weapon_quantity: parseInt(e.target.value)})} 
                  />
                </div>
              </div>
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

export default ShipDesignCalculator;
