"""
Test SearXNG web search functionality
Simple test to verify SearXNG is working correctly
"""

from api.searxng_service import SearXNGService
from datetime import datetime

def test_search():
    # Use local SearXNG instance
    searxng = SearXNGService(base_url="http://localhost:8080")
    
    # Health check
    print("🔍 Testing SearXNG Health...")
    if not searxng.health_check():
        print("❌ SearXNG is not responding at http://localhost:8080")
        print("   Make sure Docker container is running: docker-compose -f docker-compose.searxng.yml up -d")
        return
    print("✓ SearXNG is healthy\n")
    
    # Test search
    query = "price of xrp"
    print(f"🔎 Testing search: '{query}'")
    
    results = searxng.search(query=query, count=5, time_range="day")
    
    if not results:
        print("❌ No results found")
        return
    
    print(f"\n✓ Found {len(results)} results:\n")
    
    for idx, result in enumerate(results, 1):
        print(f"{idx}. {result['name']}")
        print(f"   URL: {result['url']}")
        print(f"   Engine: {result['engine']}")
        print(f"   Summary: {result['summary'][:100]}...")
        print()
    
    # Test freshness scoring
    print("\n📅 Testing freshness scoring...")
    current_date = datetime.now().strftime("%B %d, %Y")
    current_year = datetime.now().year
    
    scored = searxng.score_by_freshness(results, current_date, current_year)
    
    print(f"\nResults sorted by freshness (current: {current_date}):\n")
    for score, result in scored:
        print(f"  Score {score:3d}: {result['name'][:70]}")

if __name__ == "__main__":
    test_search()
