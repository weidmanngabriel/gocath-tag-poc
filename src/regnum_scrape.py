"""Public Regnum Christi calendar as an alternate event source.

The website exposes event links with a `vid` query parameter. The calendar
includes some archived entries; we retain dated future entries only.
"""
import re
import time
from datetime import date
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from .scrape import HEADERS

LIST_URL = "https://www.regnumchristi.eu/demnaechst/"

def event_links(html, limit=20):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for anchor in soup.select("a[href]"):
        url = urljoin(LIST_URL, anchor.get("href", ""))
        parts = urlparse(url)
        if (parts.netloc == "www.regnumchristi.eu" and parts.path.rstrip("/") == "/demnaechst"
                and "vid" in parse_qs(parts.query) and url not in links):
            links.append(url)
        if len(links) >= limit:
            break
    return links

def parse_event(html, url):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("h1")
    if not title or title.get_text(" ",strip=True).strip().upper()=="DEMNÄCHST":
        vid = parse_qs(urlparse(url).query).get("vid", [""])[0]
        anchor = next((a for a in soup.select("a[href]") if parse_qs(urlparse(urljoin(LIST_URL,a["href"])).query).get("vid", [""])[0]==vid), None)
        name = anchor.get_text(" ", strip=True) if anchor else ""
        node = anchor
        while node is not None and len(node.get_text(" ",strip=True)) < 250 and node.parent is not None:
            node = node.parent
        description = node.get_text(" ",strip=True)[:5500] if node else ""
    else:
        name = title.get_text(" ",strip=True)
        main = soup.select_one("main") or soup
        for el in main.select("script,style,nav,footer"):
            el.decompose()
        description = main.get_text(" ",strip=True)[:5500]
    return {"url":url, "title":name, "description":description}

def fetch_events(limit=20):
    session=requests.Session()
    try:
        def get(url):
            started=time.perf_counter()
            response=session.get(url,headers=HEADERS,timeout=30)
            print(f"[timing] regnum_source_get duration={time.perf_counter()-started:.3f}s http_status={response.status_code}",flush=True)
            response.raise_for_status()
            return response.text
        listing=get(LIST_URL)
        links=event_links(listing, max(limit*4,limit))
        if not links:
            raise RuntimeError("Keine Regnum-Christi-Veranstaltungslinks gefunden; Kalender-Markup prüfen.")
        events=[]
        for url in links:
            try:
                event=parse_event(listing,url)
                if event["title"] and event["description"]:
                    events.append(event)
            except requests.RequestException as exc:
                print("Warnung: Regnum Christi detail request "+type(exc).__name__,flush=True)
            if len(events)>=limit:break
        if not events:
            raise RuntimeError("Keine auswertbaren Regnum-Christi-Veranstaltungen gefunden.")
        return events
    finally:
        session.close()
