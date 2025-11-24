"""
SearXNG Service Wrapper
Handles all interactions with the SearXNG search API
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import re


class SearXNGService:
    """Service class for interacting with SearXNG search engine"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize SearXNG service
        
        Args:
            base_url: Base URL of the SearXNG instance (default: http://localhost:8080)
        """
        self.base_url = base_url.rstrip('/')
        
    def search(
        self, 
        query: str, 
        count: int = 10, 
        time_range: Optional[str] = None,
        timeout: int = 15
    ) -> List[Dict]:
        """
        Perform a search query on SearXNG
        
        Args:
            query: Search query string
            count: Maximum number of results to return
            time_range: Time range filter ('day', 'week', 'month', 'year', None for all)
            timeout: Request timeout in seconds
            
        Returns:
            List of search result dictionaries with normalized fields
        """
        try:
            # Build query parameters
            params = {
                'q': query,
                'format': 'json',
                'pageno': 1
            }
            
            # Map time_range to SearXNG's time_range parameter
            if time_range:
                params['time_range'] = time_range
            
            print(f"[SearXNG] Searching: {query} (time_range={time_range})")
            
            # Make request to SearXNG
            response = requests.get(
                f"{self.base_url}/search",
                params=params,
                timeout=timeout
            )
            
            if response.status_code != 200:
                print(f"[SearXNG] Error: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            results = data.get('results', [])
            
            print(f"[SearXNG] Found {len(results)} raw results")
            
            # Parse and normalize results
            normalized_results = self._parse_results(results)
            
            # Deduplicate results
            unique_results = self._deduplicate_results(normalized_results)
            print(f"[SearXNG] Deduplicated to {len(unique_results)} unique results")
            
            # Limit to requested count
            return unique_results[:count]
            
        except requests.Timeout:
            print(f"[SearXNG] Timeout error")
            return []
        except Exception as e:
            print(f"[SearXNG] Error: {e}")
            return []
    
    def _parse_results(self, raw_results: List[Dict]) -> List[Dict]:
        """
        Parse and normalize SearXNG results to a common format
        
        Args:
            raw_results: Raw results from SearXNG API
            
        Returns:
            List of normalized result dictionaries
        """
        normalized = []
        
        for result in raw_results:
            # Clean the summary text
            raw_summary = result.get('content', '') or result.get('title', '')
            clean_summary = self._clean_text(raw_summary)
            
            normalized_result = {
                'name': result.get('title', 'Untitled'),
                'url': result.get('url', ''),
                'summary': clean_summary,
                'engine': result.get('engine', 'unknown'),
                'score': result.get('score', 0),
                # SearXNG may include publishedDate in some engines
                'datePublished': result.get('publishedDate', None)
            }
            
            normalized.append(normalized_result)
        
        return normalized
    
    def _clean_text(self, text: str) -> str:
        """Clean up snippet text to remove noise"""
        if not text:
            return ""
            
        # Remove common noise
        text = re.sub(r'Read more\.\.\.', '', text)
        text = re.sub(r'\.\.\.$', '', text)
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def _deduplicate_results(self, results: List[Dict], threshold: float = 0.6) -> List[Dict]:
        """
        Deduplicate results based on content similarity
        
        Args:
            results: List of normalized results
            threshold: Jaccard similarity threshold (0.0 to 1.0)
            
        Returns:
            List of unique results
        """
        unique = []
        seen_texts = []
        
        for result in results:
            # Create a signature for comparison (title + summary)
            text = (result['name'] + " " + result['summary']).lower()
            
            is_duplicate = False
            for seen_text in seen_texts:
                if self._calculate_similarity(text, seen_text) > threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(result)
                seen_texts.append(text)
                
        return unique

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two strings"""
        set1 = set(text1.split())
        set2 = set(text2.split())
        
        if not set1 or not set2:
            return 0.0
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union
    
    def score_by_freshness(
        self, 
        results: List[Dict], 
        current_date: str,
        current_year: int
    ) -> List[tuple]:
        """
        Score results based on freshness indicators
        
        Args:
            results: List of search results
            current_date: Current date string (e.g., "November 24, 2025")
            current_year: Current year
            
        Returns:
            List of tuples (score, result) sorted by score descending
        """
        scored_results = []
        
        for result in results:
            score = 0
            
            # Get text fields for scoring
            summary = (result.get('summary') or '').lower()
            name = (result.get('name') or '').lower()
            url = (result.get('url') or '').lower()
            
            result_text = f"{summary} {name} {url}"
            
            # Filter out results with future dates (likely fake/incorrect)
            if '2026' in result_text or '2027' in result_text:
                print(f"[SearXNG] Filtering out result with future date")
                continue
            
            # Scoring for freshness
            if str(current_year) in result_text:
                score += 10
            if current_date.lower() in result_text:
                score += 20
            if any(word in result_text for word in ['today', 'hoy', 'latest', 'current']):
                score += 15
            
            # Boost based on SearXNG's own score if available
            if result.get('score'):
                score += result['score'] * 5
            
            scored_results.append((score, result))
        
        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)
        
        return scored_results
    
    def health_check(self) -> bool:
        """
        Check if SearXNG instance is healthy and responsive
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/healthz",
                timeout=5
            )
            return response.status_code == 200
        except:
            # Try alternative - just a simple search request
            try:
                response = requests.get(
                    f"{self.base_url}/search",
                    params={'q': 'test', 'format': 'json'},
                    timeout=5
                )
                return response.status_code == 200
            except:
                return False


# Standalone test
if __name__ == "__main__":
    service = SearXNGService()
    
    # Health check
    print("Testing SearXNG health...")
    if service.health_check():
        print("✓ SearXNG is healthy")
    else:
        print("✗ SearXNG is not responding")
        exit(1)
    
    # Test search
    print("\nTesting search...")
    results = service.search("Python programming", count=5, time_range="week")
    
    if results:
        print(f"\n✓ Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['name']}")
            print(f"   URL: {result['url']}")
            print(f"   Engine: {result['engine']}")
            print(f"   Summary: {result['summary'][:100]}...")
    else:
        print("✗ No results found")
    
    # Test freshness scoring
    print("\n\nTesting freshness scoring...")
    current_date = datetime.now().strftime("%B %d, %Y")
    current_year = datetime.now().year
    
    scored = service.score_by_freshness(results, current_date, current_year)
    print(f"\nScored results:")
    for score, result in scored:
        print(f"  Score {score}: {result['name'][:60]}")
