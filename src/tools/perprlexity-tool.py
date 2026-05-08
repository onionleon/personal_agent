import os
import time
import random
from typing import Dict, Tuple, Optional, Any
from dotenv import load_dotenv
from langchain.tools import tool
from perplexity import Perplexity, RateLimitError

load_dotenv('../../.env')

class SearchCache:
    def __init__(self, ttl_seconds=3600):
        self.cache: Dict[str, Tuple[Any, float]] = {}
        self.ttl = ttl_seconds
    
    def get(self, query: str) -> Optional[Any]:
        if query in self.cache:
            result, timestamp = self.cache[query]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[query]
        return None
    
    def set(self, query: str, result: Any):
        self.cache[query] = (result, time.time())

search_cache = SearchCache(ttl_seconds=1800) 

def search_with_retry(client, query, max_retries=3, domain: str = None):
    """Performs search with exponential backoff for RateLimitErrors."""
    cached_result = search_cache.get(query)
    if cached_result:
        return cached_result

    for attempt in range(max_retries):
        try:
            
            if not domain:
                result = client.search.create(
                    query=query,
                    max_results=3,
                    max_tokens_per_page=4096
                )
            else:
                result = client.search.create(
                    query=query,
                    max_results=3,
                    max_tokens_per_page=4096,
                    domain=domain
                )
            search_cache.set(query, result)
            return result
            
        except RateLimitError:
            if attempt < max_retries - 1:
                delay = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(delay)
            else:
                raise


@tool
def general_perplexity_search(query: str):
    """
    A comprehensive web search tool powered by Perplexity AI. 
    
    Use this tool when:
    1. The user asks about current events, news, or information after your knowledge cutoff.
    2. You need to verify specific facts, statistics, or technical data from the live web.
    3. High-precision sourcing and citations are required for the answer.
    
    Args:
        query (str): A specific, well-formed search query. For best results, use 
                    natural language questions or keyword-heavy phrases.
    
    Returns:
        dict: A result object containing the 'answer', 'citations' (URLs), and 
              the 'status'. If a RateLimitError occurs, it returns an error status.
              
    Note: This tool uses an internal cache (30-minute TTL) to ensure fast 
          response times for repeated queries and includes automatic retry 
          logic for API rate limits.
    """
    client = Perplexity()

    try:
        return search_with_retry(client, query)

    except RateLimitError:
        return {
            "status": "error",
            "message": "Maximum retries exceeded. Please wait before trying again."
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }

# search specific domain
@tool
def domain_perplexity_search(query: str, domain: str):
    """
    Performs a targeted web search restricted to a specific website or domain.
    
    Use this tool when:
    1. The user asks for information specifically from a known source (e.g., 'What does Wikipedia say about...', 'Search on reddit.com for...').
    2. You need to verify documentation, specialized articles, or news from a trusted authority (e.g., 'arxiv.org', 'nytimes.com', 'github.com').
    3. You want to exclude general web noise and focus only on one high-quality database.

    Args:
        query (str): The search terms or question. Be descriptive.
        domain (str): The specific domain to search (e.g., 'microsoft.com', 'techcrunch.com'). 
                     Do not include 'https://' or 'www.' unless necessary for the specific site.

    Returns:
        dict: Contains the filtered search 'answer', 'citations' only from the requested domain, 
              and 'status'.
              
    Note: Results are cached for 30 minutes. If the domain is invalid or returns no results, 
          the tool will return an empty or error status.
    """
    client = Perplexity()

    try:
        return search_with_retry(client, query, domain)

    except RateLimitError:
        return {
            "status": "error",
            "message": "Maximum retries exceeded. Please wait before trying again."
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }
