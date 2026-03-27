#!/usr/bin/env python3
"""
WalletDNA Intelligence MCP Server
==================================
Free, no-API-key scraping of Twitter/X, Reddit, Farcaster, RSS, and Web3 forums.

Techniques used:
  - Twitter: twscrape guest tokens (no account, no paid API)
  - Reddit:  public JSON API (no auth, 60 req/min)
  - Farcaster: Warpcast public Hub API (free, no key)
  - RSS: built-in XML parser on crypto news feeds (100% free)
  - Web: httpx + BeautifulSoup for forums (rotated UA headers)
  - Backup: Playwright browser automation for JS-heavy pages

Run as MCP server:
  python3 scripts/intel/intel_mcp_server.py

Or install as MCP in settings.json:
  "intel": {
    "command": "python3",
    "args": ["/home/user/walletdna/scripts/intel/intel_mcp_server.py"]
  }
"""

import asyncio
import json
import sys
import time
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import httpx

# MCP protocol over stdio

def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _log(msg: str) -> None:
    sys.stderr.write(f"[intel-mcp] {msg}\n")
    sys.stderr.flush()


# Browser-like headers (rotate to avoid blocks)

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
    }
    if extra:
        h.update(extra)
    return h


# RSS XML parser (zero deps — Python built-in)

def _parse_rss_xml(xml_text: str, limit: int = 20) -> list[dict]:
    """Parse RSS/Atom XML using Python's built-in xml.etree.ElementTree."""
    results = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}

        # RSS 2.0
        for item in root.findall(".//item")[:limit]:
            results.append({
                "title": (item.findtext("title") or "").strip(),
                "text": (item.findtext("description") or "").strip(),
                "author": (item.findtext("author") or item.findtext("dc:creator", "", ns) or "").strip(),
                "url": (item.findtext("link") or "").strip(),
                "created": (item.findtext("pubDate") or "").strip(),
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


# Reddit scraper (public JSON API — zero auth needed)

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
                        "created": datetime.fromtimestamp(d.get("created_utc", 0), tz=timezone.utc).isoformat(),
                    })
                await asyncio.sleep(0.5)
            except Exception as e:
                _log(f"Reddit error r/{sub}: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


async def reddit_hot(subreddit: str = "defi", limit: int = 10) -> list[dict]:
    """Get hot posts from a subreddit."""
    async with httpx.AsyncClient(headers=_headers(), follow_redirects=True, timeout=15) as client:
        try:
            r = await client.get(f"https://www.reddit.com/r/{subreddit}/hot.json", params={"limit": limit})
            if r.status_code != 200:
                return []
            data = r.json()
            return [
                {
                    "source": "reddit",
                    "subreddit": subreddit,
                    "title": p["data"].get("title", ""),
                    "body": (p["data"].get("selftext", "") or "")[:300],
                    "score": p["data"].get("score", 0),
                    "url": f"https://reddit.com{p['data'].get('permalink', '')}",
                    "created": datetime.fromtimestamp(p["data"].get("created_utc", 0), tz=timezone.utc).isoformat(),
                }
                for p in data.get("data", {}).get("children", [])
            ]
        except Exception as e:
            _log(f"Reddit hot error: {e}")
            return []


# Twitter/X scraper (twscrape guest tokens — no account, no paid API)

_NITTER_INSTANCES = [
    "nitter.net",
    "nitter.poast.org",
    "nitter.privacydev.net",
]


async def nitter_search(query: str, limit: int = 20) -> list[dict]:
    """Use Nitter RSS for Twitter search — no account, no API, open-source frontend."""
    for instance in _NITTER_INSTANCES:
        try:
            rss_url = f"https://{instance}/search/rss?q={query.replace(' ', '+')}&f=tweets"
            async with httpx.AsyncClient(headers=_headers(), timeout=10) as client:
                r = await client.get(rss_url)
                if r.status_code != 200:
                    continue
            items = _parse_rss_xml(r.text, limit)
            results = [
                {
                    "source": "twitter_nitter",
                    "title": it["title"],
                    "text": it["text"],
                    "author": it["author"],
                    "url": it["url"],
                    "created": it["created"],
                }
                for it in items
            ]
            _log(f"Nitter {instance}: {len(results)} results")
            return results
        except Exception as e:
            _log(f"Nitter {instance} failed: {e}")
    return []


async def nitter_user_rss(username: str, limit: int = 20) -> list[dict]:
    """Get user tweets via Nitter RSS."""
    for instance in _NITTER_INSTANCES:
        try:
            async with httpx.AsyncClient(headers=_headers(), timeout=10) as client:
                r = await client.get(f"https://{instance}/{username}/rss")
                if r.status_code != 200:
                    continue
            items = _parse_rss_xml(r.text, limit)
            return [
                {
                    "source": "twitter_nitter",
                    "text": it["text"] or it["title"],
                    "author": username,
                    "url": it["url"],
                    "created": it["created"],
                }
                for it in items
            ]
        except Exception as e:
            _log(f"Nitter RSS {instance}/{username} failed: {e}")
    return []


async def twitter_search(query: str, limit: int = 20, mode: str = "top") -> list[dict]:
    """
    Search Twitter via Nitter RSS (primary — no account, no API key).
    Falls back to twscrape if Nitter fails and accounts are configured.
    Note: twscrape requires logged-in accounts added via `twscrape add_accounts` since Jan 2025.
    """
    results = await nitter_search(query, limit)
    if results:
        return results
    _log("Nitter failed — trying twscrape (requires accounts configured)")
    try:
        from twscrape import API, gather
        api = API()
        tweets = await gather(api.search(query, limit=limit))
        results = []
        for t in tweets:
            results.append({
                "source": "twitter",
                "id": str(t.id),
                "text": t.rawContent,
                "author": t.user.username if t.user else "unknown",
                "author_name": t.user.displayname if t.user else "",
                "followers": t.user.followersCount if t.user else 0,
                "likes": t.likeCount,
                "retweets": t.retweetCount,
                "replies": t.replyCount,
                "created": t.date.isoformat() if t.date else "",
                "url": f"https://twitter.com/{t.user.username if t.user else 'i'}/status/{t.id}",
                "lang": t.lang,
            })
        return results
    except Exception as e:
        _log(f"twscrape error: {e}")
        return []


async def twitter_user_tweets(username: str, limit: int = 20) -> list[dict]:
    """Get recent tweets from a user. Falls back to Nitter RSS."""
    try:
        from twscrape import API, gather
        api = API()
        tweets = await gather(api.search(f"from:{username}", limit=limit))
        return [
            {
                "source": "twitter",
                "text": t.rawContent,
                "author": username,
                "likes": t.likeCount,
                "retweets": t.retweetCount,
                "created": t.date.isoformat() if t.date else "",
                "url": f"https://twitter.com/{username}/status/{t.id}",
            }
            for t in tweets
        ]
    except Exception as e:
        _log(f"twitter_user error: {e}")
        return await nitter_user_rss(username, limit)


# Farcaster scraper (free public API — no key needed)

async def farcaster_search(query: str, limit: int = 20) -> list[dict]:
    """Search Farcaster casts via Warpcast public API + Searchcaster fallback."""
    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=15) as client:
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
                        "hash": c.get("hash", ""),
                        "created": c.get("timestamp", ""),
                        "url": f"https://warpcast.com/{c.get('author', {}).get('username', '')}/{c.get('hash', '')[:10]}",
                    }
                    for c in casts
                ]
    except Exception as e:
        _log(f"Farcaster Warpcast error: {e}")

    # Fallback: Searchcaster
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


# RSS feeds (100% free — no auth, no rate limits)

_RSS_FEEDS = {
    "bankless": "https://bankless.ghost.io/rss/",
    "defiant": "https://thedefiant.io/feed",
    "decrypt": "https://decrypt.co/feed",
    "coindesk": "https://coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "cointelegraph": "https://cointelegraph.com/rss",
    # "messari": "https://messari.io/rss/news.xml",  # 429 rate-limited
    "reddit_defi": "https://www.reddit.com/r/defi/.rss",
    "reddit_crypto": "https://www.reddit.com/r/CryptoCurrency/.rss",
    "reddit_solana": "https://www.reddit.com/r/solana/.rss",
    "reddit_ethdev": "https://www.reddit.com/r/ethdev/.rss",
    "reddit_web3": "https://www.reddit.com/r/web3/.rss",
}


async def rss_fetch(feed_name: str = None, limit: int = 10) -> list[dict]:
    """Fetch from crypto RSS feeds. 100% free. Uses built-in XML parser."""
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

    return results


async def rss_keyword_filter(keyword: str, limit: int = 20) -> list[dict]:
    """Fetch all RSS feeds and filter by keyword."""
    all_items = await rss_fetch(limit=5)
    keyword_lower = keyword.lower()
    filtered = [
        item for item in all_items
        if keyword_lower in item.get("title", "").lower()
        or keyword_lower in item.get("summary", "").lower()
    ]
    return filtered[:limit]


# Multi-source intelligence sweep

async def full_intel_sweep(query: str, limit_per_source: int = 10) -> dict:
    """Run all scrapers simultaneously for a query."""
    twitter_task = asyncio.create_task(twitter_search(query, limit_per_source))
    reddit_task = asyncio.create_task(reddit_search(query, limit=limit_per_source))
    farcaster_task = asyncio.create_task(farcaster_search(query, limit_per_source))
    rss_task = asyncio.create_task(rss_keyword_filter(query, limit_per_source))

    twitter_r, reddit_r, farcaster_r, rss_r = await asyncio.gather(
        twitter_task, reddit_task, farcaster_task, rss_task,
        return_exceptions=True
    )

    def safe(r, d=None):
        return r if not isinstance(r, Exception) else (d or [])

    all_results = safe(twitter_r) + safe(reddit_r) + safe(farcaster_r) + safe(rss_r)

    return {
        "query": query,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(all_results),
        "by_source": {
            "twitter": safe(twitter_r, []),
            "reddit": safe(reddit_r, []),
            "farcaster": safe(farcaster_r, []),
            "rss": safe(rss_r, []),
        },
        "combined_sorted": sorted(
            all_results,
            key=lambda x: x.get("score", x.get("likes", 0)),
            reverse=True,
        )[:limit_per_source * 4],
    }


_COMPETITOR_QUERIES = {
    "nansen": "Nansen wallet analytics",
    "bubblemaps": "Bubblemaps on-chain",
    "arkham": "Arkham Intelligence crypto",
    "debank": "DeBank wallet tracker",
    "sybil": "sybil detection airdrop",
    "copy_trade": "copy trade detection crypto",
    "wallet_personality": "wallet personality crypto archetype",
    "walletdna": 'walletdna OR "wallet dna" OR "wallet archetype"',
}


async def competitor_sweep(competitor: str = None) -> dict:
    """Monitor competitors and key topic clusters across all platforms."""
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
        try:
            results[key]["twitter"] = await twitter_search(query, limit=5)
        except Exception:
            results[key]["twitter"] = []
        await asyncio.sleep(1)
    return results


# MCP JSON-RPC server

_TOOLS = [
    {
        "name": "twitter_search",
        "description": "Search Twitter/X for tweets. Uses twscrape guest tokens (no account/API key needed). Falls back to Nitter RSS.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["query"]},
    },
    {
        "name": "reddit_search",
        "description": "Search Reddit posts across Web3/DeFi subreddits. Public JSON API, no auth.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "subreddits": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "default": 20}}, "required": ["query"]},
    },
    {
        "name": "reddit_hot",
        "description": "Get hot/trending posts from a subreddit.",
        "inputSchema": {"type": "object", "properties": {"subreddit": {"type": "string", "default": "defi"}, "limit": {"type": "integer", "default": 10}}, "required": []},
    },
    {
        "name": "farcaster_search",
        "description": "Search Farcaster (Web3 social) for casts. Free public API.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["query"]},
    },
    {
        "name": "rss_fetch",
        "description": "Fetch crypto RSS feeds (Bankless, Defiant, CoinDesk, Messari, Reddit subs). 100% free.",
        "inputSchema": {"type": "object", "properties": {"feed_name": {"type": "string", "description": "bankless|defiant|decrypt|coindesk|cointelegraph|messari|reddit_defi|reddit_crypto|reddit_solana|reddit_ethdev"}, "limit": {"type": "integer", "default": 10}}, "required": []},
    },
    {
        "name": "rss_keyword_filter",
        "description": "Search all crypto RSS feeds for a keyword.",
        "inputSchema": {"type": "object", "properties": {"keyword": {"type": "string"}, "limit": {"type": "integer", "default": 20}}, "required": ["keyword"]},
    },
    {
        "name": "full_intel_sweep",
        "description": "SIMULTANEOUS search across Twitter, Reddit, Farcaster, and RSS feeds. Best for deep competitive research.",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit_per_source": {"type": "integer", "default": 10}}, "required": ["query"]},
    },
    {
        "name": "competitor_sweep",
        "description": "Monitor WalletDNA competitors (Nansen, Bubblemaps, Arkham, DeBank) and key topics across all platforms.",
        "inputSchema": {"type": "object", "properties": {"competitor": {"type": "string", "description": "nansen|bubblemaps|arkham|debank|sybil|copy_trade|wallet_personality|walletdna"}}, "required": []},
    },
]

_TOOL_MAP = {
    "twitter_search": lambda a: twitter_search(a["query"], a.get("limit", 20)),
    "reddit_search": lambda a: reddit_search(a["query"], a.get("subreddits"), a.get("limit", 20)),
    "reddit_hot": lambda a: reddit_hot(a.get("subreddit", "defi"), a.get("limit", 10)),
    "farcaster_search": lambda a: farcaster_search(a["query"], a.get("limit", 20)),
    "rss_fetch": lambda a: rss_fetch(a.get("feed_name"), a.get("limit", 10)),
    "rss_keyword_filter": lambda a: rss_keyword_filter(a["keyword"], a.get("limit", 20)),
    "full_intel_sweep": lambda a: full_intel_sweep(a["query"], a.get("limit_per_source", 10)),
    "competitor_sweep": lambda a: competitor_sweep(a.get("competitor")),
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
        _log(f"Calling: {tool_name}")
        if tool_name not in _TOOL_MAP:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}
        try:
            result = await _TOOL_MAP[tool_name](tool_args)
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]},
            }
        except Exception as e:
            _log(f"Tool error: {e}")
            return {
                "jsonrpc": "2.0", "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps({"error": str(e), "tool": tool_name})}], "isError": True},
            }

    if method == "notifications/initialized":
        return None

    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


async def main() -> None:
    """
    MCP stdio server loop — cross-platform (Windows ProactorEventLoop compatible).
    connect_read_pipe crashes on Windows IOCP; run_in_executor works on all platforms.
    """
    _log("WalletDNA Intel MCP server starting...")
    loop = asyncio.get_event_loop()
    while True:
        try:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            line = line.strip()
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
