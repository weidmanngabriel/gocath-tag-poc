"""RC public event listing importer, pagination and event-local text only."""
import re
import time
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup
from .regnum_scrape import LIST_URL
from .rc_delta import event_id, canonical_text

HEADERS={"User-Agent":"GoCathRCCatalog/1.0"}
HOSTS={"www.regnumchristi.eu","regnumchristi.eu"}

def url_id(url):
    try:return event_id({"url":url})
    except ValueError:return None

def following_pages(html):
    soup=BeautifulSoup(html,"html.parser")
    pages=set()
    for a in soup.select("a[href]"):
        url=urljoin(LIST_URL,a["href"])
        part=urlparse(url)
        if part.hostname not in HOSTS or part.path.rstrip("/")!="/demnaechst":continue
        query=parse_qs(part.query)
        if "vid" in query:continue
        if any(k in query for k in ("paged","page")) or "next" in a.get("rel",[]):
            pages.add(url)
    return pages

def event_container(anchor):
    node=anchor
    candidate=None
    for _ in range(12):
        node=node.parent
        if node is None:break
        if node.name not in ("div","article","li","section"):continue
        text=node.get_text(" ",strip=True)
        if not 100<=len(text)<=14000:continue
        count=sum(bool(url_id(urljoin(LIST_URL,a.get("href","")))) for a in node.select("a[href]"))
        if count>1:continue
        candidate=node
        if any(x in text for x in ("Adresse","Direktlink","Beginn:")):
            return node
    return candidate

def clean_text(text):
    text=re.sub(r"(?i)Sie haben einen Fehler entdeckt\?.*?Teilen Sie uns diesen bitte mit\.?"," ",text)
    text=re.sub(r"(?i)\b(?:last updated|last viewed|seitenaufrufe)\s*:?\s*\S+"," ",text)
    text=re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"," ",text)
    return canonical_text(text)

def parse_cards(html):
    soup=BeautifulSoup(html,"html.parser")
    events={}
    for a in soup.select("a[href]"):
        key=url_id(urljoin(LIST_URL,a.get("href","")))
        if not key:continue
        title=canonical_text(a.get_text(" ",strip=True))
        container=event_container(a)
        if not container or len(title)<3:continue
        text=clean_text(container.get_text(" ",strip=True))
        if len(text)<60:continue
        description=text.replace(title,"",1).strip()[:6500]
        audience=sorted(set(re.findall(r"Familien|Jugendliche[^,.;]{0,35}|Junge Männer[^,.;]{0,30}|Junge Frauen[^,.;]{0,30}|Paare & Ehepaare|Männer \(27\+\)|Frauen \(27\+\)|Kinder \(0-11\)|Jungen \(0-11\)|Mädchen \(0-11\)",text)))
        date=re.search(r"\b\d{1,2}\.\d{1,2}\.20\d{2}\b",text)
        address=re.search(r"\bAdresse\b\s+(.{1,100}?)(?:\b(?:Deutschland|Österreich|Sie haben|anmelden)\b|$)",text)
        events[key]={
            "url":"https://www.regnumchristi.eu/demnaechst/?vid="+key[3:],
            "title":title,"description":description,"target_groups":audience,
            "categories":[],"organizer":"",
            "location":canonical_text(address.group(1)) if address else "",
            "starts_at":date.group(0) if date else "", "ends_at":""}
    return events

def fetch_all_events(max_pages=30):
    if not 1<=max_pages<=100:raise ValueError("Invalid page limit")
    session=requests.Session()
    pending=[LIST_URL]
    visited=set()
    events={}
    try:
        while pending:
            if len(visited)>=max_pages:raise RuntimeError("Pagination bound reached; refusing partial sync")
            url=pending.pop(0)
            if url in visited:continue
            response=session.get(url,headers=HEADERS,timeout=35)
            response.raise_for_status()
            html=response.content.decode("utf-8-sig")
            found=parse_cards(html)
            if not found and not events:
                raise RuntimeError("RC listing returned no parseable event cards")
            events.update(found)
            visited.add(url)
            pending.extend(sorted(following_pages(html)-visited-set(pending)))
            time.sleep(0.12)
        if not events:raise RuntimeError("RC calendar empty")
        return list(events.values())
    finally:session.close()
