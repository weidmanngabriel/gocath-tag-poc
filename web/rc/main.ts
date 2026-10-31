import "./style.css";
type Score={id:string,category:string,label:string,score:number,matched:boolean,answer?:{probabilities?:{value:string,probability:number}[]}};
type Event={id:string,event:{title:string,description:string,url:string,location?:string,starts_at?:string},inactive?:boolean,stale?:boolean,classification?:{scores:Score[],relevance:{status:string,score:number}}};
const SOURCE="https://raw.githubusercontent.com/weidmanngabriel/gocath-tag-poc/rc-data/public.json";
const root=document.querySelector<HTMLElement>("#app")!;
const esc=(s:unknown)=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]||c));
const pct=(n:number)=>Math.round((n||0)*100)+" %";
const status=(s:string)=>s==="likely_relevant"?"Wahrscheinlich relevant":s==="review"?"Prüfen":s==="likely_not_relevant"?"Eher nicht relevant":"Noch nicht klassifiziert";
let records:Event[]=[];
function scoreRow(s:Score){const distribution=s.answer?.probabilities||[];return `<div class="score"><div class="score-head"><span>${esc(s.label)}</span><b>${pct(s.score)}</b></div><div class="track"><div style="width:${Math.max(0,Math.min(100,s.score*100))}%"></div></div>${distribution.map(p=>`<small>${esc(p.value)}: ${pct(p.probability)}</small>`).join("")}</div>`;}
function card(item:Event){
 const c=item.classification;
 const groups=[...new Set((c?.scores||[]).map(s=>s.category))].sort((a,b)=>a.localeCompare(b,"de"));
 const hits=(c?.scores||[]).filter(s=>s.matched).sort((a,b)=>b.score-a.score).slice(0,4);
 const tabs=[...groups,"Beschreibung"];
 const buttons=tabs.map((g,i)=>`<button type="button" role="tab" id="tab-${esc(item.id)}-${i}" aria-controls="panel-${esc(item.id)}-${i}" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-tab="${i}">${esc(g)}</button>`).join("");
 const panels=tabs.map((g,i)=>`<div role="tabpanel" id="panel-${esc(item.id)}-${i}" aria-labelledby="tab-${esc(item.id)}-${i}" ${i!==0?"hidden":""}>${g==="Beschreibung"?`<p class="description">${esc(item.event.description||"Keine Beschreibung verfügbar.")}</p><a href="${esc(item.event.url)}" target="_blank" rel="noopener noreferrer">Originalveranstaltung öffnen</a>`:(c?.scores.filter(s=>s.category===g).sort((a,b)=>b.score-a.score).map(scoreRow).join("")||"<p>Keine Bewertung verfügbar.</p>")}</div>`).join("");
 return `<article class="card"><div class="top"><div><h2>${esc(item.event.title)}</h2><p>${esc(item.event.location||"")} ${esc(item.event.starts_at||"")}</p></div><span class="status">${status(c?.relevance.status||"")} ${c?pct(c.relevance.score):""}</span></div><div class="chips">${hits.map(s=>`<span>${esc(s.label)} · ${pct(s.score)}</span>`).join("")}</div><details><summary>Einzelbewertungen ansehen</summary>${item.stale?"<p>Veranstaltung geändert – Neubewertung ausstehend.</p>":""}<div class="item-tabs" role="tablist" aria-label="Details zur Veranstaltung">${buttons}</div><div class="item-panels">${panels}</div></details></article>`;
}
function switchItemTab(button:HTMLButtonElement,focus=false){
 const tabs=button.closest<HTMLElement>(".item-tabs");
 const card=button.closest<HTMLElement>(".card");
 if(!tabs||!card)return;
 const selected=button.dataset.tab;
 tabs.querySelectorAll<HTMLButtonElement>('[role="tab"]').forEach(tab=>{
   const active=tab===button;
   tab.setAttribute("aria-selected",String(active));
   tab.tabIndex=active?0:-1;
 });
 card.querySelectorAll<HTMLElement>('[role="tabpanel"]').forEach(panel=>{
   panel.hidden=panel.id!==button.getAttribute("aria-controls");
 });
 if(focus)button.focus();
}

function display(){
 const q=(document.querySelector<HTMLInputElement>("#q")?.value||"").toLocaleLowerCase("de");
 const relevance=document.querySelector<HTMLSelectElement>("#relevance")?.value||"";
 const selected=new Set(Array.from(document.querySelectorAll<HTMLInputElement>(".criterion-options input:checked")).map(el=>el.value));
 const sort=document.querySelector<HTMLSelectElement>("#sort")?.value||"date";
 const filtered=records.filter(e=>!e.inactive&&(!q||[e.event.title,e.event.description,e.event.location].join(" ").toLocaleLowerCase("de").includes(q))&&(!relevance||e.classification?.relevance.status===relevance)&&(!selected.size||e.classification?.scores.some(s=>selected.has(s.id)&&s.matched)));
 filtered.sort((a,b)=>sort==="score"?(b.classification?.relevance.score||0)-(a.classification?.relevance.score||0):sort==="date"?(a.event.starts_at||"9999").localeCompare(b.event.starts_at||"9999"):(a.event.title||"").localeCompare(b.event.title||"","de"));
 document.querySelector<HTMLElement>("#count")!.textContent=`${filtered.length} von ${records.filter(e=>!e.inactive).length} Veranstaltungen`;
 document.querySelector<HTMLElement>("#results")!.innerHTML=filtered.map(card).join("")||"<p>Keine Veranstaltungen gefunden.</p>";
}
async function init(){
 root.innerHTML=`<div class="shell"><header><a href="../">GoCath</a><h1>RC Veranstaltungen</h1><p>Öffentliche KI-Einordnung mit allen Einzelwerten. Modellschätzungen, keine redaktionelle Bewertung.</p></header><section class="purpose"><h2>Damit deine Veranstaltung besser gefunden wird</h2><p>Dieses Tool hilft dir dabei, deine Veranstaltung so zu beschreiben, dass Interessierte sie leichter finden – zum Beispiel über Google, GoCath oder den RC-Kalender.</p><details><summary>Mehr dazu erfahren</summary><p>Eine KI prüft, ob aus deinem Veranstaltungstext klar hervorgeht, worum es geht und für wen die Veranstaltung gedacht ist.</p><p><strong>Wichtig:</strong> Hier wird nicht die Qualität deiner Veranstaltung bewertet. Niedrige Werte können einfach bedeuten, dass wichtige Informationen in der Beschreibung fehlen. Die KI kann sich auch irren.</p></details><p class="purpose-meta">Die Liste wird derzeit manuell aktualisiert. Eine stündliche Aktualisierung ist geplant, aber noch nicht aktiviert.</p><p class="purpose-contact">Fragen oder Rückmeldungen? Gabriel Weidmann · <a href="mailto:gweidmann@regnumchristi.eu">gweidmann@regnumchristi.eu</a></p></section><div class="filters"><input id="q" type="search" placeholder="Veranstaltung suchen" aria-label="Suche"/><select id="relevance" aria-label="Relevanz"><option value="">Alle Relevanzstufen</option><option value="likely_relevant">Wahrscheinlich relevant</option><option value="review">Prüfen</option><option value="likely_not_relevant">Eher nicht relevant</option></select><details class="criterion-filter" id="criterion-filter"><summary>Kriterien auswählen <span id="filter-count"></span></summary><div class="criterion-options" id="criterion-options"></div><button type="button" id="clear-criteria">Auswahl löschen</button></details><select id="sort" aria-label="Sortierung"><option value="date">Nach Datum</option><option value="score">Nach Relevanz</option><option value="title">Alphabetisch</option></select></div><p id="count"></p><section id="results">Daten werden geladen …</section><footer>Quelle: <a href="https://www.regnumchristi.eu/demnaechst/">Regnum Christi</a></footer></div>`;
 try{
 const response=await fetch(SOURCE+"?v="+Math.floor(Date.now()/60000),{cache:"no-store"});
 if(!response.ok)throw Error("Katalog noch nicht veröffentlicht ("+response.status+")");
 const json=await response.json() as {events:Event[]};
 if(!Array.isArray(json.events))throw Error("Ungültiges Datenformat");
 records=json.events;
 const criteria=new Map<string,{category:string,label:string}>();
 records.forEach(e=>e.classification?.scores.forEach(score=>criteria.set(score.id,{category:score.category,label:score.label})));
 const groups=new Map<string,Array<[string,string]>>();
 criteria.forEach((c,id)=>{if(!groups.has(c.category))groups.set(c.category,[]);groups.get(c.category)!.push([id,c.label]);});
 document.querySelector<HTMLElement>("#criterion-options")!.innerHTML=Array.from(groups.entries()).sort((a,b)=>a[0].localeCompare(b[0],"de")).map(([group,items])=>`<fieldset><legend>${esc(group)}</legend>${items.sort((a,b)=>a[1].localeCompare(b[1],"de")).map(([id,label])=>`<label><input type="checkbox" value="${esc(id)}"/><span>${esc(label)}</span></label>`).join("")}</fieldset>`).join("");
 document.querySelector<HTMLElement>("#criterion-options")!.addEventListener("change",()=>{const count=document.querySelectorAll(".criterion-options input:checked").length;document.querySelector<HTMLElement>("#filter-count")!.textContent=count?`(${count})`:"";display();});
 document.querySelector<HTMLButtonElement>("#clear-criteria")!.addEventListener("click",()=>{document.querySelectorAll<HTMLInputElement>(".criterion-options input:checked").forEach(input=>input.checked=false);document.querySelector<HTMLElement>("#filter-count")!.textContent="";display();});
 document.querySelectorAll<HTMLInputElement|HTMLSelectElement>(".filters input,.filters select").forEach(el=>el.addEventListener("input",display));
 document.querySelector<HTMLElement>("#results")!.addEventListener("click",event=>{
   const button=(event.target as HTMLElement).closest<HTMLButtonElement>('[role="tab"]');
   if(button)switchItemTab(button);
 });
 document.querySelector<HTMLElement>("#results")!.addEventListener("keydown",event=>{
   if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
   const button=(event.target as HTMLElement).closest<HTMLButtonElement>('[role="tab"]');
   if(!button)return;
   const tabs=Array.from(button.closest<HTMLElement>(".item-tabs")!.querySelectorAll<HTMLButtonElement>('[role="tab"]'));
   const index=tabs.indexOf(button);
   const next=event.key==="Home"?0:event.key==="End"?tabs.length-1:(index+(event.key==="ArrowLeft"?-1:1)+tabs.length)%tabs.length;
   event.preventDefault();
   switchItemTab(tabs[next],true);
 });
 display();
 }catch(error){document.querySelector<HTMLElement>("#results")!.textContent="Katalog noch nicht verfügbar: "+String(error);}
}
init();
