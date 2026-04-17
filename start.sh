#!/bin/bash

# Start MongoDB with persistent data directory
MONGO_DATA_DIR="/home/runner/workspace/data/mongodb"
mkdir -p "$MONGO_DATA_DIR"
mongod --dbpath "$MONGO_DATA_DIR" --port 27017 --bind_ip 127.0.0.1 --logpath /tmp/mongodb.log --fork
echo "MongoDB started (persistent data: $MONGO_DATA_DIR)"

# Start backend in background
cd /home/runner/workspace/backend
uvicorn server:app --host localhost --port 8000 &
echo "Backend started on port 8000"

# Start frontend
cd /home/runner/workspace/frontend
HOST=0.0.0.0 PORT=5000 DANGEROUSLY_DISABLE_HOST_CHECK=true REACT_APP_BACKEND_URL=https://$REPLIT_DEV_DOMAIN node_modules/.bin/craco start
