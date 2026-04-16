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

## Game Features
- 47x47 universe grid with 7x7 Observatory view
- Resources: Food, Metal, Hydrogen
- Buildings: Plantage (food), Erzmine (metal), Elektrolysator (hydrogen), Shipyard, Spaceport, Research Lab
- Tick-based progression (60 seconds per tick)
- Up to 20 players

## Environment Variables
- `MONGO_URL`: MongoDB connection string (mongodb://localhost:27017)
- `DB_NAME`: Database name (thecreation_authentic)
- `REACT_APP_BACKEND_URL`: Backend URL for frontend API calls (set to Replit dev domain)

## Startup
The `start.sh` script:
1. Starts MongoDB on port 27017 (with data in /tmp/mongodb-data)
2. Starts FastAPI backend on port 8000
3. Starts React frontend on port 5000

## Package Management
- Python packages: pip (backend/requirements.txt)
- Node packages: yarn (frontend/package.json)

## Key Files
- `backend/server.py` - All backend API routes and game logic
- `frontend/src/components/game/GameInterface.js` - Main game UI
- `frontend/src/context/AuthContext.js` - Auth state management
- `start.sh` - Unified startup script
