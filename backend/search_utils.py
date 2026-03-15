from ddgs import DDGS
import logging

log = logging.getLogger("kyra.search")

def search_web(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo and returns a formatted string of results.
    """
    print(f"[SEARCH] Querying: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return "No search results found."
            
            formatted_results = []
            for i, r in enumerate(results, 1):
                title = r.get('title', 'No Title')
                body = r.get('body', 'No Description')
                href = r.get('href', '#')
                formatted_results.append(f"{i}. {title}\n   {body}\n   Source: {href}")
            
            return "\n\n".join(formatted_results)
    except Exception as e:
        log.error(f"Search error: {e}")
        return f"Error performing search: {e}"

if __name__ == "__main__":
    # Test
    print(search_web("IPL score today"))
