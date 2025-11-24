"""
Test SearXNG web search with different time ranges
Tests freshness filtering to ensure most recent results
"""

from api.searxng_service import SearXNGService
from datetime import datetime

def test_freshness():
    # Use local SearXNG instance
    searxng = SearXNGService(base_url="http://localhost:8080")
    
    # Health check
    print("🔍 Checking SearXNG Health...")
    if not searxng.health_check():
        print("❌ SearXNG is not responding at http://localhost:8080")
        print("   Start it with: docker-compose -f docker-compose.searxng.yml up -d")
        return
    print("✓ SearXNG is healthy\n")
    
    query = "current bitcoin price"
    time_ranges = ["day", "week", "month", None]  # None = all time
    
    print(f"🔎 Testing query: '{query}'\n")
    print("=" * 80)
    
    for time_range in time_ranges:
        time_label = time_range if time_range else "all time"
        print(f"\n📅 Time Range: {time_label.upper()}")
        print("-" * 80)
        
        results = searxng.search(query=query, count=3, time_range=time_range)
        
        if not results:
            print("   No results found")
            continue
        
        # Score by freshness
        current_date = datetime.now().strftime("%B %d, %Y")
        current_year = datetime.now().year
        scored = searxng.score_by_freshness(results, current_date, current_year)
        
        for idx, (score, result) in enumerate(scored, 1):
            date_pub = result.get('datePublished', 'Unknown date')
            print(f"\n   {idx}. [{date_pub}] (score={score})")
            print(f"      {result['name'][:70]}")
            print(f"      {result['url']}")
            print(f"      {result['summary'][:100]}...")
    
    print("\n" + "=" * 80)
    print("✅ Test complete!")

if __name__ == "__main__":
    test_freshness()
