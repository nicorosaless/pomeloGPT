"""
SearXNG Service Wrapper
Handles all interactions with the SearXNG search API
"""

import aiohttp
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import re
from urllib.parse import urlparse, urlunparse, parse_qs
import numpy as np
from sentence_transformers import SentenceTransformer


class SearXNGService:
    """Service class for interacting with SearXNG search engine"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        """
        Initialize SearXNG service
        
        Args:
            base_url: Base URL of the SearXNG instance (default: http://localhost:8080)
        """
        self.base_url = base_url.rstrip('/')
        # Initialize embedding model for semantic deduplication (lightweight & fast)
        self._embedding_model = None  # Lazy load on first use
        
    async def search(
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
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"{self.base_url}/search",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as response:
                        
                        if response.status != 200:
                            text = await response.text()
                            print(f"[SearXNG] Error: {response.status} - {text}")
                            return []
                        
                        data = await response.json()
                        results = data.get('results', [])
                except asyncio.TimeoutError:
                    print(f"[SearXNG] Timeout error")
                    return []
            
            print(f"[SearXNG] Found {len(results)} raw results")
            
            # Parse and normalize results
            normalized_results = self._parse_results(results)
            
            # Filter bad URLs (AMP, RSS, tracking)
            filtered_results = self._filter_urls(normalized_results)
            print(f"[SearXNG] Filtered to {len(filtered_results)} clean results")
            
            # Deduplicate results (fast embedding-based)
            unique_results = self._deduplicate_results(filtered_results)
            print(f"[SearXNG] Deduplicated to {len(unique_results)} unique results")
            
            # Ensure source diversity (max 2 per domain)
            diverse_results = self._ensure_diversity(unique_results)
            print(f"[SearXNG] Selected {len(diverse_results)} diverse sources")
            
            # Limit to requested count
            return diverse_results[:count]
            
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
            
        # Remove common noise patterns
        text = re.sub(r'Read more\.\.\.', '', text)
        text = re.sub(r'Click here.*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\.\.\.$', '', text)
        text = re.sub(r'\s+-\s+\d{1,2}/\d{1,2}/\d{2,4}', '', text)  # Remove dates like "- 11/25/2025"
        
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _filter_urls(self, results: List[Dict]) -> List[Dict]:
        """Filter out unwanted URLs (AMP, RSS, tracking, etc.)"""
        filtered = []
        
        for result in results:
            url = result.get('url', '').lower()
            
            # Skip AMP URLs
            if '/amp/' in url or '?amp=' in url or '.amp' in url or '/amp.' in url:
                continue
            
            # Skip RSS/XML feeds
            if url.endswith('.rss') or url.endswith('.xml') or '/rss/' in url or '/feed/' in url:
                continue
            
            # Skip common tracking/redirect URLs
            if 'tracking' in url or 'redirect' in url or 'goto' in url:
                continue
            
            # Normalize URL (remove tracking params)
            result['url'] = self._normalize_url(result['url'])
            
            filtered.append(result)
        
        return filtered
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing tracking parameters"""
        try:
            parsed = urlparse(url)
            
            # Parse query parameters
            params = parse_qs(parsed.query)
            
            # Remove common tracking parameters
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
                              'fbclid', 'gclid', 'msclkid', 'mc_cid', 'mc_eid']
            
            for param in tracking_params:
                params.pop(param, None)
            
            # Rebuild query string
            clean_query = '&'.join(f"{k}={v[0]}" for k, v in params.items())
            
            # Rebuild URL without tracking params
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path.rstrip('/'),  # Remove trailing slash
                parsed.params,
                clean_query,
                ''  # Remove fragment
            ))
            
            return clean_url
        except:
            return url
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison (lowercase, remove noise)"""
        if not title:
            return ""
        
        # Convert to lowercase
        normalized = title.lower()
        
        # Remove common publisher suffixes
        normalized = re.sub(r'\s*-\s*(cnn|bbc|reuters|bloomberg|forbes|techcrunch|the verge).*$', '', normalized, flags=re.IGNORECASE)
        
        # Remove date patterns
        normalized = re.sub(r'\s*-\s*\d{1,2}/\d{1,2}/\d{2,4}', '', normalized)
        normalized = re.sub(r'\s*\|\s*\d{1,2}\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', '', normalized, flags=re.IGNORECASE)
        
        # Remove special characters
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def _deduplicate_results(self, results: List[Dict], threshold: float = 0.75) -> List[Dict]:
        """
        Deduplicate results based on semantic similarity using embeddings
        
        Args:
            results: List of normalized results
            threshold: Cosine similarity threshold (0.0 to 1.0), higher = more strict
            
        Returns:
            List of unique results
        """
        if len(results) <= 1:
            return results
        
        # Lazy load embedding model (only loaded once, then cached)
        if self._embedding_model is None:
            print("[SearXNG] Loading embedding model (one-time initialization)...")
            self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        unique = []
        embeddings = []
        
        for result in results:
            # Create text for embedding (normalized title + summary)
            title_norm = self._normalize_title(result['name'])
            text = f"{title_norm} {result['summary']}"
            
            # Generate embedding
            embedding = self._embedding_model.encode(text, convert_to_numpy=True)
            
            # Check similarity with existing results
            is_duplicate = False
            for existing_emb in embeddings:
                similarity = self._cosine_similarity(embedding, existing_emb)
                if similarity > threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique.append(result)
                embeddings.append(embedding)
                
        return unique
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm_product = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return dot_product / norm_product if norm_product > 0 else 0.0
    
    def _ensure_diversity(self, results: List[Dict], max_per_domain: int = 2) -> List[Dict]:
        """Ensure source diversity by limiting results per domain"""
        domain_counts = {}
        diverse = []
        
        for result in results:
            try:
                domain = urlparse(result['url']).netloc
                # Remove 'www.' prefix for counting
                domain = domain.replace('www.', '')
                
                count = domain_counts.get(domain, 0)
                if count < max_per_domain:
                    diverse.append(result)
                    domain_counts[domain] = count + 1
            except:
                # If URL parsing fails, include the result
                diverse.append(result)
        
        return diverse
    
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
    
    async def health_check(self) -> bool:
        """
        Check if SearXNG instance is healthy and responsive
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/healthz",
                    timeout=5
                ) as response:
                    return response.status == 200
        except:
            # Try alternative - just a simple search request
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/search",
                        params={'q': 'test', 'format': 'json'},
                        timeout=5
                    ) as response:
                        return response.status == 200
            except:
                return False


# Standalone test
if __name__ == "__main__":
    async def test():
        service = SearXNGService()
        
        # Health check
        print("Testing SearXNG health...")
        if await service.health_check():
            print("✓ SearXNG is healthy")
        else:
            print("✗ SearXNG is not responding")
            exit(1)
        
        # Test search
        print("\nTesting search...")
        results = await service.search("Python programming", count=5, time_range="week")
        
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

    asyncio.run(test())
