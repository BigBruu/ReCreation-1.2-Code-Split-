from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
import os
import uuid
import asyncio
import logging
import math
import random
import secrets
import string
import time

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security – key comes from environment, never hardcoded
SECRET_KEY = os.environ.get('SECRET_KEY', 'fallback-change-me-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="TheCreation Authentic", version="2.0.0")
api_router = APIRouter(prefix="/api")

# Authentic Game Constants
UNIVERSE_SIZE = 47
OBSERVATORY_VIEW_SIZE = 7  # 7x7 view centered on spaceport
MAX_PLAYERS = 20
TICK_DURATION = 60  # 1 minute per tick
MOVEMENT_POINTS_NORMAL = 6000
MOVEMENT_POINTS_DIAGONAL = 7200

# Planet Types with Authentic Resources (NO SILICON - only Food, Metal, Hydrogen)
PLANET_TYPES = {
    "green": {
        "color": "green",
        "base_resources": {"food": 50000000, "metal": 30000000, "hydrogen": 15000000}
    },
    "blue": {
        "color": "blue", 
        "base_resources": {"food": 20000000, "metal": 60000000, "hydrogen": 50000000}
    },
    "brown": {
        "color": "brown",
        "base_resources": {"food": 15000000, "metal": 70000000, "hydrogen": 35000000}
    },
    "orange": {
        "color": "orange",
        "base_resources": {"food": 35000000, "metal": 45000000, "hydrogen": 50000000}
    }
}

# Building System Configuration
BUILDING_TYPES = {
    # Resource Buildings - 500 Metal base, +5% cost per level, +5 resources per level, 5 ticks build time
    "plantage": {
        "name": "Plantage",
        "description": "Produziert Nahrung pro Tick",
        "base_cost": 500,
        "cost_increase_percent": 5,
        "base_build_time_ticks": 5,
        "build_time_increase_percent": 5,
        "resource_bonus_per_level": 5,
        "resource_type": "food",
        "category": "resource"
    },
    "erzmine": {
        "name": "Erzmine",
        "description": "Produziert Metall pro Tick",
        "base_cost": 500,
        "cost_increase_percent": 5,
        "base_build_time_ticks": 5,
        "build_time_increase_percent": 5,
        "resource_bonus_per_level": 5,
        "resource_type": "metal",
        "category": "resource"
    },
    "elektrolysator": {
        "name": "Elektrolysator",
        "description": "Produziert Wasserstoff pro Tick",
        "base_cost": 500,
        "cost_increase_percent": 5,
        "base_build_time_ticks": 5,
        "build_time_increase_percent": 5,
        "resource_bonus_per_level": 5,
        "resource_type": "hydrogen",
        "category": "resource"
    },
    # Special Buildings
    "werft": {
        "name": "Werft",
        "description": "+1 Prototyp-Slot pro Level",
        "base_cost": 5000,
        "cost_increase_percent": 10,
        "base_build_time_ticks": 15,
        "build_time_increase_percent": 5,
        "prototype_slots_per_level": 1,
        "category": "special"
    },
    "raumhafen": {
        "name": "Raumhafen",
        "description": "+1 Flotte pro Level",
        "base_cost": 10000,
        "cost_increase_percent": 15,
        "base_build_time_ticks": 20,
        "build_time_increase_percent": 5,
        "fleet_slots_per_level": 1,
        "category": "special"
    },
    "forschungslabor": {
        "name": "Forschungslabor",
        "description": "-13% Forschungszeit pro Level",
        "base_cost": 15000,
        "cost_increase_percent": 8,
        "base_build_time_ticks": 30,
        "build_time_increase_percent": 5,
        "research_time_reduction_percent": 13,
        "category": "special"
    }
}

# Authentic Component Levels and Stats
COMPONENT_LEVELS = {
    "drives": {
        "ionenstrahl": {"levels": [1, 2, 3, 4], "speed_base": 350, "weight": 50},
        "rakete": {"levels": [1, 2, 3], "speed_base": 20, "weight": 2},
        "segel": {"levels": [1, 2, 3, 4, 5], "speed_base": 200, "weight": 20},
        "fusion": {"levels": [1, 2, 3, 4, 5, 6], "speed_base": 2000, "weight": 500},
        "antimaterie": {"levels": [1, 2, 3, 4, 5, 6, 7], "speed_base": 10000, "weight": 1000}
    },
    "shields": {
        "stahl": {"levels": [1, 2, 3, 4, 5], "defense_base": 5, "weight": 2},
        "aluminium": {"levels": [1, 2, 3, 4, 5], "defense_base": 5, "weight": 1},
        "quarz": {"levels": [1, 2, 3, 4, 5, 6], "defense_base": 20, "weight": 5},
        "titan": {"levels": [1, 2, 3, 4, 5, 6], "defense_base": 70, "weight": 50},
        "diamant": {"levels": [1, 2, 3, 4, 5, 6], "defense_base": 25, "weight": 20},
        "kupfer": {"levels": [1, 2, 3, 4, 5, 6], "defense_base": 500, "weight": 400},
        "keramik": {"levels": [1, 2, 3, 4, 5, 6], "defense_base": 1500, "weight": 600},
        "chrom": {"levels": [1, 2, 3, 4, 5, 6], "defense_base": 200, "weight": 150}
    },
    "weapons": {
        "laser": {"levels": [1, 2, 3, 4, 5, 6], "attack_base": 20, "weight": 60},
        "projektil": {"levels": [1, 2, 3, 4], "attack_base": 7, "weight": 1},
        "konventionell": {"levels": [1, 2, 3, 4, 5], "attack_base": 60, "weight": 50},
        "emp": {"levels": [1, 2, 3, 4, 5, 6], "attack_base": 25, "weight": 150},
        "plasma": {"levels": [1, 2, 3, 4, 5, 6], "attack_base": 50, "weight": 250},
        "abbaueinheit": {"levels": [1, 2, 3, 4, 5], "attack_base": 10, "weight": 2000, "mining_base": 100}
    },
    "special": {
        "kolonieeinheit": {"levels": [1], "weight": 5000}
    }
}

# --- AUTH MODELS ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: str
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    points: int = 0
    spaceport_position: Dict[str, int] = Field(default_factory=lambda: {"x": -1, "y": -1})  # Will be set on first login

# --- AUTHENTIC GAME MODELS ---
class Resources(BaseModel):
    food: int = 0
    metal: int = 0
    hydrogen: int = 0

# --- BUILDING MODELS ---
class BuildingLevel(BaseModel):
    building_type: str  # "plantage", "erzmine", "elektrolysator", "werft", "raumhafen", "forschungslabor"
    level: int = 0
    upgrading: bool = False
    upgrade_start_time: Optional[datetime] = None
    upgrade_end_time: Optional[datetime] = None

class UserBuildings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    buildings: List[BuildingLevel] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UpgradeBuilding(BaseModel):
    building_type: str

class Position(BaseModel):
    x: int
    y: int

class Planet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    position: Position
    planet_type: str  # "green", "blue", "brown", "orange"
    name: str
    resources: Resources
    owner_id: Optional[str] = None  # User who controls this planet
    owner_username: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ShipComponent(BaseModel):
    component_type: str  # "drive", "shield", "weapon"
    component_name: str  # "fusion", "titan", "laser"
    level: int
    quantity: int

class ShipDesign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    drive: ShipComponent
    shield: ShipComponent
    weapon: ShipComponent
    calculated_stats: Dict[str, Any] = Field(default_factory=dict)  # speed, combat_value, mining_capacity, build_cost, build_time
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Fleet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str  # "Flotte 1 von [username]"
    position: Position
    target_position: Optional[Position] = None
    ships: List[Dict[str, Any]] = Field(default_factory=list)  # [{"design_id": "...", "quantity": 100}]
    movement_start_time: Optional[datetime] = None
    movement_end_time: Optional[datetime] = None
    fleet_speed: int = 0  # pc per tick
    stance: str = "defensive"  # "defensive" or "aggressive"
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- COMBAT SYSTEM MODELS ---
class DebrisField(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    position: Position
    resource_type: str  # "food", "metal", or "hydrogen"
    amount: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BattleReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tick: int
    position: Position
    attacker_user_id: str
    attacker_username: str
    attacker_fleet_name: str
    attacker_combat_value: int
    attacker_ships_before: List[Dict[str, Any]]
    attacker_ships_lost: List[Dict[str, Any]]
    defender_user_id: str
    defender_username: str
    defender_fleet_name: str
    defender_combat_value: int
    defender_ships_before: List[Dict[str, Any]]
    defender_ships_lost: List[Dict[str, Any]]
    winner: str  # "attacker" or "defender"
    debris_created: Optional[Dict[str, Any]] = None  # {"resource_type": "metal", "amount": 1000}
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SetFleetStance(BaseModel):
    fleet_id: str
    stance: str  # "defensive" or "aggressive"

class GameState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_tick: int = 0
    last_tick_time: datetime = Field(default_factory=datetime.utcnow)
    next_tick_time: datetime = Field(default_factory=lambda: datetime.utcnow() + timedelta(seconds=TICK_DURATION))
    active_players: int = 0
    game_started: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# --- ADMIN MODELS ---
class GameConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    max_players: int = 20
    universe_size: int = 47
    tick_duration: int = 60
    min_planet_resources: int = 10000000
    max_planet_resources: int = 100000000
    mining_efficiency: float = 1.0  # Multiplier for mining operations
    colonization_time_hours: int = 24  # Time to colonize a planet
    noob_protection_hours: int = 48
    admin_password: str = Field(default_factory=lambda: os.environ.get('ADMIN_PASSWORD', 'admin2025'))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class InviteCode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    created_by_admin: bool = True
    used_by_user_id: Optional[str] = None
    used_by_username: Optional[str] = None
    used_at: Optional[datetime] = None
    max_uses: int = 1
    current_uses: int = 0
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AdminLogin(BaseModel):
    password: str

class CreateInviteCode(BaseModel):
    max_uses: int = 1
    expires_in_hours: Optional[int] = None

class UpdateGameConfig(BaseModel):
    max_players: Optional[int] = None
    universe_size: Optional[int] = None
    tick_duration: Optional[int] = None
    min_planet_resources: Optional[int] = None
    max_planet_resources: Optional[int] = None
    mining_efficiency: Optional[float] = None
    colonization_time_hours: Optional[int] = None
    noob_protection_hours: Optional[int] = None

class UserCreateWithInvite(BaseModel):
    username: str
    email: str
    password: str
    invite_code: str

# --- REQUEST MODELS ---
class ObservatoryView(BaseModel):
    center_x: int
    center_y: int

class CreateShipDesign(BaseModel):
    name: str
    drive_type: str
    drive_level: int
    drive_quantity: int
    shield_type: str
    shield_level: int
    shield_quantity: int
    weapon_type: str
    weapon_level: int
    weapon_quantity: int

class BuildFleet(BaseModel):
    planet_id: str
    design_id: str
    quantity: int
    fleet_name: str

class MoveFleet(BaseModel):
    fleet_id: str
    target_position: Position

class BuildShips(BaseModel):
    planet_id: str
    design_id: str
    quantity: int

class SpaceportShips(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    planet_id: str
    design_id: str
    quantity: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CreateFleetFromSpaceport(BaseModel):
    planet_id: str
    fleet_name: str
    ships: List[Dict[str, Any]]  # [{"design_id": "...", "quantity": 100}]

# --- RESEARCH SYSTEM MODELS ---
class ResearchLevel(BaseModel):
    category: str  # "drives", "shields", "weapons"
    technology: str  # "segel", "quarz", "laser", etc.
    level: int = 0  # Current research level
    researching: bool = False
    research_start_time: Optional[datetime] = None
    research_end_time: Optional[datetime] = None

class UserResearch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    research_levels: List[ResearchLevel] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StartResearch(BaseModel):
    category: str
    technology: str

# Research costs and times (authentic from original)
RESEARCH_BASE_COSTS = {
    "drives": {
        "segel": {"base_cost": 5000, "base_time_hours": 1},
        "fusion": {"base_cost": 750000, "base_time_hours": 24},
        "antimaterie": {"base_cost": 10000000, "base_time_hours": 72},
        "ionenstrahl": {"base_cost": 100000, "base_time_hours": 12},
        "rakete": {"base_cost": 1000, "base_time_hours": 0.5}
    },
    "shields": {
        "stahl": {"base_cost": 2000, "base_time_hours": 0.5},
        "aluminium": {"base_cost": 2500, "base_time_hours": 0.5},
        "quarz": {"base_cost": 50000, "base_time_hours": 6},
        "titan": {"base_cost": 200000, "base_time_hours": 18},
        "diamant": {"base_cost": 500000, "base_time_hours": 24},
        "kupfer": {"base_cost": 1000000, "base_time_hours": 36},
        "keramik": {"base_cost": 2500000, "base_time_hours": 48},
        "chrom": {"base_cost": 800000, "base_time_hours": 30}
    },
    "weapons": {
        "projektil": {"base_cost": 1500, "base_time_hours": 0.5},
        "laser": {"base_cost": 500000, "base_time_hours": 18},
        "konventionell": {"base_cost": 25000, "base_time_hours": 4},
        "emp": {"base_cost": 1500000, "base_time_hours": 36},
        "plasma": {"base_cost": 7500000, "base_time_hours": 60},
        "abbaueinheit": {"base_cost": 50000, "base_time_hours": 8}
    }
}

# --- AUTH FUNCTIONS ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# --- ADMIN FUNCTIONS ---
async def init_game_config():
    """Initialize game configuration"""
    existing_config = await db.game_config.find_one()
    if not existing_config:
        config = GameConfig()
        await db.game_config.insert_one(config.dict())
        return config
    return GameConfig(**existing_config)

# --- CONFIG CACHE (Punkt 7) ---
_config_cache: Optional[GameConfig] = None
_config_cache_time: float = 0.0
_CONFIG_CACHE_TTL: float = 10.0  # seconds

async def get_game_config() -> GameConfig:
    """Get current game configuration – cached for 10 seconds"""
    global _config_cache, _config_cache_time
    now = time.monotonic()
    if _config_cache is not None and (now - _config_cache_time) < _CONFIG_CACHE_TTL:
        return _config_cache
    config_doc = await db.game_config.find_one()
    if not config_doc:
        config = await init_game_config()
    else:
        config = GameConfig(**config_doc)
    _config_cache = config
    _config_cache_time = now
    return config

def invalidate_config_cache():
    """Call after any config update to force a fresh read"""
    global _config_cache
    _config_cache = None


async def verify_admin_access(password: str):
    """Verify admin password"""
    config = await get_game_config()
    return password == config.admin_password

async def init_user_research(user_id: str):
    """Initialize research levels for a new user - all start at level 0"""
    existing_research = await db.user_research.find_one({"user_id": user_id})
    if existing_research:
        return UserResearch(**existing_research)
    
    # Initialize all technologies at level 0
    research_levels = []
    for category, technologies in RESEARCH_BASE_COSTS.items():
        for tech_name in technologies:
            research_levels.append(ResearchLevel(
                category=category,
                technology=tech_name,
                level=0
            ))
    
    user_research = UserResearch(
        user_id=user_id,
        research_levels=research_levels
    )
    
    await db.user_research.insert_one(user_research.dict())
    return user_research

def calculate_research_cost(base_cost: int, current_level: int) -> int:
    """Calculate research cost with 15% reduction per level"""
    reduction_factor = (0.85 ** current_level)  # 15% reduction per level
    return int(base_cost * reduction_factor * (current_level + 1))

def calculate_research_time(base_time_hours: float, current_level: int) -> float:
    """Calculate research time - increases with level"""
    return base_time_hours * (current_level + 1)

# --- AUTHENTIC GAME FUNCTIONS ---
def calculate_ship_stats(design: CreateShipDesign) -> Dict[str, Any]:
    """Calculate authentic ship statistics - Abbaueinheit is now a weapon type"""
    # Get component data
    drive_data = COMPONENT_LEVELS["drives"][design.drive_type]
    shield_data = COMPONENT_LEVELS["shields"][design.shield_type]
    weapon_data = COMPONENT_LEVELS["weapons"][design.weapon_type]
    
    # Calculate total weight
    drive_weight = drive_data["weight"] * design.drive_quantity
    shield_weight = shield_data["weight"] * design.shield_quantity
    weapon_weight = weapon_data["weight"] * design.weapon_quantity
    
    total_weight = drive_weight + shield_weight + weapon_weight
    
    # Calculate speed (pc per tick)
    base_speed = drive_data["speed_base"] * design.drive_level * design.drive_quantity
    speed = max(1, int(base_speed / max(1, total_weight / 100)))  # Weight affects speed
    
    # Calculate combat value
    attack_power = weapon_data["attack_base"] * design.weapon_level * design.weapon_quantity
    defense_power = shield_data["defense_base"] * design.shield_level * design.shield_quantity
    combat_value = attack_power + defense_power
    
    # Calculate mining capacity per tick (if weapon is Abbaueinheit)
    mining_capacity = 0
    if "mining_base" in weapon_data:
        mining_capacity = weapon_data["mining_base"] * design.weapon_level * design.weapon_quantity
    
    # Calculate build costs (authentic formulas - NO SILICON)
    base_food_cost = 0  # No colony units anymore
    base_metal_cost = (drive_weight + weapon_weight) * design.drive_level * 10 + (shield_weight + weapon_weight) * design.shield_level * 5
    base_hydrogen_cost = weapon_weight * design.weapon_level * 2

    # Calculate build time (based on complexity)
    build_time_ticks = max(1, total_weight // 100) + design.drive_level + design.shield_level + design.weapon_level
    
    return {
        "speed": speed,
        "combat_value": combat_value,
        "mining_capacity": mining_capacity,
        "total_weight": total_weight,
        "build_cost": {
            "food": base_food_cost,
            "metal": base_metal_cost,
            "hydrogen": base_hydrogen_cost
        },
        "build_time_ticks": build_time_ticks
    }

async def generate_universe():
    """Generate planets across the universe"""
    existing_planets = await db.planets.count_documents({})
    if existing_planets > 0:
        return  # Universe already generated
    
    config = await get_game_config()
    universe_size = config.universe_size
    min_resources = config.min_planet_resources
    max_resources = config.max_planet_resources
    
    # Map planet types to resource names (NO SILICON)
    planet_type_to_name = {
        "green": "Nahrung",
        "blue": "Wasserstoff", 
        "brown": "Metall",
        "orange": "Wasserstoff"
    }
    
    planets_to_create = []
    
    # Generate planets based on universe size
    planet_count = int((universe_size * universe_size) * 0.08)  # ~8% of fields have planets
    for i in range(planet_count):
        x = random.randint(0, universe_size - 1)
        y = random.randint(0, universe_size - 1)
        
        # Skip if position already has a planet
        if any(p["position"]["x"] == x and p["position"]["y"] == y for p in planets_to_create):
            continue
            
        planet_type = random.choice(list(PLANET_TYPES.keys()))
        base_resources = PLANET_TYPES[planet_type]["base_resources"].copy()
        
        # Scale resources based on config
        resource_multiplier = random.uniform(min_resources / 50000000, max_resources / 50000000)
        for resource in base_resources:
            base_resources[resource] = int(base_resources[resource] * resource_multiplier)
        
        # Get planet name based on type (no numbers!)
        resource_name = planet_type_to_name[planet_type]
        
        planet = {
            "id": str(uuid.uuid4()),
            "position": {"x": x, "y": y},
            "planet_type": planet_type,
            "name": resource_name,
            "resources": base_resources,
            "owner_id": None,
            "owner_username": None,
            "created_at": datetime.utcnow()
        }
        planets_to_create.append(planet)
    
    # Insert all planets
    if planets_to_create:
        await db.planets.insert_many(planets_to_create)

async def assign_spaceport_to_user(user_id: str, username: str):
    """Assign a random planet as spaceport to new user"""
    # Find an unoccupied planet
    unoccupied_planet = await db.planets.find_one({"owner_id": None})
    if not unoccupied_planet:
        raise HTTPException(status_code=400, detail="No available planets for spaceport")
    
    # Assign planet to user
    await db.planets.update_one(
        {"id": unoccupied_planet["id"]},
        {"$set": {"owner_id": user_id, "owner_username": username}}
    )
    
    # Update user's spaceport position
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"spaceport_position": unoccupied_planet["position"]}}
    )
    
    return unoccupied_planet

async def init_game_state():
    """Initialize game state and universe"""
    existing_state = await db.game_state.find_one()
    if not existing_state:
        game_state = GameState()
        await db.game_state.insert_one(game_state.dict())
        await generate_universe()  # Generate planets
        await init_game_config()  # Initialize game config
        return game_state
    return GameState(**existing_state)

# --- COMBAT SYSTEM FUNCTIONS ---
async def calculate_fleet_combat_value(fleet: Fleet) -> int:
    """Calculate total combat value of a fleet"""
    total_combat_value = 0
    for ship_group in fleet.ships:
        design = await db.ship_designs.find_one({"id": ship_group["design_id"]})
        if design:
            design_obj = ShipDesign(**design)
            combat_value = design_obj.calculated_stats.get("combat_value", 0)
            total_combat_value += combat_value * ship_group["quantity"]
    return total_combat_value

async def calculate_fleet_build_cost(fleet: Fleet) -> Dict[str, int]:
    """Calculate total build cost of all ships in a fleet"""
    total_cost = {"food": 0, "metal": 0, "hydrogen": 0}
    for ship_group in fleet.ships:
        design = await db.ship_designs.find_one({"id": ship_group["design_id"]})
        if design:
            design_obj = ShipDesign(**design)
            build_cost = design_obj.calculated_stats.get("build_cost", {})
            for resource in ["food", "metal", "hydrogen"]:
                total_cost[resource] += build_cost.get(resource, 0) * ship_group["quantity"]
    return total_cost

async def process_combat(attacker_fleet: Fleet, defender_fleet: Fleet, game_state: GameState) -> Optional[BattleReport]:
    """Process combat between two fleets. Returns battle report."""
    # Get usernames
    attacker_user = await db.users.find_one({"id": attacker_fleet.user_id})
    defender_user = await db.users.find_one({"id": defender_fleet.user_id})
    
    if not attacker_user or not defender_user:
        return None
    
    # Calculate combat values
    attacker_cv = await calculate_fleet_combat_value(attacker_fleet)
    defender_cv = await calculate_fleet_combat_value(defender_fleet)
    
    # Store ships before combat
    attacker_ships_before = [s.copy() for s in attacker_fleet.ships]
    defender_ships_before = [s.copy() for s in defender_fleet.ships]
    
    # Determine winner (higher combat value wins)
    total_cv = attacker_cv + defender_cv
    if total_cv == 0:
        return None  # No combat if no combat value
    
    winner = "attacker" if attacker_cv > defender_cv else "defender"
    
    # Calculate losses proportionally
    # Loser loses more ships proportionally to the difference
    if winner == "attacker":
        # Attacker wins - defender loses more
        defender_loss_ratio = min(1.0, attacker_cv / max(1, defender_cv) * 0.5)
        attacker_loss_ratio = min(0.8, defender_cv / max(1, attacker_cv) * 0.3)
    else:
        # Defender wins - attacker loses more
        attacker_loss_ratio = min(1.0, defender_cv / max(1, attacker_cv) * 0.5)
        defender_loss_ratio = min(0.8, attacker_cv / max(1, defender_cv) * 0.3)
    
    # Apply losses to ships
    attacker_ships_lost = []
    defender_ships_lost = []
    
    # Process attacker losses
    new_attacker_ships = []
    for ship_group in attacker_fleet.ships:
        lost_quantity = int(ship_group["quantity"] * attacker_loss_ratio)
        remaining = ship_group["quantity"] - lost_quantity
        if lost_quantity > 0:
            attacker_ships_lost.append({"design_id": ship_group["design_id"], "quantity": lost_quantity})
        if remaining > 0:
            new_attacker_ships.append({"design_id": ship_group["design_id"], "quantity": remaining})
    
    # Process defender losses
    new_defender_ships = []
    for ship_group in defender_fleet.ships:
        lost_quantity = int(ship_group["quantity"] * defender_loss_ratio)
        remaining = ship_group["quantity"] - lost_quantity
        if lost_quantity > 0:
            defender_ships_lost.append({"design_id": ship_group["design_id"], "quantity": lost_quantity})
        if remaining > 0:
            new_defender_ships.append({"design_id": ship_group["design_id"], "quantity": remaining})
    
    # Calculate debris from destroyed ships (20% of build costs)
    total_debris_cost = {"food": 0, "metal": 0, "hydrogen": 0}
    
    for lost_ship in attacker_ships_lost:
        design = await db.ship_designs.find_one({"id": lost_ship["design_id"]})
        if design:
            design_obj = ShipDesign(**design)
            build_cost = design_obj.calculated_stats.get("build_cost", {})
            for resource in ["food", "metal", "hydrogen"]:
                total_debris_cost[resource] += int(build_cost.get(resource, 0) * lost_ship["quantity"] * 0.2)
    
    for lost_ship in defender_ships_lost:
        design = await db.ship_designs.find_one({"id": lost_ship["design_id"]})
        if design:
            design_obj = ShipDesign(**design)
            build_cost = design_obj.calculated_stats.get("build_cost", {})
            for resource in ["food", "metal", "hydrogen"]:
                total_debris_cost[resource] += int(build_cost.get(resource, 0) * lost_ship["quantity"] * 0.2)
    
    # Create debris field with random resource type
    debris_info = None
    total_debris = sum(total_debris_cost.values())
    if total_debris > 0:
        resource_types = ["food", "metal", "hydrogen"]
        debris_resource = random.choice(resource_types)
        debris_amount = total_debris
        
        debris_field = DebrisField(
            position=attacker_fleet.position,
            resource_type=debris_resource,
            amount=debris_amount
        )
        await db.debris_fields.insert_one(debris_field.dict())
        debris_info = {"resource_type": debris_resource, "amount": debris_amount}
    
    # Update fleets in database
    if len(new_attacker_ships) > 0:
        await db.fleets.update_one(
            {"id": attacker_fleet.id},
            {"$set": {"ships": new_attacker_ships}}
        )
    else:
        # Fleet destroyed
        await db.fleets.delete_one({"id": attacker_fleet.id})
    
    if len(new_defender_ships) > 0:
        await db.fleets.update_one(
            {"id": defender_fleet.id},
            {"$set": {"ships": new_defender_ships}}
        )
    else:
        # Fleet destroyed
        await db.fleets.delete_one({"id": defender_fleet.id})
    
    # Create battle report
    battle_report = BattleReport(
        tick=game_state.current_tick,
        position=attacker_fleet.position,
        attacker_user_id=attacker_fleet.user_id,
        attacker_username=attacker_user["username"],
        attacker_fleet_name=attacker_fleet.name,
        attacker_combat_value=attacker_cv,
        attacker_ships_before=attacker_ships_before,
        attacker_ships_lost=attacker_ships_lost,
        defender_user_id=defender_fleet.user_id,
        defender_username=defender_user["username"],
        defender_fleet_name=defender_fleet.name,
        defender_combat_value=defender_cv,
        defender_ships_before=defender_ships_before,
        defender_ships_lost=defender_ships_lost,
        winner=winner,
        debris_created=debris_info
    )
    
    await db.battle_reports.insert_one(battle_report.dict())
    
    return battle_report

async def process_tick():
    """Process authentic game tick - movement, mining, research, and buildings"""
    config = await get_game_config()
    current_time = datetime.utcnow()
    
    # Process completed building upgrades
    all_buildings = await db.user_buildings.find({}).to_list(1000)
    for buildings_data in all_buildings:
        user_buildings = UserBuildings(**buildings_data)
        buildings_updated = False
        
        for i, building in enumerate(user_buildings.buildings):
            if (building.upgrading and building.upgrade_end_time and 
                building.upgrade_end_time <= current_time):
                # Building upgrade completed
                user_buildings.buildings[i].level += 1
                user_buildings.buildings[i].upgrading = False
                user_buildings.buildings[i].upgrade_start_time = None
                user_buildings.buildings[i].upgrade_end_time = None
                buildings_updated = True
                
                # Award points for building completion
                await db.users.update_one(
                    {"id": user_buildings.user_id},
                    {"$inc": {"points": 500}}  # 500 points per building level
                )
        
        if buildings_updated:
            await db.user_buildings.update_one(
                {"user_id": user_buildings.user_id},
                {"$set": {"buildings": [b.dict() for b in user_buildings.buildings]}}
            )
    
    # Apply resource building bonuses to player planets
    all_users = await db.users.find({}).to_list(1000)
    for user_data in all_users:
        user_id = user_data["id"]
        
        # Get user's buildings
        user_buildings_data = await db.user_buildings.find_one({"user_id": user_id})
        if not user_buildings_data:
            continue
        
        user_buildings = UserBuildings(**user_buildings_data)
        
        # Calculate resource bonuses from buildings
        food_bonus = 0
        metal_bonus = 0
        hydrogen_bonus = 0
        
        for building in user_buildings.buildings:
            if building.building_type == "plantage":
                food_bonus = building.level * 5  # +5 food per level
            elif building.building_type == "erzmine":
                metal_bonus = building.level * 5  # +5 metal per level
            elif building.building_type == "elektrolysator":
                hydrogen_bonus = building.level * 5  # +5 hydrogen per level
        
        # Apply bonuses to user's planets
        if food_bonus > 0 or metal_bonus > 0 or hydrogen_bonus > 0:
            user_planets = await db.planets.find({"owner_id": user_id}).to_list(100)
            for planet in user_planets:
                await db.planets.update_one(
                    {"id": planet["id"]},
                    {"$inc": {
                        "resources.food": food_bonus,
                        "resources.metal": metal_bonus,
                        "resources.hydrogen": hydrogen_bonus
                    }}
                )
    
    # Process completed research
    all_research = await db.user_research.find({}).to_list(1000)
    
    for research_data in all_research:
        research_obj = UserResearch(**research_data)
        research_updated = False
        
        for i, level in enumerate(research_obj.research_levels):
            if (level.researching and level.research_end_time and 
                level.research_end_time <= current_time):
                # Research completed
                research_obj.research_levels[i].level += 1
                research_obj.research_levels[i].researching = False
                research_obj.research_levels[i].research_start_time = None
                research_obj.research_levels[i].research_end_time = None
                research_updated = True
                
                # Award points for research completion
                await db.users.update_one(
                    {"id": research_obj.user_id},
                    {"$inc": {"points": 1000}}  # 1000 points per research level
                )
        
        if research_updated:
            await db.user_research.update_one(
                {"user_id": research_obj.user_id},
                {"$set": research_obj.dict()}
            )
    
    # Update fleets in movement
    fleets = await db.fleets.find({"movement_end_time": {"$lte": datetime.utcnow()}}).to_list(1000)
    for fleet_data in fleets:
        fleet = Fleet(**fleet_data)
        if fleet.target_position:
            # Fleet has arrived
            await db.fleets.update_one(
                {"id": fleet.id},
                {"$set": {
                    "position": fleet.target_position.dict(),
                    "target_position": None,
                    "movement_start_time": None,
                    "movement_end_time": None
                }}
            )
    
    # --- COMBAT PROCESSING ---
    # Get current game state for tick number
    game_state = await init_game_state()
    
    # Find all stationary fleets and check for combat
    all_fleets = await db.fleets.find({"movement_end_time": None}).to_list(1000)
    
    # Group fleets by position
    fleets_by_position = {}
    for fleet_data in all_fleets:
        fleet = Fleet(**fleet_data)
        pos_key = f"{fleet.position.x},{fleet.position.y}"
        if pos_key not in fleets_by_position:
            fleets_by_position[pos_key] = []
        fleets_by_position[pos_key].append(fleet)
    
    # Process combat for positions with multiple fleets from different users
    processed_fleets = set()
    for pos_key, position_fleets in fleets_by_position.items():
        if len(position_fleets) < 2:
            continue
        
        # Check for enemy fleets at this position
        for i, fleet1 in enumerate(position_fleets):
            if fleet1.id in processed_fleets:
                continue
            
            for fleet2 in position_fleets[i+1:]:
                if fleet2.id in processed_fleets:
                    continue
                
                # Check if fleets belong to different users
                if fleet1.user_id == fleet2.user_id:
                    continue
                
                # Check if at least one fleet is aggressive
                if fleet1.stance != "aggressive" and fleet2.stance != "aggressive":
                    continue
                
                # Determine attacker (aggressive fleet initiates)
                if fleet1.stance == "aggressive":
                    attacker = fleet1
                    defender = fleet2
                else:
                    attacker = fleet2
                    defender = fleet1
                
                # Process combat
                battle_report = await process_combat(attacker, defender, game_state)
                
                if battle_report:
                    processed_fleets.add(fleet1.id)
                    processed_fleets.add(fleet2.id)
                    logger.info(f"Combat at ({pos_key}): {attacker.name} vs {defender.name} - Winner: {battle_report.winner}")
    
    # Process mining operations for stationary fleets
    stationary_fleets = await db.fleets.find({"movement_end_time": None}).to_list(1000)
    for fleet_data in stationary_fleets:
        fleet = Fleet(**fleet_data)
        
        # Check if fleet is on a planet
        planet = await db.planets.find_one({
            "position.x": fleet.position.x,
            "position.y": fleet.position.y,
            "owner_id": fleet.user_id  # Only mine from owned planets
        })
        
        if planet:
            planet_obj = Planet(**planet)
            
            # Calculate total mining capacity of this fleet
            total_mining_capacity = 0
            for ship_group in fleet.ships:
                design = await db.ship_designs.find_one({"id": ship_group["design_id"]})
                if design:
                    design_obj = ShipDesign(**design)
                    mining_capacity = design_obj.calculated_stats.get("mining_capacity", 0)
                    total_mining_capacity += mining_capacity * ship_group["quantity"]
            
            if total_mining_capacity > 0:
                # Mine resources proportionally
                mining_efficiency = config.mining_efficiency
                actual_mining = int(total_mining_capacity * mining_efficiency)
                
                # Distribute mining across resource types based on availability (NO SILICON)
                total_resources = (planet_obj.resources.food + planet_obj.resources.metal + 
                                 planet_obj.resources.hydrogen)
                
                if total_resources > 0:
                    # Calculate proportional mining
                    food_ratio = planet_obj.resources.food / total_resources
                    metal_ratio = planet_obj.resources.metal / total_resources
                    hydrogen_ratio = planet_obj.resources.hydrogen / total_resources
                    
                    food_mined = min(int(actual_mining * food_ratio), planet_obj.resources.food)
                    metal_mined = min(int(actual_mining * metal_ratio), planet_obj.resources.metal)
                    hydrogen_mined = min(int(actual_mining * hydrogen_ratio), planet_obj.resources.hydrogen)
                    
                    # Update planet resources (subtract mined)
                    await db.planets.update_one(
                        {"id": planet_obj.id},
                        {"$inc": {
                            "resources.food": -food_mined,
                            "resources.metal": -metal_mined,
                            "resources.hydrogen": -hydrogen_mined
                        }}
                    )
                    
                    # Add mined resources to user's total (for now, we could implement cargo ships later)
                    # For simplicity, we'll add points to the user
                    resources_value = food_mined + metal_mined + hydrogen_mined
                    if resources_value > 0:
                        await db.users.update_one(
                            {"id": fleet.user_id},
                            {"$inc": {"points": resources_value // 1000}}  # 1 point per 1000 resources
                        )
    
    # Update game state with configured tick duration
    next_tick_time = datetime.utcnow() + timedelta(seconds=config.tick_duration)
    await db.game_state.update_one(
        {},
        {"$inc": {"current_tick": 1}, 
         "$set": {"last_tick_time": datetime.utcnow(), "next_tick_time": next_tick_time}}
    )

# --- AUTH ROUTES ---
@api_router.post("/register", response_model=Token)
async def register(user_data: UserCreateWithInvite):
    # Verify invite code
    invite_code = await db.invite_codes.find_one({"code": user_data.invite_code})
    if not invite_code:
        raise HTTPException(status_code=400, detail="Invalid invite code")
    
    invite = InviteCode(**invite_code)
    
    # Check if code is expired
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invite code has expired")
    
    # Check if code has been used too many times
    if invite.current_uses >= invite.max_uses:
        raise HTTPException(status_code=400, detail="Invite code has been used up")
    
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Check max players
    config = await get_game_config()
    player_count = await db.users.count_documents({})
    if player_count >= config.max_players:
        raise HTTPException(status_code=400, detail=f"Maximum {config.max_players} players reached")
    
    # Create user
    hashed_password = pwd_context.hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    await db.users.insert_one(user.dict())
    
    # Mark invite code as used
    await db.invite_codes.update_one(
        {"id": invite.id},
        {"$set": {
            "used_by_user_id": user.id,
            "used_by_username": user.username,
            "used_at": datetime.utcnow()
        },
        "$inc": {"current_uses": 1}}
    )
    
    # Initialize research for user
    await init_user_research(user.id)
    
    # Assign spaceport to user
    await assign_spaceport_to_user(user.id, user.username)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    user = await db.users.find_one({"username": user_data.username})
    if not user or not pwd_context.verify(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # If user doesn't have spaceport, assign one
    if user["spaceport_position"]["x"] == -1:
        await assign_spaceport_to_user(user["id"], user["username"])
    
    # Initialize research if not exists
    await init_user_research(user["id"])
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- ADMIN ROUTES ---
@api_router.post("/admin/login")
async def admin_login(admin_data: AdminLogin):
    """Admin login with password"""
    if not await verify_admin_access(admin_data.password):
        raise HTTPException(status_code=401, detail="Invalid admin password")
    
    # Create admin token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "admin", "admin": True}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "admin": True}

@api_router.get("/admin/config", response_model=GameConfig)
async def get_admin_config(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get game configuration (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return await get_game_config()

@api_router.post("/admin/config")
async def update_admin_config(config_update: UpdateGameConfig, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Update game configuration (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    update_data = {k: v for k, v in config_update.dict().items() if v is not None}
    
    await db.game_config.update_one({}, {"$set": update_data})
    invalidate_config_cache()
    return {"message": "Configuration updated successfully"}

@api_router.post("/admin/invite-codes", response_model=InviteCode)
async def create_invite_code(invite_data: CreateInviteCode, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Create new invite code (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    expires_at = None
    if invite_data.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=invite_data.expires_in_hours)
    
    invite_code = InviteCode(
        code=code,
        max_uses=invite_data.max_uses,
        expires_at=expires_at
    )
    
    await db.invite_codes.insert_one(invite_code.dict())
    return invite_code

@api_router.get("/admin/invite-codes", response_model=List[InviteCode])
async def get_invite_codes(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all invite codes (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    codes = await db.invite_codes.find().sort("created_at", -1).to_list(100)
    return [InviteCode(**code) for code in codes]

@api_router.delete("/admin/invite-codes/{code_id}")
async def delete_invite_code(code_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Delete invite code (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    result = await db.invite_codes.delete_one({"id": code_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Invite code not found")
    
    return {"message": "Invite code deleted successfully"}

@api_router.get("/admin/users")
async def get_all_users(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all users (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    users = await db.users.find().sort("created_at", -1).to_list(100)
    user_ids = [u["id"] for u in users]

    planet_pipeline = [
        {"$match": {"owner_id": {"$in": user_ids}}},
        {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}}
    ]
    fleet_pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}
    ]
    planet_counts = {doc["_id"]: doc["count"] async for doc in db.planets.aggregate(planet_pipeline)}
    fleet_counts  = {doc["_id"]: doc["count"] async for doc in db.fleets.aggregate(fleet_pipeline)}

    return [
        {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "points": user.get("points", 0),
            "planets": planet_counts.get(user["id"], 0),
            "fleets":  fleet_counts.get(user["id"], 0),
            "created_at": user["created_at"],
            "spaceport_position": user.get("spaceport_position", {"x": -1, "y": -1}),
        }
        for user in users
    ]

@api_router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Delete user (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Delete user's planets, fleets, ship designs
    await db.planets.update_many({"owner_id": user_id}, {"$set": {"owner_id": None, "owner_username": None}})
    await db.fleets.delete_many({"user_id": user_id})
    await db.ship_designs.delete_many({"user_id": user_id})
    
    # Delete user
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User deleted successfully"}

@api_router.post("/admin/reset-game")
async def reset_game(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Reset entire game (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Delete all game data except admin config and invite codes
    await db.users.delete_many({})
    await db.planets.delete_many({})
    await db.fleets.delete_many({})
    await db.ship_designs.delete_many({})
    await db.game_state.delete_many({})
    
    # Reinitialize game
    await init_game_state()
    
    return {"message": "Game reset successfully"}

@api_router.get("/admin/stats")
async def get_admin_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get game statistics (admin only)"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("admin"):
            raise HTTPException(status_code=403, detail="Admin access required")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    config = await get_game_config()
    user_count = await db.users.count_documents({})
    planet_count = await db.planets.count_documents({})
    occupied_planets = await db.planets.count_documents({"owner_id": {"$ne": None}})
    fleet_count = await db.fleets.count_documents({})
    invite_codes = await db.invite_codes.count_documents({})
    
    return {
        "players": {"current": user_count, "max": config.max_players},
        "planets": {"total": planet_count, "occupied": occupied_planets},
        "fleets": fleet_count,
        "invite_codes": invite_codes,
        "universe_size": f"{config.universe_size}x{config.universe_size}",
        "tick_duration": f"{config.tick_duration}s"
    }

# --- AUTHENTIC GAME ROUTES ---
@api_router.get("/game/state")
async def get_game_state():
    game_state = await init_game_state()
    config = await get_game_config()
    
    # Return game state with tick_duration from config
    state_dict = game_state.dict()
    state_dict['tick_duration'] = config.tick_duration
    
    return state_dict

@api_router.post("/game/observatory")
async def get_observatory_view(view_data: ObservatoryView, current_user: User = Depends(get_current_user)):
    """Get 7x7 observatory view centered on specified position"""
    center_x, center_y = view_data.center_x, view_data.center_y
    
    # Get 7x7 area around center
    view = {}
    for dx in range(-3, 4):  # -3 to +3 = 7 fields
        for dy in range(-3, 4):
            x = center_x + dx
            y = center_y + dy
            
            # Check bounds
            if 0 <= x < UNIVERSE_SIZE and 0 <= y < UNIVERSE_SIZE:
                view[f"{x},{y}"] = {
                    "position": {"x": x, "y": y},
                    "planet": None,
                    "fleets": []
                }
    
    # Get planets in view
    planets = await db.planets.find({
        "position.x": {"$gte": center_x - 3, "$lte": center_x + 3},
        "position.y": {"$gte": center_y - 3, "$lte": center_y + 3}
    }).to_list(100)
    
    for planet_data in planets:
        planet = Planet(**planet_data)
        key = f"{planet.position.x},{planet.position.y}"
        if key in view:
            view[key]["planet"] = planet.dict()
    
    # Get fleets in view
    fleets = await db.fleets.find({
        "position.x": {"$gte": center_x - 3, "$lte": center_x + 3},
        "position.y": {"$gte": center_y - 3, "$lte": center_y + 3}
    }).to_list(100)
    
    for fleet_data in fleets:
        fleet = Fleet(**fleet_data)
        key = f"{fleet.position.x},{fleet.position.y}"
        if key in view:
            user = await db.users.find_one({"id": fleet.user_id})
            fleet_info = fleet.dict()
            fleet_info["username"] = user["username"] if user else "Unknown"
            view[key]["fleets"].append(fleet_info)
    
    return {
        "view": view,
        "center": {"x": center_x, "y": center_y},
        "size": OBSERVATORY_VIEW_SIZE
    }

@api_router.get("/game/user-spaceport")
async def get_user_spaceport(current_user: User = Depends(get_current_user)):
    """Get user's spaceport position for centering observatory"""
    return {
        "spaceport_position": current_user.spaceport_position,
        "username": current_user.username
    }

@api_router.get("/game/planets")
async def get_user_planets(current_user: User = Depends(get_current_user)):
    """Get planets owned by current user"""
    planets = await db.planets.find({"owner_id": current_user.id}).to_list(100)
    return [Planet(**planet) for planet in planets]

@api_router.post("/game/ship-design", response_model=ShipDesign)
async def create_ship_design(design_data: CreateShipDesign, current_user: User = Depends(get_current_user)):
    """Create a new ship design (Prototyp) - limited by Werft level"""
    # Check Werft level for prototype slots
    user_buildings_data = await db.user_buildings.find_one({"user_id": current_user.id})
    werft_level = 0
    if user_buildings_data:
        user_buildings = UserBuildings(**user_buildings_data)
        for building in user_buildings.buildings:
            if building.building_type == "werft":
                werft_level = building.level
                break
    
    max_prototypes = werft_level  # 1 prototype per Werft level
    current_designs = await db.ship_designs.count_documents({"user_id": current_user.id})
    
    if current_designs >= max_prototypes:
        raise HTTPException(
            status_code=400, 
            detail=f"Prototyp-Limit erreicht! Werft Level {werft_level} erlaubt nur {max_prototypes} Prototypen. Bauen Sie die Werft aus."
        )
    
    # Validate components exist and levels are valid
    if design_data.drive_type not in COMPONENT_LEVELS["drives"]:
        raise HTTPException(status_code=400, detail="Invalid drive type")
    if design_data.shield_type not in COMPONENT_LEVELS["shields"]:
        raise HTTPException(status_code=400, detail="Invalid shield type")
    if design_data.weapon_type not in COMPONENT_LEVELS["weapons"]:
        raise HTTPException(status_code=400, detail="Invalid weapon type")
    
    # Calculate ship statistics
    calculated_stats = calculate_ship_stats(design_data)
    
    # Create design
    design = ShipDesign(
        user_id=current_user.id,
        name=design_data.name,
        drive=ShipComponent(
            component_type="drive",
            component_name=design_data.drive_type,
            level=design_data.drive_level,
            quantity=design_data.drive_quantity
        ),
        shield=ShipComponent(
            component_type="shield", 
            component_name=design_data.shield_type,
            level=design_data.shield_level,
            quantity=design_data.shield_quantity
        ),
        weapon=ShipComponent(
            component_type="weapon",
            component_name=design_data.weapon_type,
            level=design_data.weapon_level,
            quantity=design_data.weapon_quantity
        ),
        calculated_stats=calculated_stats
    )
    
    await db.ship_designs.insert_one(design.dict())
    return design

@api_router.get("/game/ship-designs", response_model=List[ShipDesign])
async def get_ship_designs(current_user: User = Depends(get_current_user)):
    """Get user's ship designs"""
    designs = await db.ship_designs.find({"user_id": current_user.id}).to_list(100)
    return [ShipDesign(**design) for design in designs]

@api_router.get("/game/component-levels")
async def get_component_levels():
    """Get available component types and levels"""
    return COMPONENT_LEVELS

@api_router.post("/game/build-ships")
async def build_ships(build_data: BuildShips, current_user: User = Depends(get_current_user)):
    """Build ships and store them in spaceport (not as fleet)"""
    # Check planet ownership
    planet = await db.planets.find_one({"id": build_data.planet_id, "owner_id": current_user.id})
    if not planet:
        raise HTTPException(status_code=404, detail="Planet not found or not owned")
    
    # Check ship design exists
    design = await db.ship_designs.find_one({"id": build_data.design_id, "user_id": current_user.id})
    if not design:
        raise HTTPException(status_code=404, detail="Ship design not found")
    
    design_obj = ShipDesign(**design)
    planet_obj = Planet(**planet)
    
    # Calculate total build cost (NO SILICON)
    total_cost = {
        "food": design_obj.calculated_stats["build_cost"]["food"] * build_data.quantity,
        "metal": design_obj.calculated_stats["build_cost"]["metal"] * build_data.quantity,
        "hydrogen": design_obj.calculated_stats["build_cost"]["hydrogen"] * build_data.quantity
    }
    
    # Check resources
    if (planet_obj.resources.food < total_cost["food"] or
        planet_obj.resources.metal < total_cost["metal"] or
        planet_obj.resources.hydrogen < total_cost["hydrogen"]):
        raise HTTPException(status_code=400, detail="Insufficient resources")
    
    # Deduct resources
    await db.planets.update_one(
        {"id": build_data.planet_id},
        {"$inc": {
            "resources.food": -total_cost["food"],
            "resources.metal": -total_cost["metal"],
            "resources.hydrogen": -total_cost["hydrogen"]
        }}
    )
    
    # Store ships in spaceport (not as fleet)
    spaceport_ships = SpaceportShips(
        user_id=current_user.id,
        planet_id=build_data.planet_id,
        design_id=build_data.design_id,
        quantity=build_data.quantity
    )
    
    await db.spaceport_ships.insert_one(spaceport_ships.dict())
    
    # Update user stats
    await db.users.update_one(
        {"id": current_user.id},
        {"$inc": {"points": build_data.quantity * 50}}
    )
    
    return {
        "message": f"{build_data.quantity} Schiffe im Raumhafen produziert",
        "ships": spaceport_ships.dict()
    }

@api_router.get("/game/spaceport-ships")
async def get_spaceport_ships(current_user: User = Depends(get_current_user)):
    """Get ships stored in user's spaceports"""
    spaceport_ships = await db.spaceport_ships.find({"user_id": current_user.id}).to_list(1000)
    
    # Group by planet and add design info
    result = {}
    for ship_data in spaceport_ships:
        ship = SpaceportShips(**ship_data)
        planet = await db.planets.find_one({"id": ship.planet_id})
        design = await db.ship_designs.find_one({"id": ship.design_id})
        
        if planet and design:
            planet_key = f"{planet['name']} ({planet['position']['x']}, {planet['position']['y']})"
            if planet_key not in result:
                result[planet_key] = {
                    "planet_id": ship.planet_id,
                    "planet_name": planet['name'],
                    "position": planet['position'],
                    "ships": []
                }
            
            result[planet_key]["ships"].append({
                "id": ship.id,
                "design_id": ship.design_id,
                "design_name": design['name'],
                "quantity": ship.quantity,
                "created_at": ship.created_at
            })
    
    return result

@api_router.post("/game/create-fleet")
async def create_fleet_from_spaceport(fleet_data: CreateFleetFromSpaceport, current_user: User = Depends(get_current_user)):
    """Create fleet from ships in spaceport - limited by Raumhafen level"""
    # Check Raumhafen level for fleet slots
    user_buildings_data = await db.user_buildings.find_one({"user_id": current_user.id})
    raumhafen_level = 0
    if user_buildings_data:
        user_buildings = UserBuildings(**user_buildings_data)
        for building in user_buildings.buildings:
            if building.building_type == "raumhafen":
                raumhafen_level = building.level
                break
    
    max_fleets = raumhafen_level  # 1 fleet per Raumhafen level
    current_fleets = await db.fleets.count_documents({"user_id": current_user.id})
    
    if current_fleets >= max_fleets:
        raise HTTPException(
            status_code=400, 
            detail=f"Flotten-Limit erreicht! Raumhafen Level {raumhafen_level} erlaubt nur {max_fleets} Flotten. Bauen Sie den Raumhafen aus."
        )
    
    # Check planet ownership
    planet = await db.planets.find_one({"id": fleet_data.planet_id, "owner_id": current_user.id})
    if not planet:
        raise HTTPException(status_code=404, detail="Planet not found or not owned")
    
    planet_obj = Planet(**planet)
    fleet_ships = []
    slowest_speed = 999999
    
    # Process each ship type for the fleet
    for ship_request in fleet_data.ships:
        design_id = ship_request["design_id"]
        requested_quantity = ship_request["quantity"]
        
        # Find ships in spaceport
        spaceport_ship = await db.spaceport_ships.find_one({
            "user_id": current_user.id,
            "planet_id": fleet_data.planet_id,
            "design_id": design_id
        })
        
        if not spaceport_ship:
            raise HTTPException(status_code=404, detail=f"No ships of design {design_id} found in spaceport")
        
        spaceport_ship_obj = SpaceportShips(**spaceport_ship)
        
        if spaceport_ship_obj.quantity < requested_quantity:
            raise HTTPException(status_code=400, detail=f"Not enough ships. Have {spaceport_ship_obj.quantity}, requested {requested_quantity}")
        
        # Get design for speed calculation
        design = await db.ship_designs.find_one({"id": design_id})
        if design:
            design_obj = ShipDesign(**design)
            ship_speed = design_obj.calculated_stats.get("speed", 1)
            slowest_speed = min(slowest_speed, ship_speed)
        
        fleet_ships.append({
            "design_id": design_id,
            "quantity": requested_quantity
        })
        
        # Remove ships from spaceport
        new_quantity = spaceport_ship_obj.quantity - requested_quantity
        if new_quantity > 0:
            await db.spaceport_ships.update_one(
                {"id": spaceport_ship_obj.id},
                {"$set": {"quantity": new_quantity}}
            )
        else:
            await db.spaceport_ships.delete_one({"id": spaceport_ship_obj.id})
    
    # Create fleet
    fleet = Fleet(
        user_id=current_user.id,
        name=fleet_data.fleet_name,
        position=planet_obj.position,
        ships=fleet_ships,
        fleet_speed=slowest_speed
    )
    
    await db.fleets.insert_one(fleet.dict())
    
    return {
        "message": f"Flotte '{fleet_data.fleet_name}' erstellt",
        "fleet": fleet.dict()
    }

@api_router.get("/game/fleets", response_model=List[Fleet])
async def get_user_fleets(current_user: User = Depends(get_current_user)):
    """Get user's fleets"""
    fleets = await db.fleets.find({"user_id": current_user.id}).to_list(100)
    return [Fleet(**fleet) for fleet in fleets]

@api_router.post("/game/move-fleet")
async def move_fleet(move_data: MoveFleet, current_user: User = Depends(get_current_user)):
    """Move fleet to target position"""
    fleet = await db.fleets.find_one({"id": move_data.fleet_id, "user_id": current_user.id})
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")
    
    fleet_obj = Fleet(**fleet)
    
    # Calculate movement time
    dx = abs(move_data.target_position.x - fleet_obj.position.x)
    dy = abs(move_data.target_position.y - fleet_obj.position.y)
    distance = max(dx, dy)  # Grid distance
    
    # Calculate time based on fleet speed (pc per tick)
    movement_points_needed = distance * MOVEMENT_POINTS_NORMAL
    ticks_needed = max(1, movement_points_needed // fleet_obj.fleet_speed)
    
    movement_start_time = datetime.utcnow()
    movement_end_time = movement_start_time + timedelta(seconds=ticks_needed * TICK_DURATION)
    
    # Update fleet
    await db.fleets.update_one(
        {"id": move_data.fleet_id},
        {"$set": {
            "target_position": move_data.target_position.dict(),
            "movement_start_time": movement_start_time,
            "movement_end_time": movement_end_time
        }}
    )
    
    return {
        "message": "Fleet movement started",
        "arrival_time": movement_end_time.isoformat(),
        "ticks_needed": ticks_needed
    }

# --- COMBAT SYSTEM ROUTES ---
@api_router.post("/game/fleet/stance")
async def set_fleet_stance(stance_data: SetFleetStance, current_user: User = Depends(get_current_user)):
    """Set fleet stance (defensive or aggressive)"""
    if stance_data.stance not in ["defensive", "aggressive"]:
        raise HTTPException(status_code=400, detail="Invalid stance. Use 'defensive' or 'aggressive'")
    
    fleet = await db.fleets.find_one({"id": stance_data.fleet_id, "user_id": current_user.id})
    if not fleet:
        raise HTTPException(status_code=404, detail="Fleet not found")
    
    await db.fleets.update_one(
        {"id": stance_data.fleet_id},
        {"$set": {"stance": stance_data.stance}}
    )
    
    return {
        "message": f"Fleet stance set to {stance_data.stance}",
        "fleet_id": stance_data.fleet_id,
        "stance": stance_data.stance
    }

@api_router.get("/game/battle-reports")
async def get_battle_reports(current_user: User = Depends(get_current_user)):
    """Get battle reports involving the user"""
    reports = await db.battle_reports.find({
        "$or": [
            {"attacker_user_id": current_user.id},
            {"defender_user_id": current_user.id}
        ]
    }).sort("created_at", -1).to_list(50)
    
    # Add design names to ship lists
    result = []
    for report in reports:
        report_data = report.copy()
        report_data.pop("_id", None)
        
        # Enrich with design names
        for key in ["attacker_ships_before", "attacker_ships_lost", "defender_ships_before", "defender_ships_lost"]:
            enriched_ships = []
            for ship in report_data.get(key, []):
                design = await db.ship_designs.find_one({"id": ship["design_id"]})
                ship_info = ship.copy()
                ship_info["design_name"] = design["name"] if design else "Unbekannt"
                enriched_ships.append(ship_info)
            report_data[key] = enriched_ships
        
        result.append(report_data)
    
    return result

@api_router.get("/game/debris-fields")
async def get_debris_fields(current_user: User = Depends(get_current_user)):
    """Get all debris fields in the universe"""
    debris = await db.debris_fields.find({}).to_list(1000)
    return [{"id": d["id"], "position": d["position"], "resource_type": d["resource_type"], "amount": d["amount"]} for d in debris]

@api_router.post("/game/collect-debris")
async def collect_debris(debris_id: str, current_user: User = Depends(get_current_user)):
    """Collect debris with a fleet at the same position"""
    debris = await db.debris_fields.find_one({"id": debris_id})
    if not debris:
        raise HTTPException(status_code=404, detail="Debris field not found")
    
    # Check if user has a fleet at this position
    fleet = await db.fleets.find_one({
        "user_id": current_user.id,
        "position.x": debris["position"]["x"],
        "position.y": debris["position"]["y"],
        "movement_end_time": None
    })
    
    if not fleet:
        raise HTTPException(status_code=400, detail="No stationary fleet at debris position")
    
    # Add resources to user's first planet
    user_planet = await db.planets.find_one({"owner_id": current_user.id})
    if not user_planet:
        raise HTTPException(status_code=400, detail="No planet to store resources")
    
    resource_type = debris["resource_type"]
    amount = debris["amount"]
    
    await db.planets.update_one(
        {"id": user_planet["id"]},
        {"$inc": {f"resources.{resource_type}": amount}}
    )
    
    # Remove debris field
    await db.debris_fields.delete_one({"id": debris_id})
    
    return {
        "message": f"Collected {amount} {resource_type} from debris",
        "resource_type": resource_type,
        "amount": amount
    }

@api_router.get("/game/rankings")
async def get_rankings():
    # Fetch all counts in 2 aggregations instead of 2×N single queries (Punkt 6)
    users = await db.users.find().sort("points", -1).to_list(MAX_PLAYERS)

    user_ids = [u["id"] for u in users]

    planet_pipeline = [
        {"$match": {"owner_id": {"$in": user_ids}}},
        {"$group": {"_id": "$owner_id", "count": {"$sum": 1}}}
    ]
    fleet_pipeline = [
        {"$match": {"user_id": {"$in": user_ids}}},
        {"$group": {"_id": "$user_id", "count": {"$sum": 1}}}
    ]

    planet_counts = {doc["_id"]: doc["count"] async for doc in db.planets.aggregate(planet_pipeline)}
    fleet_counts  = {doc["_id"]: doc["count"] async for doc in db.fleets.aggregate(fleet_pipeline)}

    return [
        {
            "rank": i + 1,
            "username": user["username"],
            "points": user.get("points", 0),
            "planets": planet_counts.get(user["id"], 0),
            "fleets":  fleet_counts.get(user["id"], 0),
        }
        for i, user in enumerate(users)
    ]

# --- BUILDING HELPER FUNCTIONS ---
async def init_user_buildings(user_id: str) -> UserBuildings:
    """Initialize buildings for a new user"""
    buildings = []
    for building_type in BUILDING_TYPES.keys():
        buildings.append(BuildingLevel(building_type=building_type, level=0))
    
    user_buildings = UserBuildings(user_id=user_id, buildings=buildings)
    await db.user_buildings.insert_one(user_buildings.dict())
    return user_buildings

def calculate_building_cost(building_type: str, current_level: int) -> int:
    """Calculate metal cost for upgrading a building"""
    building = BUILDING_TYPES[building_type]
    base_cost = building["base_cost"]
    increase = building["cost_increase_percent"] / 100
    # Cost for level N = base_cost * (1 + increase)^N
    return int(base_cost * ((1 + increase) ** current_level))

def calculate_building_time(building_type: str, current_level: int) -> int:
    """Calculate build time in ticks for upgrading a building"""
    building = BUILDING_TYPES[building_type]
    base_time = building["base_build_time_ticks"]
    increase = building["build_time_increase_percent"] / 100
    # Time for level N = base_time * (1 + increase)^N
    return int(base_time * ((1 + increase) ** current_level))

def get_building_bonus(building_type: str, level: int) -> dict:
    """Get the bonus provided by a building at a specific level"""
    building = BUILDING_TYPES[building_type]
    bonus = {"type": building_type, "level": level}
    
    if "resource_bonus_per_level" in building:
        bonus["resource_per_tick"] = building["resource_bonus_per_level"] * level
        bonus["resource_type"] = building["resource_type"]
    
    if "prototype_slots_per_level" in building:
        bonus["prototype_slots"] = building["prototype_slots_per_level"] * level
    
    if "fleet_slots_per_level" in building:
        bonus["fleet_slots"] = building["fleet_slots_per_level"] * level
    
    if "research_time_reduction_percent" in building:
        # Cumulative reduction: 1 - (1 - 0.13)^level
        reduction = 1 - ((1 - building["research_time_reduction_percent"] / 100) ** level)
        bonus["research_time_reduction"] = round(reduction * 100, 1)
    
    return bonus

# --- BUILDING ROUTES ---
@api_router.get("/game/buildings")
async def get_user_buildings(current_user: User = Depends(get_current_user)):
    """Get user's building levels and bonuses"""
    buildings = await db.user_buildings.find_one({"user_id": current_user.id})
    if not buildings:
        user_buildings = await init_user_buildings(current_user.id)
    else:
        user_buildings = UserBuildings(**buildings)
    
    # Calculate bonuses and upgrade info for each building
    result = []
    for building in user_buildings.buildings:
        building_info = BUILDING_TYPES[building.building_type]
        upgrade_cost = calculate_building_cost(building.building_type, building.level)
        upgrade_time = calculate_building_time(building.building_type, building.level)
        bonus = get_building_bonus(building.building_type, building.level)
        
        result.append({
            "building_type": building.building_type,
            "name": building_info["name"],
            "description": building_info["description"],
            "category": building_info["category"],
            "level": building.level,
            "upgrading": building.upgrading,
            "upgrade_end_time": building.upgrade_end_time.isoformat() if building.upgrade_end_time else None,
            "upgrade_cost_metal": upgrade_cost,
            "upgrade_time_ticks": upgrade_time,
            "current_bonus": bonus
        })
    
    return result

@api_router.post("/game/buildings/upgrade")
async def upgrade_building(upgrade_data: UpgradeBuilding, current_user: User = Depends(get_current_user)):
    """Start upgrading a building"""
    if upgrade_data.building_type not in BUILDING_TYPES:
        raise HTTPException(status_code=400, detail="Invalid building type")
    
    # Get user's buildings
    buildings_data = await db.user_buildings.find_one({"user_id": current_user.id})
    if not buildings_data:
        user_buildings = await init_user_buildings(current_user.id)
    else:
        user_buildings = UserBuildings(**buildings_data)
    
    # Find the building
    target_building = None
    building_index = -1
    for i, b in enumerate(user_buildings.buildings):
        if b.building_type == upgrade_data.building_type:
            target_building = b
            building_index = i
            break
    
    if not target_building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    # Check if this specific building is already upgrading
    if target_building.upgrading:
        raise HTTPException(status_code=400, detail="Dieses Gebäude wird bereits ausgebaut")
    
    # Calculate cost
    upgrade_cost = calculate_building_cost(upgrade_data.building_type, target_building.level)
    
    # Check user's total metal resources
    user_planets = await db.planets.find({"owner_id": current_user.id}).to_list(100)
    total_metal = sum(planet["resources"]["metal"] for planet in user_planets)
    
    if total_metal < upgrade_cost:
        raise HTTPException(status_code=400, detail=f"Insufficient metal. Need {upgrade_cost}, have {total_metal}")
    
    # Deduct metal costs proportionally from planets
    remaining_cost = upgrade_cost
    for planet in user_planets:
        if remaining_cost <= 0:
            break
        planet_metal = planet["resources"]["metal"]
        if planet_metal > 0:
            deduction = min(planet_metal, remaining_cost)
            await db.planets.update_one(
                {"id": planet["id"]},
                {"$inc": {"resources.metal": -deduction}}
            )
            remaining_cost -= deduction
    
    # Calculate upgrade time
    config = await get_game_config()
    upgrade_time_ticks = calculate_building_time(upgrade_data.building_type, target_building.level)
    upgrade_time_seconds = upgrade_time_ticks * config.tick_duration
    
    upgrade_start = datetime.utcnow()
    upgrade_end = upgrade_start + timedelta(seconds=upgrade_time_seconds)
    
    # Update building status
    user_buildings.buildings[building_index].upgrading = True
    user_buildings.buildings[building_index].upgrade_start_time = upgrade_start
    user_buildings.buildings[building_index].upgrade_end_time = upgrade_end
    
    await db.user_buildings.update_one(
        {"user_id": current_user.id},
        {"$set": {"buildings": [b.dict() for b in user_buildings.buildings]}}
    )
    
    return {
        "message": f"Upgrade started for {BUILDING_TYPES[upgrade_data.building_type]['name']}",
        "cost": upgrade_cost,
        "completion_time": upgrade_end.isoformat(),
        "duration_ticks": upgrade_time_ticks
    }

@api_router.get("/game/building-types")
async def get_building_types():
    """Get all available building types and their stats"""
    return BUILDING_TYPES

# --- RESEARCH ROUTES ---
@api_router.get("/game/research", response_model=UserResearch)
async def get_user_research(current_user: User = Depends(get_current_user)):
    """Get user's research levels"""
    research = await db.user_research.find_one({"user_id": current_user.id})
    if not research:
        research = await init_user_research(current_user.id)
        return research
    return UserResearch(**research)

@api_router.post("/game/research/start")
async def start_research(research_data: StartResearch, current_user: User = Depends(get_current_user)):
    """Start researching a technology"""
    # Get user's research data
    research = await db.user_research.find_one({"user_id": current_user.id})
    if not research:
        research = await init_user_research(current_user.id)
        research_obj = research
    else:
        research_obj = UserResearch(**research)
    
    # Find the specific technology
    tech_research = None
    for level in research_obj.research_levels:
        if level.category == research_data.category and level.technology == research_data.technology:
            tech_research = level
            break
    
    if not tech_research:
        raise HTTPException(status_code=404, detail="Technology not found")
    
    # Check if already researching
    if tech_research.researching:
        raise HTTPException(status_code=400, detail="Technology is already being researched")
    
    # Check if user has any active research
    for level in research_obj.research_levels:
        if level.researching:
            raise HTTPException(status_code=400, detail="You can only research one technology at a time")
    
    # Get research costs and validate resources
    tech_costs = RESEARCH_BASE_COSTS[research_data.category][research_data.technology]
    actual_cost = calculate_research_cost(tech_costs["base_cost"], tech_research.level)
    base_research_time = calculate_research_time(tech_costs["base_time_hours"], tech_research.level)
    
    # Apply Forschungslabor bonus (-13% per level)
    user_buildings_data = await db.user_buildings.find_one({"user_id": current_user.id})
    lab_level = 0
    if user_buildings_data:
        user_buildings = UserBuildings(**user_buildings_data)
        for building in user_buildings.buildings:
            if building.building_type == "forschungslabor":
                lab_level = building.level
                break
    
    # Calculate reduced research time
    research_time_reduction = 1 - ((1 - 0.13) ** lab_level)  # -13% per level compound
    research_time = base_research_time * (1 - research_time_reduction)
    
    # Check user's total food resources
    user_planets = await db.planets.find({"owner_id": current_user.id}).to_list(100)
    total_food = sum(planet["resources"]["food"] for planet in user_planets)
    
    if total_food < actual_cost:
        raise HTTPException(status_code=400, detail=f"Insufficient food. Need {actual_cost}, have {total_food}")
    
    # Deduct food costs proportionally from planets
    remaining_cost = actual_cost
    for planet in user_planets:
        if remaining_cost <= 0:
            break
        
        planet_food = planet["resources"]["food"]
        if planet_food > 0:
            deduction = min(planet_food, remaining_cost)
            await db.planets.update_one(
                {"id": planet["id"]},
                {"$inc": {"resources.food": -deduction}}
            )
            remaining_cost -= deduction
    
    # Start research
    research_start = datetime.utcnow()
    research_end = research_start + timedelta(hours=research_time)
    
    # Update research status
    for i, level in enumerate(research_obj.research_levels):
        if level.category == research_data.category and level.technology == research_data.technology:
            research_obj.research_levels[i].researching = True
            research_obj.research_levels[i].research_start_time = research_start
            research_obj.research_levels[i].research_end_time = research_end
            break
    
    # Save to database
    await db.user_research.update_one(
        {"user_id": current_user.id},
        {"$set": research_obj.dict()}
    )
    
    return {
        "message": f"Research started for {research_data.technology}",
        "cost": actual_cost,
        "completion_time": research_end.isoformat(),
        "duration_hours": research_time
    }

@api_router.get("/game/research/costs")
async def get_research_costs():
    """Get research base costs and times"""
    return RESEARCH_BASE_COSTS

@api_router.post("/game/tick")
async def manual_tick():
    """Manual tick processing"""
    await process_tick()
    return {"message": "Tick processed successfully"}

# Global variable to track automatic tick task
automatic_tick_task = None

async def automatic_tick_system():
    """Automatic tick processing system"""
    while True:
        try:
            config = await get_game_config()
            tick_duration = config.tick_duration
            
            # Wait for the tick duration
            await asyncio.sleep(tick_duration)
            
            # Process the tick
            await process_tick()
            print(f"[TICK] Automatic tick processed at {datetime.utcnow()}")
            
        except Exception as e:
            print(f"[ERROR] Automatic tick failed: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry

async def start_automatic_tick_system():
    """Start the automatic tick system"""
    global automatic_tick_task
    if automatic_tick_task is None or automatic_tick_task.done():
        automatic_tick_task = asyncio.create_task(automatic_tick_system())
        print("[TICK] Automatic tick system started")

async def stop_automatic_tick_system():
    """Stop the automatic tick system"""
    global automatic_tick_task
    if automatic_tick_task:
        automatic_tick_task.cancel()
        automatic_tick_task = None
        print("[TICK] Automatic tick system stopped")

# Include router
app.include_router(api_router)

# CORS – Punkt 3: auf eigene Domain beschränken, Wildcard nur als Fallback
_replit_domain = os.environ.get('REPLIT_DEV_DOMAIN', '')
_cors_origins_env = os.environ.get('CORS_ORIGINS', '')
if _cors_origins_env:
    _allowed_origins = _cors_origins_env.split(',')
elif _replit_domain:
    _allowed_origins = [
        f"https://{_replit_domain}",
        "http://localhost:5000",
        "http://0.0.0.0:5000",
    ]
else:
    _allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    # --- Punkt 5: MongoDB-Indizes anlegen ---
    await db.users.create_index("id", unique=True)
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email")
    await db.planets.create_index("id", unique=True)
    await db.planets.create_index("owner_id")
    await db.planets.create_index([("position.x", 1), ("position.y", 1)])
    await db.fleets.create_index("id", unique=True)
    await db.fleets.create_index("user_id")
    await db.fleets.create_index([("position.x", 1), ("position.y", 1)])
    await db.fleets.create_index("movement_end_time")
    await db.ship_designs.create_index("id", unique=True)
    await db.ship_designs.create_index("user_id")
    await db.user_buildings.create_index("user_id", unique=True)
    await db.user_research.create_index("user_id", unique=True)
    await db.spaceport_ships.create_index("user_id")
    await db.invite_codes.create_index("code", unique=True)
    await db.battle_reports.create_index([("attacker_user_id", 1), ("created_at", -1)])
    await db.battle_reports.create_index([("defender_user_id", 1), ("created_at", -1)])
    logger.info("MongoDB indexes created")

    await init_game_state()
    logger.info("TheCreation Authentic Game Engine started!")
    
    # Force universe generation if no planets exist
    planet_count = await db.planets.count_documents({})
    logger.info(f"Found {planet_count} planets in database")
    if planet_count == 0:
        logger.info("Generating universe with planets...")
        await generate_universe()
        final_count = await db.planets.count_documents({})
        logger.info(f"Generated {final_count} planets")
    
    # Initialize game config
    config = await init_game_config()
    logger.info(f"Game config: {config.max_players} max players, {config.universe_size}x{config.universe_size} universe")
    
    # Start automatic tick system
    await start_automatic_tick_system()
    logger.info(f"Automatic tick system started with {config.tick_duration}s interval")

@app.on_event("shutdown")
async def shutdown_db_client():
    await stop_automatic_tick_system()
    client.close()
    logger.info("TheCreation server shutdown complete")