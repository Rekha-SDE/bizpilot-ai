import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone


def get_search_config():
    """Retrieve search provider configuration securely from environment variables.

    Never exposes API keys to the frontend or logs.
    """
    api_key = (
        os.getenv("SEARCH_API_KEY")
        or os.getenv("TAVILY_API_KEY")
        or os.getenv("SERPAPI_API_KEY")
    )
    api_base = os.getenv("SEARCH_API_BASE", "https://api.tavily.com")

    return {
        "api_key": api_key,
        "api_base": api_base,
        "is_configured": bool(api_key and api_key.strip()),
    }


def call_search_provider(query: str, config: dict) -> list:
    """Send query to the configured search provider via HTTP request.

    This function is designed to be mocked in unit tests so that no real web searches are performed.
    """
    url = f"{config['api_base'].rstrip('/')}/search"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    payload = {
        "query": query,
        "max_results": 5,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))
        raw_results = result.get("results", [])

        now_iso = datetime.now(timezone.utc).isoformat()
        normalized = []
        for r in raw_results:
            normalized.append({
                "title": r.get("title", "Untitled Source"),
                "url": r.get("url", "#"),
                "snippet": r.get("content") or r.get("snippet", ""),
                "retrieved_at": now_iso,
            })
        return normalized


def get_market_research(idea: str, location: str) -> dict:
    """Conduct market research or return setup-needed response if not configured.

    Guarantees:
    1. Returns clear setup-needed response if search is unconfigured (does not invent facts).
    2. Separates verified sourced facts from estimates and assumptions.
    3. Never guarantees profit or business success.
    4. Records retrieval timestamp, source title, and URL for every finding.
    """
    config = get_search_config()

    if not config["is_configured"]:
        return {
            "configured": False,
            "message": (
                "Market research search provider is not configured yet. "
                "To enable web search research, set the SEARCH_API_KEY environment variable on your backend server."
            ),
            "research": None,
        }

    search_query = f"{idea} market demand competition trends in {location}"
    retrieval_time = datetime.now(timezone.utc).isoformat()

    try:
        raw_sources = call_search_provider(search_query, config)

        sourced_facts = []
        for src in raw_sources:
            snippet = src.get("snippet", "").strip()
            if snippet:
                sourced_facts.append(f"From '{src.get('title')}': {snippet}")

        if not sourced_facts:
            sourced_facts.append(f"No specific live web entries returned for query '{search_query}'.")

        estimates_and_assumptions = [
            f"Estimated local market size in {location} assumes typical regional demographics and consumer spend.",
            "Customer demand, foot traffic, and seasonal trends require local field verification.",
            "Operating expenses and competitor density will vary based on exact neighborhood and supplier contracts.",
        ]

        return {
            "configured": True,
            "message": "Market research completed successfully.",
            "research": {
                "idea": idea,
                "location": location,
                "query": search_query,
                "retrieved_at": retrieval_time,
                "sources": raw_sources,
                "sourced_facts": sourced_facts,
                "estimates_and_assumptions": estimates_and_assumptions,
                "disclaimer": (
                    "All market findings, sources, and projections are estimates and assumptions for planning purposes only. "
                    "Market conditions fluctuate and business success or profit is never guaranteed."
                ),
            },
        }
    except Exception:
        # Return safe error without exposing credentials or internal traces
        return {
            "configured": True,
            "message": "Could not complete market research due to a search provider communication error. Please try again later.",
            "research": None,
        }


def get_competitor_analysis(business_type: str, location: str) -> dict:
    """Analyze competitors strictly based on verified search results.

    Guarantees:
    1. If search is unconfigured, returns a clear setup-needed response without fabricating data.
    2. Returns only competitor information supported by search results with titles, URLs, and retrieval timestamps.
    3. Clearly states when reliable information is unavailable.
    4. Does not invent competitor names, prices, or market facts.
    5. Disclaims guaranteed profits or market success.
    """
    config = get_search_config()

    if not config["is_configured"]:
        return {
            "configured": False,
            "message": (
                "Competitor analysis search provider is not configured yet. "
                "To enable competitor analysis, set the SEARCH_API_KEY environment variable on your backend server."
            ),
            "analysis": None,
        }

    search_query = f"{business_type} competitors in {location}"
    retrieval_time = datetime.now(timezone.utc).isoformat()

    try:
        raw_sources = call_search_provider(search_query, config)

        competitors = []
        for src in raw_sources:
            title = src.get("title", "").strip()
            snippet = src.get("snippet", "").strip()
            url = src.get("url", "#")
            retrieved_at = src.get("retrieved_at", retrieval_time)

            if title or snippet:
                # Do not invent competitor names; use strictly verified source title and details
                competitors.append({
                    "name": title if title else "Identified Competitor Listing",
                    "details": snippet if snippet else "No detailed description provided in source result.",
                    "source_title": title if title else "Web Search Result",
                    "source_url": url,
                    "retrieved_at": retrieved_at,
                })

        if competitors:
            summary = (
                f"Identified {len(competitors)} potential competitor or market reference(s) "
                f"for '{business_type}' in '{location}' based on public search results."
            )
            unavailable_note = (
                "Reliable information on competitor profit margins, exact revenues, and private supplier contracts "
                "is unavailable from public search results and has not been invented."
            )
        else:
            summary = f"No direct competitor entries were identified in search results for query '{search_query}'."
            unavailable_note = (
                "Reliable competitor information is unavailable from search results for this query and location. "
                "No competitor names, pricing, or figures have been fabricated."
            )

        return {
            "configured": True,
            "message": "Competitor analysis completed successfully.",
            "analysis": {
                "business_type": business_type,
                "location": location,
                "query": search_query,
                "retrieved_at": retrieval_time,
                "competitors": competitors,
                "summary_of_findings": summary,
                "unavailable_details_note": unavailable_note,
                "disclaimer": (
                    "Competitor information is sourced strictly from public web results for informational purposes. "
                    "Private financials, pricing, and customer counts are not guaranteed and business success or profit is never promised."
                ),
            },
        }
    except Exception:
        return {
            "configured": True,
            "message": "Could not complete competitor analysis due to a search provider communication error. Please try again later.",
            "analysis": None,
        }

