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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
SECRET_KEY = "thecreation-authentic-2025"
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

# Planet Types with Authentic Resources
PLANET_TYPES = {
    "green": {
        "color": "green",
        "base_resources": {"food": 50000000, "metal": 30000000, "silicon": 20000000, "hydrogen": 15000000}
    },
    "blue": {
        "color": "blue", 
        "base_resources": {"food": 20000000, "metal": 60000000, "silicon": 40000000, "hydrogen": 25000000}
    },
    "brown": {
        "color": "brown",
        "base_resources": {"food": 15000000, "metal": 25000000, "silicon": 70000000, "hydrogen": 35000000}
    },
    "orange": {
        "color": "orange",
        "base_resources": {"food": 35000000, "metal": 45000000, "silicon": 15000000, "hydrogen": 50000000}
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
        "plasma": {"levels": [1, 2, 3, 4, 5, 6], "attack_base": 50, "weight": 250}
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
    silicon: int = 0
    hydrogen: int = 0

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
    calculated_stats: Dict[str, Any] = Field(default_factory=dict)  # speed, combat_value, build_cost, build_time
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
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    colony_production_per_tick: int = 5
    noob_protection_hours: int = 48
    admin_password: str = "admin2025"
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
    colony_production_per_tick: Optional[int] = None
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

async def get_game_config():
    """Get current game configuration"""
    config = await db.game_config.find_one()
    if not config:
        return await init_game_config()
    return GameConfig(**config)

def generate_invite_code():
    """Generate a random invite code"""
    import string
    import secrets
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))

async def verify_admin_access(password: str):
    """Verify admin password"""
    config = await get_game_config()
    return password == config.admin_password

# --- AUTHENTIC GAME FUNCTIONS ---
def calculate_ship_stats(design: CreateShipDesign) -> Dict[str, Any]:
    """Calculate authentic ship statistics like in the original game"""
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
    
    # Calculate build costs (authentic formulas)
    base_food_cost = 0
    base_metal_cost = (drive_weight + weapon_weight) * design.drive_level * 10
    base_silicon_cost = (shield_weight + weapon_weight) * design.shield_level * 5
    base_hydrogen_cost = weapon_weight * design.weapon_level * 2
    
    # Calculate build time (13 ticks as shown in screenshot)
    build_time_ticks = max(1, total_weight // 100) + design.drive_level + design.shield_level + design.weapon_level
    
    return {
        "speed": speed,
        "combat_value": combat_value,
        "total_weight": total_weight,
        "build_cost": {
            "food": base_food_cost,
            "metal": base_metal_cost,
            "silicon": base_silicon_cost,
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
    
    planets_to_create = []
    planet_names = ["Kepler", "Proxima", "Gliese", "Wolf", "Trappist", "Ross", "Luyten", "Kapteyn", 
                   "Barnard", "Vega", "Altair", "Sirius", "Rigel", "Betelgeuse", "Antares",
                   "Anno1602", "Tanne", "Übern", "Yacu", "Fräse", "Lusankya", "Manticore"]
    
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
        
        planet = {
            "id": str(uuid.uuid4()),
            "position": {"x": x, "y": y},
            "planet_type": planet_type,
            "name": f"{random.choice(planet_names)}{random.randint(1000, 9999)}",
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

async def process_tick():
    """Process authentic game tick"""
    config = await get_game_config()
    
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
    
    code = generate_invite_code()
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
    user_list = []
    for user in users:
        planet_count = await db.planets.count_documents({"owner_id": user["id"]})
        fleet_count = await db.fleets.count_documents({"user_id": user["id"]})
        user_list.append({
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "points": user["points"],
            "planets": planet_count,
            "fleets": fleet_count,
            "created_at": user["created_at"],
            "spaceport_position": user["spaceport_position"]
        })
    
    return user_list

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
    return game_state

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
    """Create a new ship design (Prototyp)"""
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

@api_router.post("/game/build-fleet", response_model=Fleet)
async def build_fleet(build_data: BuildFleet, current_user: User = Depends(get_current_user)):
    """Build ships and create fleet at planet"""
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
    
    # Calculate total build cost
    total_cost = {
        "food": design_obj.calculated_stats["build_cost"]["food"] * build_data.quantity,
        "metal": design_obj.calculated_stats["build_cost"]["metal"] * build_data.quantity,
        "silicon": design_obj.calculated_stats["build_cost"]["silicon"] * build_data.quantity,
        "hydrogen": design_obj.calculated_stats["build_cost"]["hydrogen"] * build_data.quantity
    }
    
    # Check resources
    if (planet_obj.resources.food < total_cost["food"] or
        planet_obj.resources.metal < total_cost["metal"] or
        planet_obj.resources.silicon < total_cost["silicon"] or
        planet_obj.resources.hydrogen < total_cost["hydrogen"]):
        raise HTTPException(status_code=400, detail="Insufficient resources")
    
    # Deduct resources
    await db.planets.update_one(
        {"id": build_data.planet_id},
        {"$inc": {
            "resources.food": -total_cost["food"],
            "resources.metal": -total_cost["metal"],
            "resources.silicon": -total_cost["silicon"],
            "resources.hydrogen": -total_cost["hydrogen"]
        }}
    )
    
    # Create fleet
    fleet = Fleet(
        user_id=current_user.id,
        name=f"{build_data.fleet_name}",
        position=planet_obj.position,
        ships=[{"design_id": build_data.design_id, "quantity": build_data.quantity}],
        fleet_speed=design_obj.calculated_stats["speed"]
    )
    
    await db.fleets.insert_one(fleet.dict())
    return fleet

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

@api_router.get("/game/rankings")
async def get_rankings():
    users = await db.users.find().sort("points", -1).to_list(MAX_PLAYERS)
    rankings = []
    for i, user in enumerate(users):
        planet_count = await db.planets.count_documents({"owner_id": user["id"]})
        fleet_count = await db.fleets.count_documents({"user_id": user["id"]})
        rankings.append({
            "rank": i + 1,
            "username": user["username"],
            "points": user["points"],
            "planets": planet_count,
            "fleets": fleet_count
        })
    return rankings

@api_router.post("/game/tick")
async def manual_tick():
    """Manual tick processing"""
    await process_tick()
    return {"message": "Tick processed successfully"}

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
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
    await init_game_state()
    logger.info("TheCreation Authentic Game Engine started!")
    
    # Force universe generation if no planets exist
    planet_count = await db.planets.count_documents({})
    if planet_count == 0:
        logger.info("Generating universe with planets...")
        await generate_universe()
        logger.info(f"Generated {await db.planets.count_documents({})} planets")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()