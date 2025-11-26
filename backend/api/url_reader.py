"""
Simple URL reader for fetching and extracting content from web pages.
"""

import requests
from bs4 import BeautifulSoup


async def read_url_content(url: str, max_length: int = 8000) -> str:
    """
    Reads and extracts text content from a URL.
    
    Args:
        url: The URL to read
        max_length: Maximum length of content to return (default 8000 chars)
    
    Returns:
        Extracted text content from the URL, or error message if failed
    """
    try:
        # Make request with timeout
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.decompose()
        
        # Extract text
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "\n\n... [Content truncated]"
        
        return text
        
    except requests.exceptions.Timeout:
        return f"Error: Timeout while reading URL {url}"
    except requests.exceptions.RequestException as e:
        return f"Error reading URL {url}: {str(e)}"
    except Exception as e:
        return f"Unexpected error reading URL {url}: {str(e)}"
