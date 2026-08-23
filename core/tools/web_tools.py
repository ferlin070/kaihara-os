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


# ============================================================
# Marketing / Competitor Analysis Tools
# ============================================================

def analyze_competitor(url: str) -> str:
    """Analyze a competitor website: tech stack, SEO basics, content strategy."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with httpx.Client(timeout=25, follow_redirects=True,
                          headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        result: dict[str, Any] = {"url": url}

        # Title & meta
        result["title"] = soup.title.get_text(strip=True) if soup.title else ""
        desc = soup.find("meta", attrs={"name": "description"})
        result["meta_description"] = desc["content"][:200] if desc else ""

        # Tech stack detection (scripts, generators, frameworks)
        scripts = [s.get("src", "") for s in soup.find_all("script", src=True)]
        tech_hints = []
        tech_patterns = {
            "WordPress": [r"wp-content", r"wp-includes"],
            "Shopify": [r"shopify", r"cdn\.shopify"],
            "Wix": [r"wix\.com", r"parastorage"],
            "React": [r"react", r"__NEXT_DATA__"],
            "Next.js": [r"__NEXT_DATA__", r"next"],
            "Vue": [r"vue\.js", r"vue\.min\.js"],
            "Angular": [r"ng-version", r"angular"],
            "Bootstrap": [r"bootstrap\.min"],
            "Tailwind": [r"tailwindcss"],
            "Google Analytics": [r"google-analytics", r"gtag", r"ga\.js"],
            "Facebook Pixel": [r"fbevents", r"facebook\.net/en_US/fbevents"],
            "Hotjar": [r"hotjar"],
            "HubSpot": [r"hubspot"],
        }
        for tech, patterns in tech_patterns.items():
            for p in patterns:
                if re.search(p, html, re.IGNORECASE):
                    tech_hints.append(tech)
                    break
        result["tech_stack"] = list(set(tech_hints))

        # Social links
        social = {}
        for a in soup.find_all("a", href=True):
            href = a["href"]
            for platform in ["facebook.com", "instagram.com", "twitter.com",
                             "x.com", "linkedin.com", "tiktok.com", "youtube.com",
                             "shopee.com.my", "lazada.com.my"]:
                if platform in href:
                    social[platform.split(".")[0]] = href
        result["social_links"] = social

        # Content analysis
        h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")]
        result["headings"] = {"h1": h1s[:5], "h2": h2s[:8]}

        # Image alt text analysis (SEO)
        imgs = soup.find_all("img")
        imgs_with_alt = sum(1 for i in imgs if i.get("alt"))
        result["images_total"] = len(imgs)
        result["images_with_alt"] = imgs_with_alt
        result["alt_text_score"] = round(
            (imgs_with_alt / len(imgs) * 100) if imgs else 0, 1
        )

        # Page speed hints (rough: page size)
        result["page_size_kb"] = round(len(html.encode()) / 1024, 1)

        # Internal/external links
        base_domain = re.sub(r"^https?://([^/]+).*", r"\1", url)
        internal, external = 0, 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/") or base_domain in href:
                internal += 1
            elif href.startswith("http"):
                external += 1
        result["links"] = {"internal": internal, "external": external}

        # Contact info
        phones = sorted(set(re.findall(
            r"(?:\+?6?01\d[-\s]?\d{3,4}[-\s]?\d{4})"
            r"|(?:\+?6?0[3-9][-.\\s]?\d{7,8})", html)))[:4]
        emails = sorted(set(re.findall(
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", html)))[:4]
        result["contact"] = {"phones": phones, "emails": emails}

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"analyze_competitor failed: {e}"})


def social_monitor(query: str, max_results: int = 8) -> str:
    """Monitor social mentions via DuckDuckGo search."""
    try:
        # Search across social platforms
        platforms = ["twitter.com", "reddit.com", "facebook.com",
                     "instagram.com", "tiktok.com"]
        all_results = []

        for platform in platforms[:3]:  # Top 3 platforms
            query_site = f"site:{platform} {query}"
            try:
                results = _ddg_results(query_site, max_results=3)
                for r in results:
                    r["platform"] = platform.split(".")[0]
                all_results.extend(results)
            except Exception:
                continue

        # General mentions
        general = _ddg_results(f"{query} review OR opinion OR mentioned", max_results=4)
        for r in general:
            r["platform"] = "web"
        all_results.extend(general)

        return json.dumps({
            "query": query,
            "mentions": all_results[:max_results],
            "total_found": len(all_results),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"social_monitor failed: {e}"})


def seo_audit(url: str) -> str:
    """Basic SEO audit: title, meta, headings, images, structure."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        with httpx.Client(timeout=25, follow_redirects=True,
                          headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(url)
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        issues = []
        checks = []

        # Title
        title = soup.title.get_text(strip=True) if soup.title else ""
        if not title:
            issues.append("No <title> tag found")
        elif len(title) < 30:
            issues.append(f"Title too short ({len(title)} chars, aim for 50-60)")
        elif len(title) > 60:
            issues.append(f"Title too long ({len(title)} chars, aim for 50-60)")
        else:
            checks.append(f"Title length OK ({len(title)} chars)")

        # Meta description
        desc = soup.find("meta", attrs={"name": "description"})
        if not desc:
            issues.append("No meta description found")
        else:
            d = desc.get("content", "")
            if len(d) < 120:
                issues.append(f"Meta description too short ({len(d)} chars)")
            elif len(d) > 160:
                issues.append(f"Meta description too long ({len(d)} chars)")
            else:
                checks.append(f"Meta description OK ({len(d)} chars)")

        # H1 tags
        h1s = soup.find_all("h1")
        if len(h1s) == 0:
            issues.append("No H1 tag found")
        elif len(h1s) > 1:
            issues.append(f"Multiple H1 tags ({len(h1s)})")
        else:
            checks.append("Single H1 tag present")

        # Images without alt
        imgs = soup.find_all("img")
        no_alt = sum(1 for i in imgs if not i.get("alt"))
        if no_alt > 0:
            issues.append(f"{no_alt}/{len(imgs)} images missing alt text")
        elif imgs:
            checks.append("All images have alt text")

        # Canonical link
        canonical = soup.find("link", rel="canonical")
        if not canonical:
            issues.append("No canonical link tag")
        else:
            checks.append("Canonical link present")

        # Open Graph tags
        og_title = soup.find("meta", property="og:title")
        og_desc = soup.find("meta", property="og:description")
        og_image = soup.find("meta", property="og:image")
        if not all([og_title, og_desc, og_image]):
            missing = []
            if not og_title: missing.append("og:title")
            if not og_desc: missing.append("og:description")
            if not og_image: missing.append("og:image")
            issues.append(f"Missing Open Graph: {', '.join(missing)}")
        else:
            checks.append("Open Graph tags complete")

        # Robots
        robots = soup.find("meta", attrs={"name": "robots"})
        if robots:
            checks.append(f"Robots meta: {robots.get('content', '')}")

        # Structured data (JSON-LD)
        jsonld = soup.find_all("script", type="application/ld+json")
        if jsonld:
            checks.append(f"Structured data found ({len(jsonld)} blocks)")
        else:
            issues.append("No structured data (JSON-LD) found")

        # Page size
        size_kb = round(len(html.encode()) / 1024, 1)
        if size_kb > 500:
            issues.append(f"Large page size ({size_kb} KB)")
        else:
            checks.append(f"Page size OK ({size_kb} KB)")

        return json.dumps({
            "url": url,
            "score": max(0, 100 - len(issues) * 10),
            "issues": issues,
            "checks": checks,
            "title": title,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"seo_audit failed: {e}"})


def keyword_research(topic: str, max_results: int = 10) -> str:
    """Research keywords related to a topic via DuckDuckGo suggestions."""
    try:
        # Get related searches
        queries = [
            f"{topic} how to",
            f"{topic} tips",
            f"{topic} tutorial",
            f"{topic} guide",
            f"{topic} Malaysia",
            f"best {topic}",
            f"{topic} vs",
            f"{topic} review",
        ]
        all_results = []
        seen = set()

        for q in queries[:6]:
            try:
                results = _ddg_results(q, max_results=3)
                for r in results:
                    key = r["title"].lower()[:50]
                    if key not in seen:
                        seen.add(key)
                        r["keyword"] = q
                        all_results.append(r)
            except Exception:
                continue

        return json.dumps({
            "topic": topic,
            "keywords_found": len(all_results),
            "results": all_results[:max_results],
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"keyword_research failed: {e}"})
