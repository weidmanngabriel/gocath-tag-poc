"""Read only publicly available GoCath event webpages."""
import re
import time
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

# These site-wide blocks are navigation, not evidence about the event.
RELATED_MARKERS = ("Ähnliche Veranstaltungen", "Mehr zum Thema")
BOILERPLATE = (
    "Google Maps kann aufgrund Deiner Datenschutzeinstellungen leider nicht angezeigt werden. Bitte akzeptiere die Cookies.",
    "Cookie akzeptieren",
    "Alle Angaben ohne Gewähr. Bitte prüfe Datum, Uhrzeit und Ort vor dem Besuch auf der offiziellen Veranstaltungsseite.",
    "Fehler melden",
)

def clean_event_text(text):
    """Remove exact GoCath navigation/cookie copy without editing event facts.

    Do not guess at semantic content: dates, locations, organiser names,
    liturgy, audience and the complete event body are deliberately retained.
    """
    for marker in RELATED_MARKERS:
        at = text.find(marker)
        if at != -1:
            text = text[:at]
    for fragment in BOILERPLATE:
        text = text.replace(fragment, " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def parse_event(html, url, *, clean=True, truncate=True):
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
    text = main.get_text(" ", strip=True)
    description = clean_event_text(text) if clean else text
    if truncate:
        description = description[:5500]
    return {"url": url, "title": name, "description": description}

def fetch_events(limit=20, *, clean=True, truncate=True):
    session = requests.Session()
    def html(url):
        t0 = time.perf_counter()
        res = session.get(url, timeout=30, headers=HEADERS)
        print(f"[timing] source_get duration={time.perf_counter()-t0:.3f}s http_status={res.status_code}",flush=True)
        res.raise_for_status()
        return res.content.decode("utf-8-sig")
    try:
        links = event_links(html(LIST_URL), limit)
        if not links:
            raise RuntimeError("Keine Event-Links gefunden. GoCath-Markup prüfen.")
        out = []
        for url in links:
            try:
                event = parse_event(html(url), url, clean=clean, truncate=truncate)
                if event["title"]:
                    out.append(event)
            except requests.RequestException as exc:
                print(f"Warnung: {url}: {type(exc).__name__}")
        if not out:
            raise RuntimeError("Keine auswertbaren Event-Detailseiten.")
        return out
    finally:
        session.close()
