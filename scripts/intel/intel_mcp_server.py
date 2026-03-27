#!/usr/bin/env python3
"""
WalletDNA Intelligence MCP Server
==================================
Free, no-API-key scraping of Twitter/X, Reddit, Farcaster, RSS, and Web3 forums.

Techniques used (2025 updated):
  - Twitter/X: twikit with account login (free, no paid API — guest tokens dead as of Jan 2025)
             Setup: pip install twikit, set TWITTER_USERNAME/TWITTER_EMAIL/TWITTER_PASSWORD env vars
             Alternative: twscrape with account cookies pooling (also requires account login)
  - Reddit:  public JSON API (no auth, 60 req/min)
  - Farcaster: Warpcast public Hub API (free, no key)
  - RSS: built-in xml.etree.ElementTree parser (zero external dependencies)
  - Web: httpx + BeautifulSoup for forums (rotated UA headers)
  - Backup: Playwright browser automation for JS-heavy pages

NOTE: Twitter scraping requires a real account (free tier, no paid Twitter API needed).
      Nitter public instances are defunct (shut down early 2024).

Run as MCP server:
  python3 scripts/intel/intel_mcp_server.py

Or install as MCP in settings.json:
  "walletdna-intel": {
    "command": "python3",
    "args": ["/home/user/walletdna/scripts/intel/intel_mcp_server.py"]
  }
"""

import asyncio
import json
import sys
import time
import random
from datetime import datetime, timezone
from typing import Any

import httpx

# ── MCP protocol over stdio ────────────────────────────────────────────────────

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _log(msg: str) -> None:
    sys.stderr.write(f"[intel-mcp] {msg}\n")
    sys.stderr.flush()


# ── Browser-like headers (rotate to avoid blocks) ─────────────────────────────

_UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


def _headers(extra: dict = None) -> dict:
    h = {
        "User-Agent": random.choice(_UA_POOL),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    if extra:
        h.update(extra)
    return h


# ── Reddit scraper (public JSON API — zero auth needed) ───────────────────────

async def reddit_search(query: str, subreddits: list[str] = None, limit: int = 20) -> list[dict]:
    """Search Reddit posts. No API key. No OAuth. Pure public JSON."""
    results = []
    subs = subreddits or ["defi", "CryptoCurrency", "solana", "ethdev", "CryptoTechnology", "web3"]

    async with httpx.AsyncClient(headers=_headers(), follow_redirects=True, timeout=15) as client:
        for sub in subs:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {"q": query, "sort": "new", "limit": min(limit, 25), "restrict_sr": "1", "t": "month"}
            try:
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    _log(f"Reddit r/{sub} status {r.status_code}")
                    continue
                data = r.json()
                for post in data.get("data", {}).get("children", []):
                    d = post["data"]
                    results.append({
                        "source": "reddit",
                        "subreddit": d.get("subreddit", sub),
                        "title": d.get("title", ""),
                        "body": (d.get("selftext", "") or "")[:500],
                        "score": d.get("score", 0),
                        "comments": d.get("num_comments", 0),
                        "url": f"https://reddit.com{d.get('permalink', '')}",
                        "author": d.get("author", ""),
                        "created_utc": d.get("created_utc", 0),
                        "created": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).isoformat(),
                    })
                await asyncio.sleep(0.5)  # be polite
            except Exception as e:
                _log(f"Reddit error r/{sub}: {e}")

    # Sort by score desc
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


async def reddit_hot(subreddit: str = "defi", limit: int = 10) -> list[dict]:
    """Get hot posts from a subreddit."""
    async with httpx.AsyncClient(headers=_headers(), follow_redirects=True, timeout=15) as client:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json"
        try:
            r = await client.get(url, params={"limit": limit})
            if r.status_code != 200:
                return []
            data = r.json()
            results = []
            for post in data.get("data", {}).get("children", []):
                d = post["data"]
                results.append({
                    "source": "reddit",
                    "subreddit": subreddit,
                    "title": d.get("title", ""),
                    "body": (d.get("selftext", "") or "")[:300],
                    "score": d.get("score", 0),
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                    "created": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).isoformat(),
                })
            return results
        except Exception as e:
            _log(f"Reddit hot error: {e}")
            return []


# ── Twitter/X scraper (requires account login as of Jan 2025) ───────────────

async def twitter_search(query: str, limit: int = 20, mode: str = "top") -> list[dict]:
    """
    Search Twitter using twikit (requires account login).

    ⚠️ IMPORTANT: As of Jan 2025, guest token scraping is DEAD.
    Twitter now binds guest tokens to browser fingerprints and permanently bans datacenter IPs.

    Setup required:
      pip install twikit
      export TWITTER_USERNAME="your_username"
      export TWITTER_EMAIL="your_email"
      export TWITTER_PASSWORD="your_password"

    For pooling multiple accounts, use twscrape instead:
      pip install twscrape
      # Then configure accounts in ~/.local/share/twscrape/accounts.json

    mode: "top" | "latest"
    """
    try:
        from twikit import Client
        import os

        client = Client(language='en-US')
        username = os.getenv('TWITTER_USERNAME')
        email = os.getenv('TWITTER_EMAIL')
        password = os.getenv('TWITTER_PASSWORD')

        if not all([username, email, password]):
            _log("Twitter: missing TWITTER_USERNAME/TWITTER_EMAIL/TWITTER_PASSWORD env vars")
            return []

        await client.login(auth_info_1=username, auth_info_2=email, password=password)
        tweets = await client.search(query, product='Latest' if mode == 'latest' else 'Top')

        results = []
        for t in tweets:
            results.append({
                "source": "twitter",
                "id": str(t.id),
                "text": t.text,
                "author": t.user.name if t.user else "unknown",
                "author_handle": t.user.screen_name if t.user else "",
                "followers": t.user.followers_count if t.user else 0,
                "likes": t.favorite_count,
                "retweets": t.retweet_count,
                "replies": t.reply_count,
                "created": t.created_at.isoformat() if t.created_at else "",
                "url": f"https://twitter.com/{t.user.screen_name if t.user else 'i'}/status/{t.id}",
                "lang": t.lang if hasattr(t, 'lang') else "",
            })
        return results
    except ImportError:
        _log("twikit not installed: pip install twikit")
        return []
    except Exception as e:
        _log(f"twikit search error: {e}")
        return []


async def twitter_user_tweets(username: str, limit: int = 20) -> list[dict]:
    """Get recent tweets from a specific user. Requires account login (Jan 2025+)."""
    try:
        from twikit import Client
        import os

        client = Client(language='en-US')
        auth_username = os.getenv('TWITTER_USERNAME')
        email = os.getenv('TWITTER_EMAIL')
        password = os.getenv('TWITTER_PASSWORD')

        if not all([auth_username, email, password]):
            _log("Twitter: missing TWITTER_USERNAME/TWITTER_EMAIL/TWITTER_PASSWORD env vars")
            return []

        await client.login(auth_info_1=auth_username, auth_info_2=email, password=password)

        # Fetch user by handle
        user = await client.get_user_by_screen_name(username)
        tweets = await client.get_user_tweets(user.id, count=limit)

        results = []
        for t in tweets:
            results.append({
                "source": "twitter",
                "text": t.text,
                "author": username,
                "likes": t.favorite_count,
                "retweets": t.retweet_count,
                "created": t.created_at.isoformat() if t.created_at else "",
                "url": f"https://twitter.com/{username}/status/{t.id}",
            })
        return results
    except ImportError:
        _log("twikit not installed: pip install twikit")
        return []
    except Exception as e:
        _log(f"twitter_user_tweets error: {e}")
        return []


# ── Nitter RSS fallback (DEPRECATED — all public instances shut down early 2024) ──

_NITTER_INSTANCES = [
    # All Nitter public instances are defunct as of early 2024
    # X revoked guest account access that Nitter relied on
    # Keeping for reference only — will not work
]


def _parse_rss_xml(xml_text: str, limit: int = 20) -> list[dict]:
    """Parse RSS/Atom XML using Python's built-in xml.etree.ElementTree. Zero deps."""
    import xml.etree.ElementTree as ET

    results = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}

        # RSS 2.0
        for item in root.findall(".//item")[:limit]:
            results.append({
                "title": item.findtext("title", "").strip(),
                "text": item.findtext("description", "").strip(),
                "author": item.findtext("author", item.findtext("dc:creator", "", ns), ns).strip(),
                "url": item.findtext("link", "").strip(),
                "created": item.findtext("pubDate", "").strip(),
            })

        # Atom
        if not results:
            for entry in root.findall(".//atom:entry", ns)[:limit]:
                link_el = entry.find("atom:link", ns)
                results.append({
                    "title": (entry.findtext("atom:title", "", ns) or "").strip(),
                    "text": (entry.findtext("atom:summary", entry.findtext("atom:content", "", ns), ns) or "").strip(),
                    "author": (entry.findtext("atom:author/atom:name", "", ns) or "").strip(),
                    "url": link_el.get("href", "") if link_el is not None else "",
                    "created": (entry.findtext("atom:published", entry.findtext("atom:updated", "", ns), ns) or "").strip(),
                })
    except ET.ParseError as e:
        _log(f"XML parse error: {e}")
    return results


async def nitter_search(query: str, limit: int = 20) -> list[dict]:
    """DEPRECATED: Nitter RSS fallback — all public instances shut down early 2024.
    Use twitter_search() with twikit account login instead.
    """
    _log("nitter_search: DEPRECATED — use twitter_search with twikit account login")
    return []


async def nitter_user_rss(username: str, limit: int = 20) -> list[dict]:
    """DEPRECATED: Nitter RSS fallback — all public instances shut down early 2024.
    Use twitter_user_tweets() with twikit account login instead.
    """
    _log("nitter_user_rss: DEPRECATED — use twitter_user_tweets with twikit account login")
    return []


# ── Farcaster scraper (free public API — no key needed) ───────────────────────

async def farcaster_search(query: str, limit: int = 20) -> list[dict]:
    """
    Search Farcaster casts. Uses public Neynar API free tier OR
    direct Warpcast/Hub API — no key needed for public reads.
    """
    # Approach 1: Neynar free tier (1000 req/day — register free at neynar.com)
    neynar_key = "NEYNAR_API_KEY"  # replace with your free key from neynar.com

    # Approach 2: Direct Farcaster Hub (truly free, no key)
    try:
        async with httpx.AsyncClient(headers=_headers({"Content-Type": "application/json"}), timeout=15) as client:
            # Warpcast public search API
            r = await client.get(
                "https://api.warpcast.com/v2/search-casts",
                params={"q": query, "limit": limit}
            )
            if r.status_code == 200:
                data = r.json()
                casts = data.get("result", {}).get("casts", [])
                return [
                    {
                        "source": "farcaster",
                        "text": c.get("text", ""),
                        "author": c.get("author", {}).get("username", ""),
                        "author_display": c.get("author", {}).get("displayName", ""),
                        "likes": c.get("reactions", {}).get("likes", 0),
                        "recasts": c.get("reactions", {}).get("recasts", 0),
                        "replies": c.get("replies", {}).get("count", 0),
                        "hash": c.get("hash", ""),
                        "created": c.get("timestamp", ""),
                        "url": f"https://warpcast.com/{c.get('author', {}).get('username', '')}/{c.get('hash', '')[:10]}",
                    }
                    for c in casts
                ]
    except Exception as e:
        _log(f"Farcaster Warpcast API error: {e}")

    # Approach 3: Searchcaster (community search API)
    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=10) as client:
            r = await client.get(f"https://searchcaster.xyz/api/search?text={query}&count={limit}")
            if r.status_code == 200:
                data = r.json()
                return [
                    {
                        "source": "farcaster_searchcaster",
                        "text": c.get("body", {}).get("data", {}).get("text", ""),
                        "author": c.get("meta", {}).get("username", ""),
                        "likes": c.get("meta", {}).get("reactions", {}).get("count", 0),
                        "created": c.get("body", {}).get("publishedAt", ""),
                    }
                    for c in data.get("casts", [])[:limit]
                ]
    except Exception as e:
        _log(f"Searchcaster error: {e}")

    return []


# ── RSS feeds (100% free — no auth, no rate limits) ───────────────────────────

_RSS_FEEDS = {
    "bankless": "https://bankless.ghost.io/rss/",
    "defiant": "https://thedefiant.io/feed",
    "decrypt": "https://decrypt.co/feed",
    "coindesk": "https://coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "cointelegraph": "https://cointelegraph.com/rss",
    "messari": "https://messari.io/rss/news.xml",
    "delphi_digital": "https://members.delphidigital.io/feed/",
    "reddit_defi": "https://www.reddit.com/r/defi/.rss",
    "reddit_crypto": "https://www.reddit.com/r/CryptoCurrency/.rss",
    "reddit_solana": "https://www.reddit.com/r/solana/.rss",
    "reddit_ethdev": "https://www.reddit.com/r/ethdev/.rss",
}


async def rss_fetch(feed_name: str = None, limit: int = 10) -> list[dict]:
    """Fetch from RSS feeds — 100% free, no auth, no rate limits. Uses built-in XML parser."""
    feeds_to_fetch = {feed_name: _RSS_FEEDS[feed_name]} if feed_name and feed_name in _RSS_FEEDS else _RSS_FEEDS
    results = []

    async with httpx.AsyncClient(
        headers=_headers({"Accept": "application/rss+xml, application/xml, text/xml, */*"}),
        timeout=10, follow_redirects=True
    ) as client:
        for name, url in feeds_to_fetch.items():
            try:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                items = _parse_rss_xml(r.text, limit)
                for it in items:
                    results.append({
                        "source": f"rss_{name}",
                        "feed": name,
                        "title": it["title"],
                        "summary": it["text"][:400],
                        "url": it["url"],
                        "author": it["author"],
                        "created": it["created"],
                    })
                await asyncio.sleep(0.2)
            except Exception as e:
                _log(f"RSS {name} error: {e}")

    return results[:limit * len(feeds_to_fetch)]


async def rss_keyword_filter(keyword: str, limit: int = 20) -> list[dict]:
    """Fetch all RSS feeds and filter by keyword."""
    all_items = await rss_fetch(limit=5)  # 5 per feed
    keyword_lower = keyword.lower()
    filtered = [
        item for item in all_items
        if keyword_lower in item.get("title", "").lower()
        or keyword_lower in item.get("summary", "").lower()
    ]
    return filtered[:limit]


# ── Multi-source intelligence sweep ───────────────────────────────────────────

async def full_intel_sweep(query: str, limit_per_source: int = 10) -> dict:
    """
    Run all scrapers simultaneously for a query.
    Returns unified results from Twitter, Reddit, Farcaster, RSS.
    """
    twitter_task = asyncio.create_task(twitter_search(query, limit_per_source))
    reddit_task = asyncio.create_task(reddit_search(query, limit=limit_per_source))
    farcaster_task = asyncio.create_task(farcaster_search(query, limit_per_source))
    rss_task = asyncio.create_task(rss_keyword_filter(query, limit_per_source))

    twitter_results, reddit_results, farcaster_results, rss_results = await asyncio.gather(
        twitter_task, reddit_task, farcaster_task, rss_task,
        return_exceptions=True
    )

    def safe(result, default=None):
        return result if not isinstance(result, Exception) else (default or [])

    all_results = (
        safe(twitter_results) +
        safe(reddit_results) +
        safe(farcaster_results) +
        safe(rss_results)
    )

    return {
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(all_results),
        "by_source": {
            "twitter": safe(twitter_results, []),
            "reddit": safe(reddit_results, []),
            "farcaster": safe(farcaster_results, []),
            "rss": safe(rss_results, []),
        },
        "combined_sorted": sorted(
            all_results,
            key=lambda x: x.get("score", x.get("likes", 0)),
            reverse=True,
        )[:limit_per_source * 4],
    }


# ── Competitor monitoring ──────────────────────────────────────────────────────

_COMPETITOR_QUERIES = {
    "nansen": "Nansen wallet analytics",
    "bubblemaps": "Bubblemaps on-chain",
    "arkham": "Arkham Intelligence crypto",
    "debank": "DeBank wallet tracker",
    "sybil": "sybil detection airdrop",
    "copy_trade": "copy trade detection crypto",
    "wallet_personality": "wallet personality crypto",
    "walletdna": "walletdna OR \"wallet dna\" OR \"wallet archetype\"",
}


async def competitor_sweep(competitor: str = None) -> dict:
    """Monitor competitors or keyword clusters across all platforms."""
    queries = (
        {competitor: _COMPETITOR_QUERIES[competitor]}
        if competitor and competitor in _COMPETITOR_QUERIES
        else _COMPETITOR_QUERIES
    )

    results = {}
    for key, query in queries.items():
        _log(f"Sweeping: {key}")
        results[key] = {
            "query": query,
            "reddit": await reddit_search(query, limit=5),
            "rss": await rss_keyword_filter(query, limit=5),
        }
        # Add Twitter only if twscrape works
        try:
            results[key]["twitter"] = await twitter_search(query, limit=5)
        except Exception:
            results[key]["twitter"] = []

        await asyncio.sleep(1)  # rate limit

    return results


# ── MCP JSON-RPC server ────────────────────────────────────────────────────────

_TOOLS = [
    {
        "name": "twitter_search",
        "description": "Search Twitter/X for tweets on any topic. Uses twscrape guest tokens — no account or API key needed. Falls back to Nitter RSS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "reddit_search",
        "description": "Search Reddit posts across Web3/DeFi subreddits. Uses public JSON API — no auth needed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "subreddits": {"type": "array", "items": {"type": "string"}, "description": "Optional list of subreddits"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "reddit_hot",
        "description": "Get hot/trending posts from a subreddit.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "subreddit": {"type": "string", "default": "defi"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": [],
        },
    },
    {
        "name": "farcaster_search",
        "description": "Search Farcaster (Web3 social network) for casts/posts. Free public API.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "rss_fetch",
        "description": "Fetch from crypto RSS feeds (Bankless, The Defiant, CoinDesk, Messari, etc). 100% free.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "feed_name": {
                    "type": "string",
                    "description": "Optional: specific feed. One of: bankless, defiant, decrypt, coindesk, cointelegraph, messari, reddit_defi, reddit_crypto, reddit_solana",
                },
                "limit": {"type": "integer", "default": 10},
            },
            "required": [],
        },
    },
    {
        "name": "rss_keyword_filter",
        "description": "Search all crypto RSS feeds for a keyword. Great for catching news about a topic.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "full_intel_sweep",
        "description": "Run a SIMULTANEOUS search across Twitter, Reddit, Farcaster, and RSS feeds for a query. Best for deep competitive research.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit_per_source": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "competitor_sweep",
        "description": "Monitor WalletDNA competitors (Nansen, Bubblemaps, Arkham, DeBank) and key topics (sybil, copy-trade) across all platforms.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "competitor": {
                    "type": "string",
                    "description": "Optional: specific competitor. One of: nansen, bubblemaps, arkham, debank, sybil, copy_trade, wallet_personality, walletdna",
                },
            },
            "required": [],
        },
    },
]

_TOOL_MAP = {
    "twitter_search": lambda args: twitter_search(args["query"], args.get("limit", 20)),
    "reddit_search": lambda args: reddit_search(args["query"], args.get("subreddits"), args.get("limit", 20)),
    "reddit_hot": lambda args: reddit_hot(args.get("subreddit", "defi"), args.get("limit", 10)),
    "farcaster_search": lambda args: farcaster_search(args["query"], args.get("limit", 20)),
    "rss_fetch": lambda args: rss_fetch(args.get("feed_name"), args.get("limit", 10)),
    "rss_keyword_filter": lambda args: rss_keyword_filter(args["keyword"], args.get("limit", 20)),
    "full_intel_sweep": lambda args: full_intel_sweep(args["query"], args.get("limit_per_source", 10)),
    "competitor_sweep": lambda args: competitor_sweep(args.get("competitor")),
}


async def handle_request(req: dict) -> dict | None:
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "walletdna-intel", "version": "1.0.0"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": _TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        _log(f"Calling tool: {tool_name} with {tool_args}")

        if tool_name not in _TOOL_MAP:
            return {
                "jsonrpc": "2.0", "id": req_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        try:
            result = await _TOOL_MAP[tool_name](tool_args)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}],
                },
            }
        except Exception as e:
            _log(f"Tool error: {e}")
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"error": str(e), "tool": tool_name})}],
                    "isError": True,
                },
            }

    if method == "notifications/initialized":
        return None  # no response needed

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


async def main() -> None:
    _log("WalletDNA Intel MCP server starting...")

    loop = asyncio.get_event_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        try:
            line = await reader.readline()
            if not line:
                break
            line = line.decode().strip()
            if not line:
                continue

            req = json.loads(line)
            resp = await handle_request(req)
            if resp is not None:
                _send(resp)
        except json.JSONDecodeError as e:
            _log(f"JSON decode error: {e}")
        except Exception as e:
            _log(f"Server error: {e}")
            break


if __name__ == "__main__":
    asyncio.run(main())
