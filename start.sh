#!/bin/bash

# Start MongoDB in background
mkdir -p /tmp/mongodb-data
mongod --dbpath /tmp/mongodb-data --port 27017 --bind_ip 127.0.0.1 --logpath /tmp/mongodb.log --fork
echo "MongoDB started"

# Start backend in background
cd /home/runner/workspace/backend
MONGO_URL=mongodb://localhost:27017 DB_NAME=thecreation_authentic uvicorn server:app --host localhost --port 8000 &
echo "Backend started on port 8000"

# Start frontend
cd /home/runner/workspace/frontend
HOST=0.0.0.0 PORT=5000 DANGEROUSLY_DISABLE_HOST_CHECK=true REACT_APP_BACKEND_URL=https://$REPLIT_DEV_DOMAIN node_modules/.bin/craco start
