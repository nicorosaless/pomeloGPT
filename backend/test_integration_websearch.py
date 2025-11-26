"""
Integration Test for Complete WebSearch Pipeline
Tests the full flow: search → filter → deduplicate → diversify
"""

from api.searxng_service import SearXNGService
from datetime import datetime


def test_complete_pipeline():
    """Test the complete search pipeline with SearXNG"""
    service = SearXNGService()
    
    print("\n" + "="*70)
    print("🔍 WebSearch Pipeline Integration Test")
    print("="*70 + "\n")
    
    # Health check
    print("1. Checking SearXNG health...")
    if not service.health_check():
        print("   ❌ SearXNG is not available at http://localhost:8080")
        print("   💡 Start it with: docker-compose -f docker-compose.searxng.yml up -d")
        return False
    print("   ✓ SearXNG is healthy\n")
    
    # Test search with filtering and deduplication
    print("2. Testing search with full pipeline...")
    query = "Bitcoin price today"
    print(f"   Query: '{query}'")
    print(f"   Requesting: 10 results (will fetch more internally for filtering)")
    
    results = service.search(
        query=query,
        count=10,
        time_range="day"
    )
    
    print(f"\n   ✓ Received {len(results)} final results after pipeline")
    
    # Verify URL quality
    print("\n3. Verifying URL quality...")
    bad_urls = []
    for r in results:
        url = r['url'].lower()
        if any(pattern in url for pattern in ['/amp/', '?amp=', '.amp', '.rss', '.xml', '/feed/', 'tracking']):
            bad_urls.append(url)
    
    if bad_urls:
        print(f"   ❌ Found {len(bad_urls)} bad URLs:")
        for url in bad_urls:
            print(f"      - {url}")
        return False
    else:
        print("   ✓ All URLs are clean (no AMP, RSS, or tracking URLs)")
    
    # Verify source diversity
    print("\n4. Verifying source diversity...")
    from urllib.parse import urlparse
    from collections import Counter
    
    domains = [urlparse(r['url']).netloc.replace('www.', '') for r in results]
    domain_counts = Counter(domains)
    
    print(f"   Domains found: {len(domain_counts)}")
    for domain, count in domain_counts.most_common():
        print(f"      - {domain}: {count} result(s)")
    
    max_per_domain = max(domain_counts.values())
    if max_per_domain > 2:
        print(f"   ⚠️  Domain '{domain_counts.most_common(1)[0][0]}' has {max_per_domain} results (max should be 2)")
    else:
        print(f"   ✓ Source diversity maintained (max {max_per_domain} per domain)")
    
    # Show sample results
    print("\n5. Sample results:")
    for i, result in enumerate(results[:3], 1):
        print(f"\n   Result #{i}:")
        print(f"      Title: {result['name'][:70]}")
        print(f"      URL:   {result['url'][:70]}")
        print(f"      Summary: {result['summary'][:100]}...")
    
    print("\n" + "="*70)
    print("✅ Integration test completed successfully!")
    print("="*70 + "\n")
    
    return True


if __name__ == "__main__":
    try:
        test_complete_pipeline()
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
