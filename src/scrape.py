"""Read only publicly available GoCath event webpages."""
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE = "https://gocath.org"
LIST_URL = BASE + "/de/finde"
HEADERS = {"User-Agent": "GoCathTagPOC/1.0"}

def event_links(html, limit):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a[href]"):
        u = urljoin(BASE, a["href"])
        if re.match(r"^/(de/)?event/[^/]+/?$", urlparse(u).path) and u not in links:
            links.append(u)
        if len(links) >= limit:
            break
    return links

def parse_event(html, url):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main") or soup
    title = main.find("h1")
    if not title:
        meta = soup.find("meta", attrs={"property": "og:title"})
        name = meta.get("content", "") if meta else ""
    else:
        name = title.get_text(" ", strip=True)
    for node in main.select("script,style,nav,footer"):
        node.decompose()
    description = main.get_text(" ", strip=True)[:5500]
    return {"url": url, "title": name, "description": description}

def fetch_events(limit=20):
    session = requests.Session()
    def html(url):
        res = session.get(url, timeout=30, headers=HEADERS)
        res.raise_for_status()
        return res.text
    try:
        links = event_links(html(LIST_URL), limit)
        if not links:
            raise RuntimeError("Keine Event-Links gefunden. GoCath-Markup prüfen.")
        out = []
        for url in links:
            try:
                event = parse_event(html(url), url)
                if event["title"]:
                    out.append(event)
            except requests.RequestException as exc:
                print(f"Warnung: {url}: {type(exc).__name__}")
        if not out:
            raise RuntimeError("Keine auswertbaren Event-Detailseiten.")
        return out
    finally:
        session.close()
