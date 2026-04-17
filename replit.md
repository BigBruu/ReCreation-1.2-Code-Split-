# TheCreation Authentic - Space Strategy Game

## Overview
A multiplayer web-based space strategy game (4X style) where players manage planets, build structures, research technologies, design custom ships, and engage in fleet combat in a persistent, tick-based universe.

## Architecture

### Backend (FastAPI + Python)
- **Framework**: FastAPI with async support
- **Database**: MongoDB via Motor async driver
- **Auth**: JWT tokens with bcrypt password hashing; admin login uses protected environment secret validation
- **Port**: 8000 (localhost only)
- **Entry**: `backend/server.py`
- **Supporting modules**:
  - `backend/app_config.py` - required environment configuration, secret validation, CORS origin construction
  - `backend/database.py` - MongoDB client and database binding
  - `backend/security.py` - JWT creation/decoding, password hashing context, admin password comparison
  - `backend/indexes.py` - MongoDB index setup and legacy admin password cleanup
  - `backend/services/spaceport.py` - atomic spaceport planet assignment

### Frontend (React + Tailwind)
- **Framework**: React 19 with Create React App + CRACO override
- **Styling**: Tailwind CSS + Radix UI + Shadcn components
- **Routing**: react-router-dom
- **Port**: 5000 (0.0.0.0 for Replit proxy)
- **Entry**: `frontend/src/App.js`
- **API Routing**: React dev server proxies relative `/api` requests to `http://localhost:8000`, keeping backend traffic private while exposing only the frontend webview.
- **API Config**: `frontend/src/lib/api.js` centralizes API base URL handling.

## Game Features
- 47x47 universe grid with 7x7 Observatory view
- Resources: Food, Metal, Hydrogen
- Buildings: Plantage (food), Erzmine (metal), Elektrolysator (hydrogen), Shipyard, Spaceport, Research Lab
- Tick-based progression
- Up to 20 players by default

## Environment Variables and Secrets
- `MONGO_URL`: MongoDB connection string, default development value is `mongodb://localhost:27017`
- `DB_NAME`: Database name, default development value is `thecreation_authentic`
- `SECRET_KEY`: Required protected secret for JWT signing
- `ADMIN_PASSWORD`: Required protected secret for admin login
- `CORS_ORIGINS`: Optional comma-separated list to override CORS allowed origins
- `REACT_APP_BACKEND_URL`: Optional frontend API base URL override; normally unset in Replit development so relative `/api` proxying is used

## Implemented Safety/Runtime Improvements
1. Server startup now requires `SECRET_KEY` and `ADMIN_PASSWORD` instead of silently using insecure defaults.
2. Admin password is no longer stored in game configuration; existing legacy `admin_password` fields are removed from MongoDB during startup.
3. Admin session state is validated by the backend via `/api/auth/session` instead of trusting `localStorage.isAdmin`.
4. Frontend API paths are centralized and default to relative `/api` proxying.
5. Spaceport assignment is atomic using MongoDB `find_one_and_update`, preventing duplicate planet claims during concurrent registration.
6. Startup script clears stale frontend/backend dev processes, uses `CI=true`, and starts the frontend through `yarn start` to avoid interactive port prompts.
7. Backend has started modularization with separate config, database, security, index, and spaceport service modules.

## Startup
The `start.sh` script:
1. Stops stale FastAPI/React dev processes from previous runs
2. Starts MongoDB on port 27017 if it is not already running, using persistent data in `/home/runner/workspace/data/mongodb`
3. Starts FastAPI backend on localhost port 8000 through `uv run`
4. Starts React frontend on port 5000 through `yarn start`

## Package Management
- Python packages: uv (`pyproject.toml` / `uv.lock`)
- Node packages: yarn (`frontend/package.json` / `frontend/yarn.lock`)

## Key Files
- `backend/server.py` - Main API routes and game logic
- `backend/app_config.py` - Environment and CORS configuration
- `backend/security.py` - Auth/JWT/admin security helpers
- `backend/services/spaceport.py` - Spaceport assignment service
- `frontend/src/components/game/GameInterface.js` - Main game UI
- `frontend/src/context/AuthContext.js` - Auth state management and backend session validation
- `frontend/src/lib/api.js` - Central frontend API configuration
- `frontend/package.json` - Frontend dependencies and `/api` proxy configuration
- `start.sh` - Unified startup script
