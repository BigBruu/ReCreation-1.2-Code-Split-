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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Security
SECRET_KEY = "thecreation-secret-key-mvp-2025"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 24 * 60  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app
app = FastAPI(title="TheCreation MVP", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Game Constants
FIELD_SIZE = 47
FIELD_POINTS_NORMAL = 6000
FIELD_POINTS_DIAGONAL = 7200
MAX_PLAYERS = 20
RESOURCES_PER_TICK = 5
TICK_DURATION = 60  # seconds

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
    colonies_count: int = 0
    ships_count: int = 0

# --- GAME MODELS ---
class Resources(BaseModel):
    food: int = 0
    metal: int = 0
    silicon: int = 0
    hydrogen: int = 0

class Position(BaseModel):
    x: int
    y: int

class Colony(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    position: Position
    name: str
    resources: Resources = Field(default_factory=Resources)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    production_level: int = 1

class Ship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    ship_type: str  # "scout", "fighter", "colonizer"
    position: Position
    name: str
    health: int = 100
    attack: int = 10
    defense: int = 10
    speed: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GameState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    current_tick: int = 0
    last_tick_time: datetime = Field(default_factory=datetime.utcnow)
    active_players: int = 0
    game_started: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MoveShip(BaseModel):
    ship_id: str
    target_position: Position

class CreateColony(BaseModel):
    position: Position
    name: str

class CreateShip(BaseModel):
    colony_id: str
    ship_type: str
    name: str

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

# --- GAME FUNCTIONS ---
def calculate_movement_cost(from_pos: Position, to_pos: Position) -> int:
    """Calculate movement cost between two positions"""
    dx = abs(to_pos.x - from_pos.x)
    dy = abs(to_pos.y - from_pos.y)
    
    # Diagonal movement costs more
    if dx > 0 and dy > 0:
        return FIELD_POINTS_DIAGONAL
    else:
        return FIELD_POINTS_NORMAL

def is_valid_position(pos: Position) -> bool:
    """Check if position is within game bounds"""
    return 0 <= pos.x < FIELD_SIZE and 0 <= pos.y < FIELD_SIZE

async def init_game_state():
    """Initialize game state if not exists"""
    existing_state = await db.game_state.find_one()
    if not existing_state:
        game_state = GameState()
        await db.game_state.insert_one(game_state.dict())
        return game_state
    return GameState(**existing_state)

async def process_tick():
    """Process game tick - resource production"""
    # Update all colonies
    colonies = await db.colonies.find().to_list(1000)
    for colony_data in colonies:
        colony = Colony(**colony_data)
        # Add resources per tick
        colony.resources.food += RESOURCES_PER_TICK * colony.production_level
        colony.resources.metal += RESOURCES_PER_TICK * colony.production_level
        colony.resources.silicon += RESOURCES_PER_TICK * colony.production_level
        colony.resources.hydrogen += RESOURCES_PER_TICK * colony.production_level
        
        await db.colonies.update_one(
            {"id": colony.id},
            {"$set": colony.dict()}
        )
    
    # Update game state
    await db.game_state.update_one(
        {},
        {"$inc": {"current_tick": 1}, "$set": {"last_tick_time": datetime.utcnow()}}
    )

# --- AUTH ROUTES ---
@api_router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"$or": [{"username": user_data.username}, {"email": user_data.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Check max players
    player_count = await db.users.count_documents({})
    if player_count >= MAX_PLAYERS:
        raise HTTPException(status_code=400, detail=f"Maximum {MAX_PLAYERS} players reached")
    
    # Create user
    hashed_password = pwd_context.hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password
    )
    
    await db.users.insert_one(user.dict())
    
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
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@api_router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- GAME ROUTES ---
@api_router.get("/game/state")
async def get_game_state():
    game_state = await init_game_state()
    return game_state

@api_router.get("/game/field")
async def get_game_field():
    """Get complete game field with all colonies and ships"""
    colonies = await db.colonies.find().to_list(1000)
    ships = await db.ships.find().to_list(1000)
    
    # Create field grid
    field = {}
    for x in range(FIELD_SIZE):
        for y in range(FIELD_SIZE):
            field[f"{x},{y}"] = {
                "position": {"x": x, "y": y},
                "colonies": [],
                "ships": []
            }
    
    # Add colonies to field
    for colony_data in colonies:
        colony = Colony(**colony_data)
        key = f"{colony.position.x},{colony.position.y}"
        if key in field:
            user = await db.users.find_one({"id": colony.user_id})
            field[key]["colonies"].append({
                **colony.dict(),
                "username": user["username"] if user else "Unknown"
            })
    
    # Add ships to field
    for ship_data in ships:
        ship = Ship(**ship_data)
        key = f"{ship.position.x},{ship.position.y}"
        if key in field:
            user = await db.users.find_one({"id": ship.user_id})
            field[key]["ships"].append({
                **ship.dict(),
                "username": user["username"] if user else "Unknown"
            })
    
    return {"field": field, "size": FIELD_SIZE}

@api_router.post("/game/colony", response_model=Colony)
async def create_colony(colony_data: CreateColony, current_user: User = Depends(get_current_user)):
    if not is_valid_position(colony_data.position):
        raise HTTPException(status_code=400, detail="Invalid position")
    
    # Check if position is occupied
    existing_colony = await db.colonies.find_one({
        "position.x": colony_data.position.x,
        "position.y": colony_data.position.y
    })
    if existing_colony:
        raise HTTPException(status_code=400, detail="Position already occupied")
    
    colony = Colony(
        user_id=current_user.id,
        position=colony_data.position,
        name=colony_data.name
    )
    
    await db.colonies.insert_one(colony.dict())
    
    # Update user stats
    await db.users.update_one(
        {"id": current_user.id},
        {"$inc": {"colonies_count": 1, "points": 100}}
    )
    
    return colony

@api_router.get("/game/colonies", response_model=List[Colony])
async def get_my_colonies(current_user: User = Depends(get_current_user)):
    colonies = await db.colonies.find({"user_id": current_user.id}).to_list(100)
    return [Colony(**colony) for colony in colonies]

@api_router.post("/game/ship", response_model=Ship)
async def create_ship(ship_data: CreateShip, current_user: User = Depends(get_current_user)):
    # Check if colony exists and belongs to user
    colony = await db.colonies.find_one({"id": ship_data.colony_id, "user_id": current_user.id})
    if not colony:
        raise HTTPException(status_code=404, detail="Colony not found")
    
    # Ship costs (simplified)
    costs = {
        "scout": {"metal": 100, "silicon": 50},
        "fighter": {"metal": 200, "silicon": 100, "hydrogen": 50},
        "colonizer": {"metal": 500, "silicon": 250, "food": 200}
    }
    
    if ship_data.ship_type not in costs:
        raise HTTPException(status_code=400, detail="Invalid ship type")
    
    # Check if colony has enough resources
    colony_obj = Colony(**colony)
    ship_cost = costs[ship_data.ship_type]
    
    if (colony_obj.resources.metal < ship_cost.get("metal", 0) or
        colony_obj.resources.silicon < ship_cost.get("silicon", 0) or
        colony_obj.resources.food < ship_cost.get("food", 0) or
        colony_obj.resources.hydrogen < ship_cost.get("hydrogen", 0)):
        raise HTTPException(status_code=400, detail="Insufficient resources")
    
    # Deduct resources
    colony_obj.resources.metal -= ship_cost.get("metal", 0)
    colony_obj.resources.silicon -= ship_cost.get("silicon", 0)
    colony_obj.resources.food -= ship_cost.get("food", 0)
    colony_obj.resources.hydrogen -= ship_cost.get("hydrogen", 0)
    
    await db.colonies.update_one(
        {"id": ship_data.colony_id},
        {"$set": colony_obj.dict()}
    )
    
    # Create ship with different stats
    ship_stats = {
        "scout": {"health": 50, "attack": 5, "defense": 5, "speed": 3},
        "fighter": {"health": 100, "attack": 20, "defense": 15, "speed": 2},
        "colonizer": {"health": 80, "attack": 0, "defense": 10, "speed": 1}
    }
    
    stats = ship_stats[ship_data.ship_type]
    ship = Ship(
        user_id=current_user.id,
        ship_type=ship_data.ship_type,
        position=colony_obj.position,
        name=ship_data.name,
        **stats
    )
    
    await db.ships.insert_one(ship.dict())
    
    # Update user stats
    await db.users.update_one(
        {"id": current_user.id},
        {"$inc": {"ships_count": 1, "points": 50}}
    )
    
    return ship

@api_router.get("/game/ships", response_model=List[Ship])
async def get_my_ships(current_user: User = Depends(get_current_user)):
    ships = await db.ships.find({"user_id": current_user.id}).to_list(100)
    return [Ship(**ship) for ship in ships]

@api_router.post("/game/move")
async def move_ship(move_data: MoveShip, current_user: User = Depends(get_current_user)):
    # Check if ship belongs to user
    ship = await db.ships.find_one({"id": move_data.ship_id, "user_id": current_user.id})
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")
    
    ship_obj = Ship(**ship)
    
    if not is_valid_position(move_data.target_position):
        raise HTTPException(status_code=400, detail="Invalid target position")
    
    # Calculate movement cost (simplified - just check if adjacent)
    dx = abs(move_data.target_position.x - ship_obj.position.x)
    dy = abs(move_data.target_position.y - ship_obj.position.y)
    
    if dx > ship_obj.speed or dy > ship_obj.speed:
        raise HTTPException(status_code=400, detail="Target too far for this ship")
    
    # Update ship position
    await db.ships.update_one(
        {"id": move_data.ship_id},
        {"$set": {"position": move_data.target_position.dict()}}
    )
    
    return {"message": "Ship moved successfully"}

@api_router.get("/game/rankings")
async def get_rankings():
    users = await db.users.find().sort("points", -1).to_list(MAX_PLAYERS)
    rankings = []
    for i, user in enumerate(users):
        rankings.append({
            "rank": i + 1,
            "username": user["username"],
            "points": user["points"],
            "colonies": user["colonies_count"],
            "ships": user["ships_count"]
        })
    return rankings

@api_router.post("/game/tick")
async def manual_tick():
    """Manual tick for testing - in production this would be automatic"""
    await process_tick()
    return {"message": "Tick processed"}

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
    logger.info("TheCreation MVP Game Engine started!")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()