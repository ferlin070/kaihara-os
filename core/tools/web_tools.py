"""
Web Tools - real scraping + search for Kaihara agents.
- web_search: DuckDuckGo HTML search (no API key needed)
- scrape_website: fetch page, extract clean text/tables/contacts/links
- search_places: business/place search (Google Maps + DDG fallback)
"""

import re
import json
from typing import Any
from urllib.parse import unquote, quote_plus

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _clean_text(soup: BeautifulSoup, max_chars: int = 6000) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "noscript", "iframe", "svg"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", text)[:max_chars]


def _ddg_results(query: str, max_results: int = 8) -> list[dict]:
    resp = httpx.post(
        "https://html.duckduckgo.com/html/",
        data={"q": query},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
        follow_redirects=True,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for i, res in enumerate(soup.select(".result")[:max_results]):
        a = res.select_one("a.result__a")
        snippet = res.select_one(".result__snippet")
        if not a:
            continue
        url = a.get("href", "")
        m = re.search(r"uddg=([^&]+)", url)
        if m:
            url = unquote(m.group(1))
        results.append({
            "rank": i + 1,
            "title": a.get_text(strip=True),
            "url": url,
            "snippet": snippet.get_text(" ", strip=True)[:250] if snippet else "",
        })
    return results


def web_search(query: str, max_results: int = 8) -> str:
    """Search the web via DuckDuckGo. Returns structured JSON results."""
    try:
        results = _ddg_results(query, max_results)
        note = "" if results else "No results found"
        return json.dumps({"query": query, "results": results,
                           "note": note}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"web_search failed: {e}"})


def scrape_website(url: str, max_chars: int = 8000,
                   include_links: bool = True) -> str:
    """Scrape a webpage: title, clean text, tables, phones/emails, links."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with httpx.Client(timeout=25, follow_redirects=True,
                          headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else ""
        out: dict[str, Any] = {"url": url, "title": title}

        tables = []
        for t in soup.find_all("table")[:3]:
            rows = []
            for tr in t.find_all("tr")[:15]:
                cells = [c.get_text(" ", strip=True)
                         for c in tr.find_all(["td", "th"])]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(rows)
        if tables:
            out["tables"] = tables

        # Malaysian contact patterns
        phones = sorted(set(re.findall(
            r"(?:\+?6?01\d[-\s]?\d{3,4}[-\s]?\d{4})"
            r"|(?:\+?6?0[3-9][-.\\s]?\d{7,8})", html)))[:6]
        emails = sorted(set(re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)))[:6]
        if phones:
            out["phones_found"] = phones
        if emails:
            out["emails_found"] = emails

        if include_links:
            base_domain = re.sub(r"^https?://([^/]+).*", r"\1", url)
            links = []
            for a in soup.find_all("a", href=True)[:40]:
                href = a["href"]
                text = a.get_text(strip=True)[:60]
                if href.startswith("/"):
                    href = f"https://{base_domain}{href}"
                if href.startswith("http") and text:
                    links.append({"text": text, "url": href})
            out["links"] = links[:20]

        out["content"] = _clean_text(soup, max_chars)
        return json.dumps(out, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"scrape failed for {url}: {e}"})


def search_places(query: str, max_results: int = 10) -> str:
    """Search businesses/places. Google Maps page extraction + DDG fallback."""
    try:
        maps_url = ("https://www.google.com/maps/search/"
                    + quote_plus(query))
        places: list[dict] = []
        try:
            with httpx.Client(timeout=30, follow_redirects=True,
                              headers={"User-Agent": USER_AGENT}) as client:
                resp = client.get(maps_url)
                html = resp.text
            # Google embeds place data in JS arrays — extract name/address pairs
            entries = re.findall(
                r'\\"name\\":\\"([^"]{3,60}?)\\",.*?'
                r'\\"address\\":\\"([^"]{5,120}?)\\"', html)
            seen = set()
            for name, addr in entries:
                name = name.encode().decode("unicode_escape", errors="ignore")
                addr = addr.encode().decode("unicode_escape", errors="ignore")
                if name not in seen and "besut" not in name.lower() * 0:
                    seen.add(name)
                    places.append({"name": name, "address": addr})
                if len(places) >= max_results:
                    break
        except Exception:
            pass

        # Fallback / enrichment via DDG
        if len(places) < 3:
            ddg = _ddg_results(f"{query} alamat telefon", max_results)
            for r in ddg:
                places.append({"name": r["title"], "source": r["url"],
                               "snippet": r["snippet"]})

        return json.dumps({"query": query,
                           "results": places[:max_results]},
                          ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"search_places failed: {e}"})
