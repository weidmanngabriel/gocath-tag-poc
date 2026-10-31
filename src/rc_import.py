"""RC public event listing importer, pagination and event-local text only."""
import re
import time
from urllib.parse import urljoin, urlparse, parse_qs
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
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
    """Prefer an event-local DOM section, not the whole calendar."""
    node=anchor
    candidate=None
    for _ in range(15):
        node=node.parent
        if node is None:break
        if node.name not in ("div","article","li","section"):continue
        text=node.get_text(" ",strip=True)
        if not 60<=len(text)<=25000:continue
        ids={url_id(urljoin(LIST_URL,a.get("href",""))) for a in node.select("a[href]")}
        ids.discard(None)
        if len(ids)>1:continue
        candidate=node
        if any(x in text for x in ("Adresse","Direktlink","Beginn:")):
            return node
    return candidate

def following_event_text(anchor, key):
    """Fallback for JS calendar markup without semantic card containers.

    Read event-local text from the title link until the next distinct event.
    Never use the full page as an event description.
    """
    chunks=[]
    for node in anchor.next_elements:
        if isinstance(node,Tag):
            if node.name=="a" and url_id(urljoin(LIST_URL,node.get("href",""))) not in (None,key):
                break
            if node.name in ("script","style","footer","nav"):continue
        if isinstance(node,NavigableString):
            if node.parent and node.parent.name in ("script","style","nav","footer"):continue
            piece=canonical_text(node)
            if piece: chunks.append(piece)
            if sum(map(len,chunks))>8000:break
    return clean_text(" ".join(chunks))[:6500]

def clean_text(text):
    text=re.sub(r"(?i)Sie haben einen Fehler entdeckt\?.*?Teilen Sie uns diesen bitte mit\.?"," ",text)
    text=re.sub(r"(?i)\b(?:last updated|last viewed|seitenaufrufe)\s*:?\s*\S+"," ",text)
    text=re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"," ",text)
    return canonical_text(text)

def event_dates(text):
    """Extract the calendar's start and end dates, including shortened ranges."""
    from datetime import date
    pattern = re.compile(
        r"(?<!\d)(\d{1,2})\.(\d{1,2})\.\s*"
        r"(?:(20\d{2})\s*)?[-–]\s*"
        r"(\d{1,2})\.(\d{1,2})\.(20\d{2})(?!\d)"
    )
    match = pattern.search(text)
    if match:
        d1,m1,y1,d2,m2,y2=match.groups()
        end=date(int(y2),int(m2),int(d2))
        if y1 is not None:
            start=date(int(y1),int(m1),int(d1))
        else:
            year=int(y2) - (int(m1)>int(m2))
            start=date(year,int(m1),int(d1))
        if start>end:raise ValueError("RC event starts after end date")
        return start.isoformat(),end.isoformat()
    match=re.search(r"(?<!\\d)(\\d{1,2})\\.(\\d{1,2})\\.(20\\d{2})(?!\\d)",text)
    if not match:return "",""
    day,month,year=map(int,match.groups())
    return date(year,month,day).isoformat(),""

def parse_cards(html):
    soup=BeautifulSoup(html,"html.parser")
    events={}
    for a in soup.select("a[href]"):
        key=url_id(urljoin(LIST_URL,a.get("href","")))
        if not key:continue
        title=canonical_text(a.get_text(" ",strip=True))
        container=event_container(a)
        if len(title)<3 or title.casefold() in ('direktlink','anmelden','termin speichern'):continue
        if key in events:continue
        text=clean_text(container.get_text(" ",strip=True)) if container else following_event_text(a,key)
        if len(text)<60:text=following_event_text(a,key)
        if len(text)<60:continue
        description=text.replace(title,"",1).strip()[:6500]
        audience=sorted(set(re.findall(r"Familien|Jugendliche[^,.;]{0,35}|Junge Männer[^,.;]{0,30}|Junge Frauen[^,.;]{0,30}|Paare & Ehepaare|Männer \(27\+\)|Frauen \(27\+\)|Kinder \(0-11\)|Jungen \(0-11\)|Mädchen \(0-11\)",text)))
        start_date,end_date=event_dates(text)
        address=re.search(r"\bAdresse\b\s+(.{1,100}?)(?:\b(?:Deutschland|Österreich|Sie haben|anmelden)\b|$)",text)
        events[key]={
            "url":"https://www.regnumchristi.eu/demnaechst/?vid="+key[3:],
            "title":title,"description":description,"target_groups":audience,
            "categories":[],"organizer":"",
            "location":canonical_text(address.group(1)) if address else "",
            "starts_at":start_date, "ends_at":end_date}
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
