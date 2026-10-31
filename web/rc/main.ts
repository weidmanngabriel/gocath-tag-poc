import "./style.css";
type Score={id:string,category:string,label:string,score:number,matched:boolean,answer?:{probabilities?:{value:string,probability:number}[]}};
type Event={id:string,event:{title:string,description:string,url:string,location?:string,starts_at?:string},inactive?:boolean,stale?:boolean,classification?:{scores:Score[],relevance:{status:string,score:number}}};
const SOURCE="https://raw.githubusercontent.com/weidmanngabriel/gocath-tag-poc/rc-data/public.json";
const root=document.querySelector<HTMLElement>("#app")!;
const esc=(s:unknown)=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]||c));
const parseDate=(v:string)=>{const m=/^(\\d{1,2})\\.(\\d{1,2})\\.(\\d{4})$/.exec(v||"");return m?`${m[3]}-${m[2].padStart(2,"0")}-${m[1].padStart(2,"0")}`:v||"9999";};
const pct=(n:number)=>Math.round((n||0)*100)+" %";
const status=(s:string)=>s==="likely_relevant"?"Wahrscheinlich relevant":s==="review"?"Prüfen":s==="likely_not_relevant"?"Eher nicht relevant":"Noch nicht klassifiziert";
let records:Event[]=[];
function scoreRow(s:Score){const distribution=s.answer?.probabilities||[];return `<div class="score"><div class="score-head"><span>${esc(s.label)}</span><b>${pct(s.score)}</b></div><div class="track"><div style="width:${Math.max(0,Math.min(100,s.score*100))}%"></div></div>${distribution.map(p=>`<small>${esc(p.value)}: ${pct(p.probability)}</small>`).join("")}</div>`;}
function card(item:Event){
 const c=item.classification;
 const groups=[...new Set((c?.scores||[]).map(s=>s.category))].sort((a,b)=>a.localeCompare(b,"de"));
 const hits=(c?.scores||[]).filter(s=>s.matched).sort((a,b)=>b.score-a.score).slice(0,4);
 return `<article class="card"><div class="top"><div><h2>${esc(item.event.title)}</h2><p>${esc(item.event.location||"")} ${esc(item.event.starts_at||"")}</p></div><span class="status">${status(c?.relevance.status||"")} ${c?pct(c.relevance.score):""}</span></div><div class="chips">${hits.map(s=>`<span>${esc(s.label)} · ${pct(s.score)}</span>`).join("")}</div><details><summary>Einzelbewertungen ansehen</summary>${item.stale?"<p>Veranstaltung geändert – Neubewertung ausstehend.</p>":""}<p>${esc(item.event.description)}</p><a href="${esc(item.event.url)}" target="_blank" rel="noopener noreferrer">Originalveranstaltung öffnen</a>${groups.map(g=>`<section><h3>${esc(g)}</h3>${c?.scores.filter(s=>s.category===g).sort((a,b)=>b.score-a.score).map(scoreRow).join("")||""}</section>`).join("")}</details></article>`;
}
function display(){
 const q=(document.querySelector<HTMLInputElement>("#q")?.value||"").toLocaleLowerCase("de");
 const relevance=document.querySelector<HTMLSelectElement>("#relevance")?.value||"";
 const category=document.querySelector<HTMLSelectElement>("#category")?.value||"";
 const criterion=document.querySelector<HTMLSelectElement>("#criterion")?.value||"";
 const sort=document.querySelector<HTMLSelectElement>("#sort")?.value||"title";
 const filtered=records.filter(e=>!e.inactive&&(!q||[e.event.title,e.event.description,e.event.location].join(" ").toLocaleLowerCase("de").includes(q))&&(!relevance||e.classification?.relevance.status===relevance)&&(!category||e.classification?.scores.some(s=>s.category===category&&s.matched))&&(!criterion||e.classification?.scores.some(s=>s.id===criterion&&s.matched)));
 filtered.sort((a,b)=>sort==="score"?(b.classification?.relevance.score||0)-(a.classification?.relevance.score||0):sort==="date"?parseDate(a.event.starts_at||"").localeCompare(parseDate(b.event.starts_at||"")):(a.event.title||"").localeCompare(b.event.title||"","de"));
 document.querySelector<HTMLElement>("#count")!.textContent=`${filtered.length} von ${records.filter(e=>!e.inactive).length} Veranstaltungen`;
 document.querySelector<HTMLElement>("#results")!.innerHTML=filtered.map(card).join("")||"<p>Keine Veranstaltungen gefunden.</p>";
}
async function init(){
 root.innerHTML=`<div class="shell"><header><a href="../">GoCath</a><h1>RC Veranstaltungen</h1><p>Öffentliche KI-Einordnung mit allen Einzelwerten. Modellschätzungen, keine redaktionelle Bewertung.</p></header><div class="filters"><input id="q" type="search" placeholder="Veranstaltung suchen" aria-label="Suche"/><select id="relevance" aria-label="Relevanz"><option value="">Alle Relevanzstufen</option><option value="likely_relevant">Wahrscheinlich relevant</option><option value="review">Prüfen</option><option value="likely_not_relevant">Eher nicht relevant</option></select><select id="category" aria-label="Bereich"><option value="">Alle Bereiche</option></select><select id="criterion" aria-label="Merkmal"><option value="">Alle Merkmale</option></select><select id="sort" aria-label="Sortierung"><option value="title">Alphabetisch</option><option value="score">Nach Relevanz</option><option value="date">Nach Datum</option></select></div><p id="count"></p><section id="results">Daten werden geladen …</section><footer>Quelle: <a href="https://www.regnumchristi.eu/demnaechst/">Regnum Christi</a></footer></div>`;
 try{
 const response=await fetch(SOURCE+"?v="+Math.floor(Date.now()/60000),{cache:"no-store"});
 if(!response.ok)throw Error("Katalog noch nicht veröffentlicht ("+response.status+")");
 const json=await response.json() as {events:Event[]};
 if(!Array.isArray(json.events))throw Error("Ungültiges Datenformat");
 records=json.events;
 const categories=[...new Set(records.flatMap(e=>e.classification?.scores.map(s=>s.category)||[]))].sort((a,b)=>a.localeCompare(b,"de"));
 document.querySelector<HTMLSelectElement>("#category")!.innerHTML+=categories.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join("");
 const criteria=new Map<string,string>();
 records.forEach(e=>e.classification?.scores.forEach(v=>criteria.set(v.id,v.category+" · "+v.label)));
 document.querySelector<HTMLSelectElement>("#criterion")!.innerHTML+=[...criteria.entries()].sort((a,b)=>a[1].localeCompare(b[1],"de")).map(([id,label])=>`<option value="${esc(id)}">${esc(label)}</option>`).join("");
 document.querySelectorAll<HTMLInputElement|HTMLSelectElement>(".filters input,.filters select").forEach(el=>el.addEventListener("input",display));
 display();
 }catch(error){document.querySelector<HTMLElement>("#results")!.textContent="Katalog noch nicht verfügbar: "+String(error);}
}
init();
