#!/bin/bash

# Script to start PomeloGPT (Frontend + Backend)
# Kills existing processes on ports 8000 and 5173 before starting

echo "🍊 Starting PomeloGPT..."

# Check if Docker is running, and try to start it if not
if ! docker info > /dev/null 2>&1; then
    echo "🔍 Docker is not running. Attempting to start Docker Desktop..."
    
    # Try to start Docker Desktop (macOS)
    if [ -d "/Applications/Docker.app" ]; then
        open -a Docker
        echo "   Waiting for Docker Desktop to start..."
        
        # Wait up to 60 seconds for Docker to be ready
        DOCKER_WAIT=0
        while [ $DOCKER_WAIT -lt 60 ]; do
            if docker info > /dev/null 2>&1; then
                echo "   ✓ Docker Desktop started successfully!"
                break
            fi
            sleep 2
            DOCKER_WAIT=$((DOCKER_WAIT + 2))
        done
        
        # Check if Docker is now running
        if ! docker info > /dev/null 2>&1; then
            echo "   ⚠️  Docker Desktop is taking longer than expected to start."
            echo "   ⚠️  Web search will not be available, but PomeloGPT will work normally."
            echo "   💡 Tip: Restart the application later to enable web search."
            echo ""
            DOCKER_AVAILABLE=false
        else
            DOCKER_AVAILABLE=true
        fi
    else
        echo "   ⚠️  Docker Desktop is not installed."
        echo "   ⚠️  Web search will not be available, but PomeloGPT will work normally."
        echo "   💡 To enable web search, install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        echo ""
        DOCKER_AVAILABLE=false
    fi
else
    echo "✓ Docker is running"
    DOCKER_AVAILABLE=true
fi

# Start SearXNG if Docker is available
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "🔍 Starting SearXNG search engine..."
    if docker ps -a --format '{{.Names}}' | grep -q '^pomelogpt-searxng$'; then
        echo "   Restarting existing SearXNG container..."
        docker restart pomelogpt-searxng > /dev/null 2>&1
    else
        echo "   Starting new SearXNG container..."
        docker-compose -f docker-compose.searxng.yml up -d
    fi

    # Wait for SearXNG to be ready
    echo "   Waiting for SearXNG to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:8080/search?q=test&format=json > /dev/null 2>&1; then
            echo "   ✓ SearXNG is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "   ⚠️  SearXNG took too long to start. Web search may not work."
        fi
        sleep 1
    done
fi

# Kill processes on port 8000 (backend)
echo "Cleaning port 8000 (backend)..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || echo "Port 8000 is already free"

# Kill processes on port 5173 (frontend)
echo "Cleaning port 5173 (frontend)..."
lsof -ti :5173 | xargs kill -9 2>/dev/null || echo "Port 5173 is already free"

# Wait a moment for ports to be released
sleep 1

# Start backend
echo "Starting backend..."
cd backend
python3 main.py &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"

# Wait for backend to be ready
sleep 2

# Start frontend
echo "Starting frontend..."
cd ../front
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "✅ PomeloGPT is running!"
echo "   Backend:  http://localhost:8000"
echo "   Frontend: http://localhost:5173"
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "   SearXNG:  http://localhost:8080 (web search enabled)"
else
    echo "   Web Search: Not available (Docker not running)"
fi
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
if [ "$DOCKER_AVAILABLE" = true ]; then
    trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker stop pomelogpt-searxng 2>/dev/null; exit" INT
else
    trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
fi
wait
