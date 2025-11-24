# Quick Start: Testing SearXNG Integration

## Prerequisites
1. **Docker Desktop must be running**
2. Open Docker Desktop before running these commands

## Start SearXNG

```bash
# From the project root
cd /Users/testnico/Documents/GitHub/pomeloGPT

# Start SearXNG container
docker-compose -f docker-compose.searxng.yml up -d

# Wait a few seconds for it to start, then verify it's running
curl http://localhost:8080/search?q=test&format=json
```

## Test the Service

```bash
# Test the SearXNG service wrapper
cd backend
python api/searxng_service.py

# Test with different time ranges
python test_web_search_freshness.py

# Simple search test
python test_web_search.py
```

## Expected Results

If everything works correctly:
- ✅ SearXNG container starts on port 8080
- ✅ Health check passes
- ✅ Search queries return JSON results
- ✅ Results are scored by freshness

## Restart Your Application

```bash
# Stop current running app (if needed)
# Then start with the updated script
./start.sh
```

The start script will now automatically start SearXNG before starting the backend and frontend!
