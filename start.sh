#!/bin/bash

MONGO_DATA_DIR="/home/runner/workspace/data/mongodb"
mkdir -p "$MONGO_DATA_DIR"
if pgrep -x mongod >/dev/null; then
  echo "MongoDB already running"
else
  mongod --dbpath "$MONGO_DATA_DIR" --port 27017 --bind_ip 127.0.0.1 --logpath /tmp/mongodb.log --fork
  echo "MongoDB started (persistent data: $MONGO_DATA_DIR)"
fi

cd /home/runner/workspace/backend
uv run --project /home/runner/workspace uvicorn server:app --host localhost --port 8000 &
echo "Backend started on port 8000"

cd /home/runner/workspace/frontend
HOST=0.0.0.0 PORT=5000 DANGEROUSLY_DISABLE_HOST_CHECK=true REACT_APP_BACKEND_URL=https://$REPLIT_DEV_DOMAIN node_modules/.bin/craco start
