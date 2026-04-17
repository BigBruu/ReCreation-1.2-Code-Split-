# TheCreation Authentic - Space Strategy Game

## Overview
A multiplayer web-based space strategy game (4X style) where players manage planets, build structures, research technologies, design custom ships, and engage in fleet combat in a persistent, tick-based universe.

## Architecture

### Backend (FastAPI + Python)
- **Framework**: FastAPI with async support
- **Database**: MongoDB (via motor async driver)
- **Auth**: JWT tokens with bcrypt password hashing
- **Port**: 8000 (localhost only)
- **Entry**: `backend/server.py`

### Frontend (React + Tailwind)
- **Framework**: React 19 with Create React App + CRACO override
- **Styling**: Tailwind CSS + Radix UI + Shadcn components
- **Routing**: react-router-dom
- **Port**: 5000 (0.0.0.0 for Replit proxy)
- **Entry**: `frontend/src/App.js`
- **API Routing**: React dev server proxies `/api` requests to `http://localhost:8000` to keep backend traffic private while exposing only the frontend webview.

## Game Features
- 47x47 universe grid with 7x7 Observatory view
- Resources: Food, Metal, Hydrogen
- Buildings: Plantage (food), Erzmine (metal), Elektrolysator (hydrogen), Shipyard, Spaceport, Research Lab
- Tick-based progression (60 seconds per tick)
- Up to 20 players

## Environment Variables
- `MONGO_URL`: MongoDB connection string (mongodb://localhost:27017)
- `DB_NAME`: Database name (thecreation_authentic)
- `REACT_APP_BACKEND_URL`: Backend URL used by frontend API calls during development
- `SECRET_KEY`: JWT signing key
- `ADMIN_PASSWORD`: Admin panel password
- `CORS_ORIGINS`: Optional comma-separated list to override CORS allowed origins

## Optimierungen (umgesetzt)
1. SECRET_KEY aus Umgebungsvariable (nicht hardcodiert)
2. Admin-Passwort aus Umgebungsvariable
3. CORS auf eigene Replit-Domain beschränkt
4. MongoDB persistentes Datenverzeichnis: `/home/runner/workspace/data/mongodb`
5. MongoDB-Indizes für alle häufig abgefragten Felder (user_id, id, owner_id, position)
6. N+1-Abfragen in Rankings und User-Liste durch MongoDB-Aggregation ersetzt
7. get_game_config() mit 10-Sekunden In-Memory-Cache

## Startup
The `start.sh` script:
1. Starts MongoDB on port 27017 if it is not already running (persistent data in /home/runner/workspace/data/mongodb)
2. Starts FastAPI backend on localhost port 8000 through `uv run`
3. Starts React frontend on port 5000

## Package Management
- Python packages: uv (`pyproject.toml` / `uv.lock`)
- Node packages: yarn (`frontend/package.json` / `frontend/yarn.lock`)

## Key Files
- `backend/server.py` - All backend API routes and game logic
- `frontend/src/components/game/GameInterface.js` - Main game UI
- `frontend/src/context/AuthContext.js` - Auth state management
- `frontend/package.json` - Frontend dependencies and `/api` proxy configuration
- `start.sh` - Unified startup script
