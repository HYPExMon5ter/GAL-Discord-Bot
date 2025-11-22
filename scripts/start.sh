#!/bin/sh

# Start the API server in background
echo "Starting FastAPI server on port 8000..."
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for API to be ready
echo "Waiting for API to start..."
for i in $(seq 1 30); do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "API is ready! (attempt $i/30)"
        break
    fi
    echo "Attempt $i/30: API not ready yet"
    sleep 2
done

# Check if API is actually running
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: API failed to start properly"
    exit 1
fi

# Start the bot
echo "Starting Discord bot..."
exec python bot.py
