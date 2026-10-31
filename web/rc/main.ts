import "./style.css";
type Score={id:string,category:string,label:string,score:number,matched:boolean,type?:string,answer?:{choice?:string,confidence?:number,score?:number,probabilities?:{value:string|number,label?:string,probability:number}[]}};
type Criterion={id:string,label:string,category:string,description?:string,type?:string,threshold?:number,weight?:number,options?:{value?:string,label?:string,description?:string}[]};
type Questionnaire={revision:string,published_at:string,criteria:Criterion[]};
type Event={id:string,event:{title:string,description:string,url:string,location?:string,starts_at?:string},inactive?:boolean,stale?:boolean,classification?:{scores:Score[],pending_criteria?:string[],questionnaire_revision?:string,relevance:{status:string,score:number}}};
const SOURCE="https://raw.githubusercontent.com/weidmanngabriel/gocath-tag-poc/rc-data/public.json";
const root=document.querySelector<HTMLElement>("#app")!;
const esc=(s:unknown)=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]||c));
const pct=(n:number)=>Math.round((n||0)*100)+" %";
const statusKind=(s:string)=>s==="likely_relevant"?"relevant":s==="review"?"review":s==="likely_not_relevant"?"irrelevant":"unknown";
const status=(s:string)=>s==="likely_relevant"?"Wahrscheinlich relevant":s==="review"?"Prüfen":s==="likely_not_relevant"?"Eher nicht relevant":"Noch nicht klassifiziert";
let records:Event[]=[];
let questionnaire:Questionnaire|null=null;
function scoreColor(s:Score):string {if(!Number.isFinite(s.score))return "unknown";if(!s.matched)return "irrelevant";return s.score>=0.8?"relevant":"review";}
function scoreRow(s:Score){const distribution=s.answer?.probabilities||[];return `<div class="score score-${scoreColor(s)}"><div class="score-head"><span>${esc(s.label)}</span><b>${pct(s.score)}</b></div><div class="track"><div style="width:${Math.max(0,Math.min(100,s.score*100))}%"></div></div>${distribution.map(p=>`<small>${esc(p.value)}: ${pct(p.probability)}</small>`).join("")}</div>`;}
function card(item:Event){
 const c=item.classification;
 const groups=[...new Set((c?.scores||[]).map(s=>s.category))].sort((a,b)=>a.localeCompare(b,"de"));
 const hits=(c?.scores||[]).filter(s=>s.type!=="choice"&&s.type!=="score"&&s.matched).sort((a,b)=>b.score-a.score);
 const nonPredicates=(c?.scores||[]).filter(s=>s.type==="choice"||s.type==="score");
 const groupOrder=questionnaire?[...new Set(questionnaire.criteria.map(c=>c.category))]:[];
 const matchedGroups=[...new Set([...hits,...nonPredicates].map(s=>s.category))].sort((a,b)=>{
  const ai=groupOrder.indexOf(a),bi=groupOrder.indexOf(b);
  return (ai<0?99:ai)-(bi<0?99:bi)||a.localeCompare(b,"de");
 });
 const groupedHits=matchedGroups.map(group=>{
  const entries=[...hits,...nonPredicates].filter(s=>s.category===group);
  const visible=entries.slice(0,2);
  const more=entries.slice(2);
  const chip=(s:Score)=>{
   if(s.type==="choice"){
    const choice=s.answer?.choice||"Nicht erkennbar";
    return `<span class="match-chip match-unknown">${esc(s.label)}: ${esc(choice)}</span>`;
   }
   if(s.type==="score"){
    const levels=questionnaire?.criteria.find(c=>c.id===s.id)?.options||[];
    const value=s.answer?.score;
    const index=typeof value==="number"?Math.max(0,Math.min(levels.length-1,Math.round(value))):-1;
    const selected=index>=0?levels[index]?.label:"Unbekannt";
    return `<span class="match-chip match-unknown">${esc(s.label)}: ${esc(selected)}</span>`;
   }
   return `<span class="match-chip match-${scoreColor(s)}">${esc(s.label)} · ${pct(s.score)}</span>`;
  };
  return `<section class="match-group" aria-label="${esc(group)}"><div class="match-group-heading"><strong>${esc(group)}</strong></div><div class="match-list">${visible.map(chip).join("")}${more.length?`<button type="button" class="match-expand" aria-label="${more.length} weitere Treffer in ${esc(group)} anzeigen">+${more.length}</button><span class="match-extra" hidden>${more.map(chip).join("")}</span>`:""}</div></section>`;
 }).join("");
 const pending=(questionnaire?.criteria||[]).filter(q=>(c?.pending_criteria||[]).includes(q.id));
 const tabs=[...new Set([...(questionnaire?.criteria.map(q=>q.category)||[]),...groups]),"Beschreibung"];
 const buttons=tabs.map((g,i)=>`<button type="button" role="tab" id="tab-${esc(item.id)}-${i}" aria-controls="panel-${esc(item.id)}-${i}" aria-selected="${i===0}" tabindex="${i===0?0:-1}" data-tab="${i}">${esc(g)}</button>`).join("");
 const panels=tabs.map((g,i)=>`<div role="tabpanel" id="panel-${esc(item.id)}-${i}" aria-labelledby="tab-${esc(item.id)}-${i}" ${i!==0?"hidden":""}>${g==="Beschreibung"?`<p class="description">${esc(item.event.description||"Keine Beschreibung verfügbar.")}</p><a href="${esc(item.event.url)}" target="_blank" rel="noopener noreferrer">Originalveranstaltung öffnen</a>`:((c?.scores.filter(s=>s.category===g).sort((a,b)=>b.score-a.score).map(scoreRow).join("")||"")+
 pending.filter(q=>q.category===g).map(q=>`<div class="score score-unknown"><div class="score-head"><span>${esc(q.label)}</span><small>Noch nicht bewertet</small></div></div>`).join("")+
 (!c?.scores.some(s=>s.category===g)&&!pending.some(q=>q.category===g)?"<p>Keine Bewertung verfügbar.</p>":""))}</div>`).join("");
 return `<article class="card"><div class="top"><div><h2>${esc(item.event.title)}</h2><p>${esc(item.event.location||"")} ${esc(item.event.starts_at||"")}</p></div></div><div class="matched-groups" aria-label="Erkannte Merkmale">${matchedGroups.length?groupedHits:`<p class="no-hits">${c?"Keine Kriterien oberhalb ihrer Trefferschwelle":"Noch keine Bewertung vorhanden"}</p>`}</div><details><summary>Einzelbewertungen ansehen</summary>${item.stale?"<p>Veranstaltung geändert – Neubewertung ausstehend.</p>":""}${pending.length?`<p class="pending-note">${pending.length} Kriterien noch nicht mit der aktuellen Konfiguration bewertet.</p>`:""}<div class="item-tabs" role="tablist" aria-label="Details zur Veranstaltung">${buttons}</div><div class="item-panels">${panels}</div></details></article>`;
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

function questionnaireView(q:Questionnaire|null){
 if(!q)return '<p>Der veröffentlichte Fragebogen ist noch nicht verfügbar. Bitte den RC-Katalog einmal im Modus „refresh“ aktualisieren.</p>';
 const date=new Date(q.published_at);
 const stamp=Number.isNaN(date.getTime())?"Unbekannt":date.toLocaleString("de-DE");
 const categories=[...new Set(q.criteria.map(c=>c.category))].sort((a,b)=>a.localeCompare(b,"de"));
 return `<p>Dies ist der zuletzt veröffentlichte Fragebogen, der für neue Bewertungen verwendet wird. Ältere Einzelbewertungen bleiben unverändert und können auf einer früheren Version beruhen. Änderungen am Fragebogen erfordern für neue Bewertungen einen eigenen Klassifizierungslauf.</p><p class="questionnaire-meta">Veröffentlicht: ${esc(stamp)} · ${q.criteria.length} aktive Kriterien · Revision: <code>${esc(q.revision.slice(0,12))}</code></p>${categories.map(category=>`<section class="questionnaire-group"><h3>${esc(category)}</h3>${q.criteria.filter(c=>c.category===category).map(c=>`<article class="questionnaire-item"><h4>${esc(c.label)}</h4><p>${esc(c.description||"Keine zusätzliche Beschreibung hinterlegt.")}</p>${c.type==="predicate"||!c.type?`<small>Gilt ab ${Math.round((c.threshold||0)*100)} % Wahrscheinlichkeit als passend.</small>`:""}${c.options?.length?`<div class="questionnaire-options"><strong>${c.type==="choice"?"Mögliche Antworten:":"Bewertungsstufen:"}</strong><ul>${c.options.map(o=>`<li>${esc(o.label||o.value||"")}${o.description?": "+esc(o.description):""}</li>`).join("")}</ul></div>`:""}</article>`).join("")}</section>`).join("")}<p class="questionnaire-contact">Fehlt ein Kriterium oder ist etwas unklar? <a href="mailto:gweidmann@regnumchristi.eu?subject=R%C3%BCckmeldung%20zum%20RC-Fragebogen">Gabriel Weidmann kontaktieren</a>.</p>`;
}
function display(){
 const q=(document.querySelector<HTMLInputElement>("#q")?.value||"").toLocaleLowerCase("de");
 const selected=new Set(Array.from(document.querySelectorAll<HTMLInputElement>(".criterion-options input:checked")).map(el=>el.value));
 const sort=document.querySelector<HTMLSelectElement>("#sort")?.value||"date";
 const filtered=records.filter(e=>!e.inactive&&(!q||[e.event.title,e.event.description,e.event.location].join(" ").toLocaleLowerCase("de").includes(q))&&(!selected.size||e.classification?.scores.some(s=>selected.has(s.id)&&s.matched)));
 filtered.sort((a,b)=>sort==="date"?(a.event.starts_at||"9999").localeCompare(b.event.starts_at||"9999"):(a.event.title||"").localeCompare(b.event.title||"","de"));
 document.querySelector<HTMLElement>("#count")!.textContent=`${filtered.length} von ${records.filter(e=>!e.inactive).length} Veranstaltungen`;
 document.querySelector<HTMLElement>("#results")!.innerHTML=filtered.map(card).join("")||"<p>Keine Veranstaltungen gefunden.</p>";
}
async function init(){
 root.innerHTML=`<div class="shell"><header><a class="rc-brand" href="https://www.regnumchristi.eu/" target="_blank" rel="noopener noreferrer" aria-label="Regnum Christi – Webseite"><img class="rc-logo" src="/gocath-tag-poc/rc-logo.svg" alt="Regnum Christi" /></a><h1>Veranstaltungen</h1><p>Erkannte Veranstaltungsmerkmale mit transparenten Einzelbewertungen. Modellschätzungen, keine redaktionelle Bewertung.</p></header><section class="purpose"><h2>Damit deine Veranstaltung besser gefunden wird</h2><p>Dieses Tool hilft dir dabei, deine Veranstaltung so zu beschreiben, dass Interessierte sie leichter finden – zum Beispiel über Suchmaschinen oder den Veranstaltungskalender von Regnum Christi.</p><details><summary>Mehr dazu erfahren</summary><p>Eine KI prüft, ob aus deinem Veranstaltungstext klar hervorgeht, worum es geht und für wen die Veranstaltung gedacht ist.</p><p><strong>Wichtig:</strong> Ein hoher Wert bedeutet nur, dass der Veranstaltungstext genügend eindeutige Hinweise enthält, um die Veranstaltung automatisch als katholisch relevant einzuordnen und richtig zu klassifizieren. Er sagt nichts darüber aus, wie gut oder ansprechend der Text geschrieben ist oder ob Menschen deshalb teilnehmen. Niedrige Werte können auf fehlende Informationen hinweisen. Die KI kann sich auch irren.</p></details><p class="purpose-meta">Die Liste wird derzeit manuell aktualisiert. Eine stündliche Aktualisierung ist geplant, aber noch nicht aktiviert.</p><p class="purpose-contact">Fragen oder Rückmeldungen? Gabriel Weidmann · <a href="mailto:gweidmann@regnumchristi.eu">gweidmann@regnumchristi.eu</a></p></section><nav class="catalog-nav" aria-label="Katalogansicht"><button type="button" id="show-events" aria-pressed="true">Veranstaltungen</button><button type="button" id="show-questionnaire" aria-pressed="false">Bewertungskriterien</button></nav><section id="events-view"><p class="purpose-meta"><strong>Erkannte Merkmale:</strong> Direkt angezeigt werden alle Kriterien, deren individuelle Trefferschwelle überschritten wird. Alle weiteren KI-Schätzwerte bleiben unter „Einzelbewertungen ansehen“ sichtbar. Die Werte bewerten nicht die Qualität der Veranstaltung.</p><div class="filters"><input id="q" type="search" placeholder="Veranstaltung suchen" aria-label="Suche"/><details class="criterion-filter" id="criterion-filter"><summary>Kriterien auswählen <span id="filter-count"></span></summary><div class="criterion-options" id="criterion-options"></div><button type="button" id="clear-criteria">Auswahl löschen</button></details><select id="sort" aria-label="Sortierung"><option value="date">Nach Datum</option><option value="title">Alphabetisch</option></select></div><p id="count"></p><section id="results">Daten werden geladen …</section></section><section id="questionnaire-view" hidden><h2>So werden Veranstaltungen bewertet</h2><div id="questionnaire-content"></div></section><footer>Quelle: <a href="https://www.regnumchristi.eu/demnaechst/">Regnum Christi</a></footer></div>`;
 try{
 const response=await fetch(SOURCE+"?v="+Math.floor(Date.now()/60000),{cache:"no-store"});
 if(!response.ok)throw Error("Katalog noch nicht veröffentlicht ("+response.status+")");
 const json=await response.json() as {events:Event[],questionnaire?:Questionnaire};
 if(!Array.isArray(json.events))throw Error("Ungültiges Datenformat");
 records=json.events;
 questionnaire=json.questionnaire||null;
 document.querySelector<HTMLElement>("#questionnaire-content")!.innerHTML=questionnaireView(questionnaire);
 const toggle=(showQuestions:boolean)=>{document.querySelector<HTMLElement>("#events-view")!.hidden=showQuestions;document.querySelector<HTMLElement>("#questionnaire-view")!.hidden=!showQuestions;document.querySelector<HTMLButtonElement>("#show-events")!.setAttribute("aria-pressed",String(!showQuestions));document.querySelector<HTMLButtonElement>("#show-questionnaire")!.setAttribute("aria-pressed",String(showQuestions));};
 document.querySelector<HTMLButtonElement>("#show-events")!.addEventListener("click",()=>toggle(false));
 document.querySelector<HTMLButtonElement>("#show-questionnaire")!.addEventListener("click",()=>toggle(true));
 const criteria=new Map<string,{category:string,label:string}>();
 (questionnaire?.criteria||[]).forEach(c=>criteria.set(c.id,{category:c.category,label:c.label}));
 records.forEach(e=>e.classification?.scores.forEach(score=>criteria.set(score.id,{category:score.category,label:score.label})));
 const groups=new Map<string,Array<[string,string]>>();
 criteria.forEach((c,id)=>{if(!groups.has(c.category))groups.set(c.category,[]);groups.get(c.category)!.push([id,c.label]);});
 document.querySelector<HTMLElement>("#criterion-options")!.innerHTML=Array.from(groups.entries()).sort((a,b)=>a[0].localeCompare(b[0],"de")).map(([group,items])=>`<fieldset><legend>${esc(group)}</legend>${items.sort((a,b)=>a[1].localeCompare(b[1],"de")).map(([id,label])=>`<label><input type="checkbox" value="${esc(id)}"/><span>${esc(label)}</span></label>`).join("")}</fieldset>`).join("");
 document.querySelector<HTMLElement>("#criterion-options")!.addEventListener("change",()=>{const count=document.querySelectorAll(".criterion-options input:checked").length;document.querySelector<HTMLElement>("#filter-count")!.textContent=count?`(${count})`:"";display();});
 document.querySelector<HTMLButtonElement>("#clear-criteria")!.addEventListener("click",()=>{document.querySelectorAll<HTMLInputElement>(".criterion-options input:checked").forEach(input=>input.checked=false);document.querySelector<HTMLElement>("#filter-count")!.textContent="";display();});
 document.querySelectorAll<HTMLInputElement|HTMLSelectElement>(".filters input,.filters select").forEach(el=>el.addEventListener("input",display));
 document.querySelector<HTMLElement>("#results")!.addEventListener("click",event=>{
   const expand=(event.target as HTMLElement).closest<HTMLButtonElement>(".match-expand");
   if(expand){const extras=expand.nextElementSibling as HTMLElement|null;if(extras){extras.hidden=false;expand.remove();}return;}
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
