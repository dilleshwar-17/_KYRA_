from ddgs import DDGS # type: ignore
import logging

log = logging.getLogger("kyra.search")

def search_web(query: str, max_results: int = 5) -> str:
    """
    Performs a web search using DuckDuckGo and returns a formatted string of results.
    """
    print(f"[SEARCH] Querying: {query}")
    try:
        import threading
        
        results = []
        def _target():
            nonlocal results
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=max_results))
            except Exception as inner_e:
                log.error(f"DDGS Internal Error: {inner_e}")

        thread = threading.Thread(target=_target)
        thread.start()
        thread.join(timeout=10.0) # 10 second search timeout
        
        if thread.is_alive():
            log.warning(f"Search timed out for query: {query}")
            return "Search timed out. Please try again or rephrase."

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
