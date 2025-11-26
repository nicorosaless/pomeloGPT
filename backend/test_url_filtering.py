"""
Test URL Filtering and Deduplication
"""

from api.searxng_service import SearXNGService


def test_url_filtering():
    """Test URL filtering removes AMP, RSS, and tracking URLs"""
    service = SearXNGService()
    
    # Mock results with various bad URLs
    mock_results = [
        {"name": "Good Article", "url": "https://example.com/article", "summary": "This is good"},
        {"name": "AMP URL 1", "url": "https://example.com/amp/article", "summary": "AMP version"},
        {"name": "AMP URL 2", "url": "https://example.com/article?amp=1", "summary": "AMP query param"},
        {"name": "RSS Feed", "url": "https://example.com/feed.rss", "summary": "RSS feed"},
        {"name": "XML Feed", "url": "https://example.com/feed.xml", "summary": "XML feed"},
        {"name": "Tracking URL", "url": "https://example.com/tracking/redirect", "summary": "Tracking"},
        {"name": "Good Article 2", "url": "https://example2.com/news", "summary": "Another good one"},
    ]
    
    filtered = service._filter_urls(mock_results)
    
    print(f"✓ URL Filtering Test")
    print(f"  Input: {len(mock_results)} results")
    print(f"  Output: {len(filtered)} results")
    print(f"  Filtered out: {len(mock_results) - len(filtered)} bad URLs")
    
    assert len(filtered) == 2, "Should have 2 good URLs remaining"
    assert all('amp' not in r['url'].lower() for r in filtered), "No AMP URLs should remain"
    assert all(not r['url'].endswith(('.rss', '.xml')) for r in filtered), "No RSS/XML should remain"
    print("  ✓ All assertions passed\n")


def test_url_normalization():
    """Test URL normalization removes tracking parameters"""
    service = SearXNGService()
    
    test_cases = [
        {
            "input": "https://example.com/article?utm_source=twitter&utm_medium=social&id=123",
            "expected_clean": ["utm_source", "utm_medium"],  # These should be removed
            "should_keep": "id=123"  # This should remain
        },
        {
            "input": "https://example.com/page/?fbclid=abc123&ref=home",
            "expected_clean": ["fbclid"],
            "should_keep": "ref=home"
        },
    ]
    
    print(f"✓ URL Normalization Test")
    for i, test in enumerate(test_cases, 1):
        normalized = service._normalize_url(test["input"])
        print(f"  Test {i}:")
        print(f"    Input:  {test['input']}")
        print(f"    Output: {normalized}")
        
        # Check tracking params are removed
        for param in test["expected_clean"]:
            assert param not in normalized, f"Tracking param '{param}' should be removed"
        
        # Check important params remain
        if test["should_keep"]:
            assert test["should_keep"] in normalized, f"Important param '{test['should_keep']}' should remain"
    
    print("  ✓ All normalization tests passed\n")


def test_title_normalization():
    """Test title normalization"""
    service = SearXNGService()
    
    test_cases = [
        ("Breaking: Bitcoin Hits $50K - CNN", "breaking bitcoin hits 50k"),
        ("Apple Releases New iPhone | Nov 25", "apple releases new iphone"),
        ("Tech News - Forbes 2024", "tech news"),
    ]
    
    print(f"✓ Title Normalization Test")
    for input_title, expected in test_cases:
        normalized = service._normalize_title(input_title)
        print(f"  '{input_title}' → '{normalized}'")
        assert normalized == expected, f"Expected '{expected}', got '{normalized}'"
    
    print("  ✓ All title normalization tests passed\n")


def test_diversity():
    """Test source diversity enforcement"""
    service = SearXNGService()
    
    # Mock results with multiple from same domain
    mock_results = [
        {"name": "Article 1", "url": "https://example.com/article1", "summary": "First"},
        {"name": "Article 2", "url": "https://example.com/article2", "summary": "Second"},
        {"name": "Article 3", "url": "https://example.com/article3", "summary": "Third"},
        {"name": "Different 1", "url": "https://another.com/article", "summary": "Different source"},
        {"name": "Different 2", "url": "https://third.com/article", "summary": "Another source"},
    ]
    
    diverse = service._ensure_diversity(mock_results, max_per_domain=2)
    
    print(f"✓ Source Diversity Test")
    print(f"  Input: {len(mock_results)} results (3 from example.com)")
    print(f"  Output: {len(diverse)} results")
    print(f"  Max per domain: 2")
    
    # Count domains
    from collections import Counter
    from urllib.parse import urlparse
    domain_counts = Counter(urlparse(r['url']).netloc.replace('www.', '') for r in diverse)
    print(f"  Domain distribution: {dict(domain_counts)}")
    
    assert max(domain_counts.values()) <= 2, "No domain should have more than 2 results"
    print("  ✓ Diversity test passed\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Testing WebSearch Improvements")
    print("="*60 + "\n")
    
    test_url_filtering()
    test_url_normalization()
    test_title_normalization()
    test_diversity()
    
    print("="*60)
    print("✅ All tests passed!")
    print("="*60)
