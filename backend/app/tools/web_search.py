"""
Web search tool for searching the internet.
"""
import logging
from typing import Dict, Any, Optional

import httpx

from app.config import settings
from app.tools.base import BaseTool

logger = logging.getLogger(__name__)

DUCKDUCKGO_API_URL = "https://api.duckduckgo.com/"
SERPAPI_URL = "https://serpapi.com/search"


class WebSearchTool(BaseTool):
    """Tool for searching the web for information."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for information about a topic, person, place, or any query. "
            "Returns relevant search results with titles, snippets, and URLs. "
            "Use this when you need current information, facts, or details that aren't in your knowledge base."
        )

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up on the web"
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of search results to return (default: 5, max: 10)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }

    async def execute(
            self,
            query: str,
            num_results: int = 5,
            **kwargs
    ) -> str:
        """
        Execute web search tool.

        Args:
            query: Search query string
            num_results: Number of results to return (1-10)
            **kwargs: Additional context

        Returns:
            Formatted search results string
        """
        import time
        start_time = time.time()
        logger.info(
            f"[WEB_SEARCH] Execution started - query: {query}, num_results: {num_results}, provider: {settings.search_provider}")

        # Validate num_results
        num_results = max(1, min(10, num_results))

        try:
            if settings.search_provider == "serpapi" and settings.serpapi_api_key:
                results = await self._search_serpapi(query, num_results)
            else:
                results = await self._search_duckduckgo(query, num_results)

            execution_time = time.time() - start_time
            logger.info(
                f"[WEB_SEARCH] Search completed in {execution_time:.2f}s - found {len(results)} results")

            if not results:
                return f"I couldn't find any relevant results for '{query}'. Try rephrasing your search query or being more specific."

            formatted_response = self._format_search_results(query, results)
            total_time = time.time() - start_time
            logger.info(
                f"[WEB_SEARCH] Execution completed successfully in {total_time:.2f}s - response_length: {len(formatted_response)}")
            return formatted_response

        except httpx.TimeoutException:
            execution_time = time.time() - start_time
            logger.error(f"[WEB_SEARCH] Timeout searching for '{query}' - time: {execution_time:.2f}s")
            return f"The search service is taking too long to respond. Please try again in a moment."
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"[WEB_SEARCH] Error searching for '{query}': {str(e)} - time: {execution_time:.2f}s",
                exc_info=True)
            return f"Sorry, I encountered an error while searching: {str(e)}"

    async def _search_duckduckgo(self, query: str, num_results: int) -> list:
        """Search using DuckDuckGo HTML scraping approach."""
        import time
        api_start = time.time()

        try:
            # DuckDuckGo doesn't have a public JSON API, so we'll use HTML scraping
            # Using a simple approach with DuckDuckGo's instant answer API and HTML search
            search_url = "https://html.duckduckgo.com/html/"
            
            params = {
                "q": query
            }

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }

            logger.debug(f"[WEB_SEARCH] Calling DuckDuckGo - query: {query}")
            
            # Try to use BeautifulSoup if available, otherwise use fallback
            try:
                from bs4 import BeautifulSoup
                use_beautifulsoup = True
            except ImportError:
                logger.debug("[WEB_SEARCH] BeautifulSoup not available, using fallback method")
                use_beautifulsoup = False
                return await self._search_duckduckgo_fallback(query, num_results)
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(search_url, params=params, headers=headers)
                api_time = time.time() - api_start
                logger.debug(f"[WEB_SEARCH] DuckDuckGo response received in {api_time:.2f}s - status: {response.status_code}")
                response.raise_for_status()
                
                if not use_beautifulsoup:
                    return await self._search_duckduckgo_fallback(query, num_results)
                
                # Parse HTML results
                soup = BeautifulSoup(response.text, 'html.parser')
                
                results = []
                # DuckDuckGo HTML structure - find result links
                result_divs = soup.find_all('div', class_='result')
                
                for i, result_div in enumerate(result_divs[:num_results]):
                    try:
                        title_elem = result_div.find('a', class_='result__a')
                        snippet_elem = result_div.find('a', class_='result__snippet')
                        
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            url = title_elem.get('href', '')
                            
                            # Clean URL (DuckDuckGo uses redirect URLs)
                            if url.startswith('/l/?kh='):
                                # Extract actual URL from redirect
                                import urllib.parse
                                parsed = urllib.parse.urlparse(url)
                                query_params = urllib.parse.parse_qs(parsed.query)
                                if 'uddg' in query_params:
                                    url = urllib.parse.unquote(query_params['uddg'][0])
                            
                            snippet = ""
                            if snippet_elem:
                                snippet = snippet_elem.get_text(strip=True)
                            else:
                                # Try to find snippet in other elements
                                snippet_elem = result_div.find('a', class_='result__snippet')
                                if not snippet_elem:
                                    snippet_elem = result_div.find('div', class_='result__snippet')
                                if snippet_elem:
                                    snippet = snippet_elem.get_text(strip=True)
                            
                            if title and url:
                                results.append({
                                    "title": title,
                                    "url": url,
                                    "snippet": snippet or "No description available"
                                })
                    except Exception as e:
                        logger.debug(f"[WEB_SEARCH] Error parsing result {i}: {e}")
                        continue
                
                # If HTML parsing didn't yield results, fall back to instant answer API
                if not results:
                    logger.debug("[WEB_SEARCH] HTML parsing yielded no results, using fallback")
                    return await self._search_duckduckgo_fallback(query, num_results)
                
                return results
        except Exception as e:
            logger.error(f"[WEB_SEARCH] Error in DuckDuckGo search: {e}", exc_info=True)
            raise

    async def _search_duckduckgo_fallback(self, query: str, num_results: int) -> list:
        """Fallback DuckDuckGo search using instant answer API."""
        try:
            # Try DuckDuckGo Instant Answer API (limited but free)
            instant_answer_url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(instant_answer_url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                
                # Extract Abstract (if available)
                if data.get("AbstractText"):
                    results.append({
                        "title": data.get("Heading", query),
                        "url": data.get("AbstractURL", ""),
                        "snippet": data.get("AbstractText", "")
                    })

                # Extract Related Topics
                for topic in data.get("RelatedTopics", [])[:num_results - len(results)]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " ").title(),
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", "")
                        })

                return results[:num_results]

        except Exception as e:
            logger.error(f"[WEB_SEARCH] Error in DuckDuckGo fallback search: {e}", exc_info=True)
            return []

    async def _search_serpapi(self, query: str, num_results: int) -> list:
        """Search using SerpAPI (requires API key)."""
        import time
        api_start = time.time()

        if not settings.serpapi_api_key:
            logger.error("[WEB_SEARCH] SerpAPI key not configured, falling back to DuckDuckGo")
            return await self._search_duckduckgo(query, num_results)

        params = {
            "q": query,
            "api_key": settings.serpapi_api_key,
            "num": num_results
        }

        logger.debug(f"[WEB_SEARCH] Calling SerpAPI - query: {query}")
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(SERPAPI_URL, params=params)
            api_time = time.time() - api_start
            logger.debug(f"[WEB_SEARCH] SerpAPI response received in {api_time:.2f}s - status: {response.status_code}")
            response.raise_for_status()
            data = response.json()

            results = []
            organic_results = data.get("organic_results", [])

            for result in organic_results[:num_results]:
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("link", ""),
                    "snippet": result.get("snippet", "")
                })

            return results

    def _format_search_results(self, query: str, results: list) -> str:
        """Format search results into a readable string."""
        if not results:
            return f"No results found for '{query}'."

        formatted = f"🔍 Search results for '{query}':\n\n"

        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            url = result.get("url", "")
            snippet = result.get("snippet", "No description available")

            formatted += f"{i}. **{title}**\n"
            if url:
                formatted += f"   🔗 {url}\n"
            formatted += f"   {snippet}\n\n"

        return formatted.strip()

