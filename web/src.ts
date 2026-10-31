import "./style.css";
declare global { interface Window { google?: { accounts: { oauth2: { initTokenClient: (settings: Record<string, unknown>) => { requestAccessToken: (opts?: Record<string,unknown>) => void } } } } } }
const SHEET="1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w";
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const API="https://sheets.googleapis.com/v4/spreadsheets/"+SHEET;
const SESSION_KEY="gocath_sheets_oauth_session";
type SavedSession={accessToken:string; expiresAt:number};
function restoreSession():string {
  try{
    const saved=JSON.parse(sessionStorage.getItem(SESSION_KEY)||"null") as SavedSession|null;
    if(saved && typeof saved.accessToken==="string" && Number.isFinite(saved.expiresAt) && saved.expiresAt>Date.now()+30000) return saved.accessToken;
  }catch{}
  sessionStorage.removeItem(SESSION_KEY);
  return "";
}
function clearSession(){token="";sessionStorage.removeItem(SESSION_KEY);}
let reconnecting:Promise<boolean>|null=null;
function reconnect():Promise<boolean>{
 if(reconnecting)return reconnecting;
 reconnecting=new Promise<boolean>(resolve=>{
  if(!CLIENT_ID||!window.google?.accounts?.oauth2){resolve(false);return;}
  const client=window.google.accounts.oauth2.initTokenClient({
   client_id:CLIENT_ID,scope:"https://www.googleapis.com/auth/spreadsheets",prompt:"",
   callback:(r:{access_token?:string;expires_in?:number})=>{
    if(!r.access_token){resolve(false);return;}
    token=r.access_token;
    sessionStorage.setItem(SESSION_KEY,JSON.stringify({accessToken:token,expiresAt:Date.now()+Math.max(0,Number(r.expires_in)||0)*1000}));
    resolve(true);
   },
   error_callback:()=>resolve(false)
  });
  try{client.requestAccessToken({prompt:""});}catch{resolve(false);}
 }).finally(()=>{reconnecting=null;});
 return reconnecting;
}
let activeView="results";
let token=restoreSession(), config: string[][]=[], tags: string[][]=[], runs:string[][]=[], history:string[][]=[], criteria:string[][]=[], details:string[][]=[];
const app=document.querySelector<HTMLDivElement>("#app")!;
function safe(s:string):string {return s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");}
async function api(url:string,opts:RequestInit={}) {const r=await fetch(url,{...opts,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json",...(opts.headers||{})}});if(r.status===401){clearSession();render();throw new Error("Google-Sitzung abgelaufen. Bitte erneut mit Google anmelden.");}if(!r.ok)throw new Error("Google Sheets HTTP "+r.status+"; Zugriff und OAuth-Freigabe prüfen");return r.json();}
const read=async(range:string):Promise<string[][]>=>{const x=await api(API+"/values/"+encodeURIComponent(range));return x.values||[]};
async function load(){[config,tags,runs,history,criteria,details]=await Promise.all([read("Config!A1:C100"),read("Tags!A1:C300"),read("Runs!A1:L100"),read("ResultsHistory!A1:N1000"),read("Criteria!A1:I450"),read("ClassificationDetails!A1:O5000")]);render();}
function status(s:string,isError=false){const e=document.querySelector("#status");if(e){e.textContent=s;e.className=isError?"error":"";}}

function norm(value:string):string{return value.normalize("NFKC").toLocaleLowerCase("de").replace(/[.,;:!?()]/g," ").replace(/\s+/g," ").trim();}
function oneEdit(a:string,b:string):boolean{
 if(Math.abs(a.length-b.length)>1)return false;
 let i=0,j=0,errors=0;
 while(i<a.length&&j<b.length){
  if(a[i]===b[j]){i++;j++;continue;}
  if(++errors>1)return false;
  if(a.length>b.length)i++;else if(b.length>a.length)j++;else{i++;j++;}
 }
 return errors+(a.length-i)+(b.length-j)<=1;
}
function containsFuzzy(term:string,word:string):boolean{
 if(term.length<3)return false;
 if(word.includes(term))return true;
 // Short search terms cause too many false positives with one-edit matching.
 if(term.length<5)return false;
 for(let length=Math.max(1,term.length-1);length<=Math.min(word.length,term.length+1);length++){
  for(let start=0;start+length<=word.length;start++){
   if(oneEdit(term,word.slice(start,start+length)))return true;
  }
 }
 return false;
}
function matchesHistory(row:string[],query:string,configuredTags:string[][]):boolean{
 const q=norm(query).split(" ").filter(Boolean);if(!q.length)return true;if(q.some(part=>part.length<3))return false;
 const chosen=(row[3]||"").split(",").map(x=>x.trim());
 const synonyms=configuredTags.filter(t=>chosen.some(c=>norm(c)===norm(t[0]))).flatMap(t=>(t[2]||"").split(",").map(x=>x.trim()));
 const words=norm([row[2],row[3],row[4],row[5],...synonyms].join(" ")).split(" ").filter(Boolean);
 return q.every(part=>words.some(word=>containsFuzzy(part,word)));
}
function optionsLines(value:string):string {try{const a=JSON.parse(value) as {value?:string,label?:string,description?:string}[];return Array.isArray(a)?a.map(x=>String(x.value??x.label??"")+" | "+String(x.description??"")).join("\n"):"";}catch{return value;}}
function encodeOptions(raw:string,type:string):string {
 const options=raw.split(/\r?\n/).map(x=>x.trim()).filter(Boolean).map(line=>{
  const split=line.indexOf("|"),name=(split<0?line:line.slice(0,split)).trim(),description=(split<0?"":line.slice(split+1)).trim();
  if(!name)throw new Error("Jede Option braucht eine Bezeichnung");
  return type==="score"?{label:name,description}:{value:name,description};
 });
 const max=type==="score"?10:255;
 if(options.length<2||options.length>max)throw new Error("Bitte 2 bis "+max+" Optionen eingeben");
 if(new Set(options.map(o=>"label" in o?o.label:o.value)).size!==options.length)throw new Error("Doppelte Antwortoption");
 return JSON.stringify(options);
}
function answerDistribution(raw:string,type:string):string {
 if(type!=="choice"&&type!=="score")return "";
 try{
   const answer=JSON.parse(raw) as {choice?:string,score?:number,confidence?:number,probabilities?:{value:string|number,label?:string,probability:number}[]};
   if(!Array.isArray(answer.probabilities))return "";
   const items=answer.probabilities;
   return `<div class="answer-distribution"><div class="answer-heading">${type==="choice"?"Auswahl: "+safe(answer.choice||"–"):"Score: "+safe(String(answer.score??"–"))}</div>${items.map(o=>`<div class="answer-item"><div class="answer-item-label"><span>${safe(String(o.label??o.value))}</span><strong>${Math.round(o.probability*100)} %</strong></div><div class="answer-track"><div class="answer-fill" style="width:${Math.max(0,Math.min(100,o.probability*100))}%"></div></div></div>`).join("")}<small class="muted">Modellverteilung; keine kalibrierten Wahrscheinlichkeiten. Konfidenz: ${Math.round((answer.confidence||0)*100)} %</small></div>`;
 }catch{return "";}
}
const germanSort=new Intl.Collator("de",{sensitivity:"base",numeric:true});
function questionGroups(rows:string[][]){
 const groups=new Map<string,{row:number,data:string[]}[]>();
 rows.slice(1).forEach((data,i)=>{if(!data[0])return;const name=data[1]?.trim()||"Sonstiges";if(!groups.has(name))groups.set(name,[]);groups.get(name)!.push({row:i+2,data});});
 return [...groups.entries()].sort((a,b)=>germanSort.compare(a[0],b[0])).map(([name,items])=>({name,items:items.sort((a,b)=>germanSort.compare(a.data[2]||a.data[0],b.data[2]||b.data[0]))}));
}
function sheetNumber(input:string):number {const n=Number(String(input||"0").replace(",","."));return Number.isFinite(n)?n:0;}
function percent(input:string):string{return Math.round(sheetNumber(input)*100)+" %";}
function criteriaTypeLabel(type:string):string{return type==="choice"?"Einzelauswahl":type==="score"?"Bewertungsskala":"Wahrscheinlichkeit";}
function relevanceInfo(value:string):{label:string,kind:string}{
 if(value==="likely_relevant")return {label:"Wahrscheinlich relevant",kind:"relevant"};
 if(value==="review")return {label:"Prüfen",kind:"review"};
 if(value==="likely_not_relevant")return {label:"Eher nicht relevant",kind:"unlikely"};
 return {label:"Nicht bewertet",kind:"unknown"};
}
function matchingDetails(run:string,url:string):string[][] {return details.slice(1).filter(d=>d[0]===run&&d[1]===url);}
function renderCriterionDetail(d:string[]):string{
 const type=d[13]||"predicate",value=sheetNumber(d[8]);
 return `<div class="criterion-result"><div class="criterion-result-head"><strong>${safe(d[7]||d[5]||"")}</strong><span>${percent(String(value))}</span></div><div class="answer-track"><div class="answer-fill" style="width:${Math.max(0,Math.min(100,value*100))}%"></div></div>${answerDistribution(d[14]||"",type)}${d[12]?`<p class="hint">${safe(d[12])}</p>`:""}</div>`;
}
function renderEventCard(r:string[]):string{
 const ds=matchingDetails(r[0],r[1]),info=relevanceInfo(ds[0]?.[11]||""),score=ds[0]?.[10];
 const top=ds.filter(d=>d[9]==="true").sort((a,b)=>sheetNumber(b[8])-sheetNumber(a[8])).slice(0,4);
 const groups=[...new Set(ds.map(d=>d[6]||"Sonstiges"))].sort(germanSort.compare);
 const body=groups.map(group=>{
   const items=ds.filter(d=>(d[6]||"Sonstiges")===group).sort((a,b)=>sheetNumber(b[8])-sheetNumber(a[8]));
   return `<details class="detail-group"><summary>${safe(group)} <span>${items.filter(d=>d[9]==="true").length} Treffer · ${items.length} Fragen</span></summary><div class="detail-questions">${items.map(renderCriterionDetail).join("")}</div></details>`;
 }).join("");
 return `<article class="event-card"><div class="event-card-main"><div class="event-card-title"><h3>${safe(r[2]||"Ohne Titel")}</h3><span class="relevance-tag ${info.kind}">${info.label}${score!==undefined&&score!==""?" · "+percent(score):""}</span></div><div class="event-chips">${top.map(d=>`<span class="result-chip">${safe(d[7]||"")}: ${percent(d[8])}</span>`).join("")}</div><div class="event-card-meta"><span>${ds.length} Fragen</span><span>${ds.filter(d=>d[9]==="true").length} Treffer</span>${r[12]?`<span>${safe(r[12])} Tokens</span>`:""}</div></div><details class="event-expand"><summary>Alle Bewertungen ansehen</summary><div class="event-expanded"><p><a href="${safe(r[1]||"")}" target="_blank" rel="noopener noreferrer">Veranstaltungsseite öffnen ↗</a></p>${r[3]||r[4]?`<p><strong>Tags:</strong> ${safe([r[3],r[4]].filter(Boolean).join(", "))}</p>`:""}${r[5]?`<p><strong>Begründung:</strong> ${safe(r[5])}</p>`:""}${ds.length?body:'<p class="hint">Für diesen Lauf liegen keine Einzelbewertungen vor.</p>'}</div></details></article>`;
}
function render(){
 const c=config.slice(1).filter(x=>x[0]); const t=tags.slice(1).filter(x=>x[0]);
 app.innerHTML=`<header><div class="brand"><span class="mark">✝</span><div><b>GoCath Tagging</b><small>Konfiguration & Ergebnisse · POC</small></div></div><span class="muted">${token?"Google Sheets verbunden":"Nicht verbunden"}</span></header>
 <main><section class="hero"><h1>Event-Klassifizierung</h1><p>Verwalte die Einstellungen für den manuell gestarteten GitHub-Actions-Runner. Alle Werte werden im Google Sheet gespeichert.</p>
 <div class="actions"><button id="login">${token?"Erneut autorisieren":"Mit Google anmelden"}</button><a href="https://github.com/weidmanngabriel/gocath-tag-poc/actions" target="_blank" rel="noopener">GitHub Actions öffnen ↗</a><a href="https://docs.google.com/spreadsheets/d/${SHEET}/edit" target="_blank" rel="noopener">Google Sheet öffnen ↗</a></div><p id="status" aria-live="polite"></p></section>
 ${token?`<nav class="section-tabs" aria-label="Dashboard-Bereiche">${[["results","Ergebnisse"],["criteria","Kriterien"],["config","Konfiguration"],["tags","Alte Tags"],["metrics","Metriken"],["runs","Läufe"]].map(([id,label])=>`<button type="button" data-switch-view="${id}" aria-pressed="${activeView===id}">${label}</button>`).join("")}</nav><div class="columns"><section class="panel" data-view="config"><h2>Konfiguration</h2><p class="hint">Änderungen werden beim Verlassen eines Feldes automatisch gespeichert.</p><div id="settings">${c.map((r,i)=>`<label data-config-key="${safe(r[0])}"><span>${safe(r[0]==="gemini_prompt"?"Klassifizierungs-Prompt (alle Anbieter)":r[0]==="gemini_temperature"?"Temperatur (Gemini / Groq)":r[0]==="openai_reasoning_effort"?"OpenAI Reasoning-Stufe":r[0]==="cost_input_per_million_usd"?"Input-Preis in USD / 1 Mio. Tokens":r[0]==="cost_output_per_million_usd"?"Output-Preis in USD / 1 Mio. Tokens":r[2]||r[0])}<small>${safe(r[0])}</small></span>${r[0]==="event_source"?`<select data-setting="${i}"><option value="gocath" ${r[1]==="gocath"?"selected":""}>GoCath – gocath.org/de/finde</option><option value="regnum_christi" ${r[1]==="regnum_christi"?"selected":""}>Regnum Christi – demnächst</option></select>`:r[0]==="classifier_provider"?`<select data-setting="${i}"><option value="groq" ${r[1]==="groq"?"selected":""}>Groq · GPT-OSS 20B</option><option value="gemini" ${r[1]==="gemini"?"selected":""}>Google Gemini</option><option value="openai" ${r[1]==="openai"?"selected":""}>OpenAI · GPT-6 Luna</option></select>`:r[0]==="openai_reasoning_effort"?`<select data-setting="${i}">${["none","low","medium","high"].map(v=>`<option value="${v}" ${r[1]===v?"selected":""}>${v}</option>`).join("")}</select>`:r[0]==="changed_only"||r[0]==="additional_tags_enabled"?`<select data-setting="${i}"><option value="true" ${r[1]==="true"?"selected":""}>Ja</option><option value="false" ${r[1]==="false"?"selected":""}>Nein</option></select>`:r[0]==="max_additional_tags"?`<select data-setting="${i}">${[0,1,2,3,4,5,6,7,8].map(v=>`<option value="${v}" ${r[1]===String(v)?"selected":""}>${v}</option>`).join("")}</select>`:r[0]==="gemini_temperature"?`<select data-setting="${i}">${["0","0.1","0.2","0.3","0.5","0.7","1"].map(v=>`<option value="${v}" ${r[1]===v?"selected":""}>${v}</option>`).join("")}</select>`:r[0]==="gemini_prompt"?`<textarea data-setting="${i}" rows="9">${safe(r[1]||"")}</textarea>`:`<input data-setting="${i}" value="${safe(r[1]||"")}" />`}</label>`).join("")}</div><button id="saveConfig" hidden>Konfiguration speichern</button></section>
 <section class="panel" data-view="tags"><h2>Standard-Tags</h2><p class="hint">Nur aktivierte Tags werden der ausgewählten KI zur Auswahl angeboten.</p><div class="tag-grid">${t.map((r,i)=>`<div class="tag-entry" data-tag-entry="${i}"><div class="tag-entry-header"><label class="tag"><input type="checkbox" data-tag="${i}" ${r[1]?.toLowerCase()==="true"?"checked":""}/><span>${safe(r[0])}</span></label><button type="button" class="remove-tag" data-remove-tag="${i}" aria-label="Standard-Tag ${safe(r[0])} löschen" title="Standard-Tag löschen">Löschen</button></div><input class="synonyms" data-synonyms="${i}" placeholder="Synonyme, mit Kommas getrennt" value="${safe(r[2]||"")}" aria-label="Synonyme für ${safe(r[0])}"/></div>`).join("")}</div><label class="add"><span>Neuen Tag ergänzen</span><input id="newTag" placeholder="z. B. Kirchenmusik"/></label><button id="saveTags">Neuen Tag hinzufügen</button></section></div>
<section class="panel questionnaire" data-view="criteria"><h2>Decisions-Fragebogen</h2><p class="hint">Titel, Beschreibung und Entscheidungsregeln direkt pflegen. Änderungen werden automatisch gespeichert. Bei Einzelauswahl werden die Wahrscheinlichkeiten <strong>aller</strong> Antworten gespeichert.</p>
<div class="question-tabs" role="tablist" aria-label="Fragebogenbereiche">${questionGroups(criteria).map((group,i)=>`<button type="button" role="tab" data-question-tab="${i}" aria-selected="${i===0}">${safe(group.name)} <span>${group.items.length}</span></button>`).join("")}</div>
<div class="question-groups">${questionGroups(criteria).map((group,i)=>`<section class="question-group" data-question-group="${i}" role="tabpanel" ${i!==0?"hidden":""}><div class="question-group-heading"><h3>${safe(group.name)}</h3><p>${group.items.length} Fragen · alphabetisch sortiert</p></div><div class="question-list">${group.items.map(({row,data:r})=>`<details class="question-card"><summary><span class="question-category">${safe(r[1]||"Sonstiges")}</span><strong>${safe(r[2]||r[0])}</strong><span class="question-type">${safe(criteriaTypeLabel(r[7]||"predicate"))}</span><span class="question-state">${r[4]==="true"?"Aktiv":"Inaktiv"}</span></summary>
<div class="question-fields">
<label>Fragetitel<input data-criterion-row="${row}" data-criterion-col="C" value="${safe(r[2]||"")}"/></label>
<label>Bereich<input data-criterion-row="${row}" data-criterion-col="B" value="${safe(r[1]||"")}"/></label>
<label>Beschreibung / Entscheidungsregel<textarea rows="3" data-criterion-row="${row}" data-criterion-col="D">${safe(r[3]||"")}</textarea></label>
<label>Fragetyp<select data-criterion-row="${row}" data-criterion-col="H">${["predicate","choice","score"].map(type=>`<option value="${type}" ${(r[7]||"predicate")===type?"selected":""}>${type==="predicate"?"Wahrscheinlichkeit (0–1)":type==="choice"?"Einzelauswahl mit Verteilung":"Bewertungsskala mit Verteilung"}</option>`).join("")}</select></label>
<label>Aktiv<input type="checkbox" data-criterion-row="${row}" data-criterion-col="E" ${r[4]==="true"?"checked":""}/></label>
<div class="option-editor" ${!["choice","score"].includes(r[7])?"hidden":""}><label>Antwortmöglichkeiten und Regeln<textarea rows="5" data-criterion-row="${row}" data-criterion-col="I" placeholder="Antwort | Wähle diese Antwort, wenn …">${safe(optionsLines(r[8]||""))}</textarea></label><small>Eine Option pro Zeile. Einzelauswahl: 2–255 Antworten; Skala: 2–10 geordnete Stufen. Zuerst die Optionen eintragen, dann den Fragetyp umstellen.</small></div>
<label>Relevanzgewicht (nur Wahrscheinlichkeit)<input type="number" min="0" max="3" step="0.1" data-criterion-row="${row}" data-criterion-col="F" ${["choice","score"].includes(r[7])?"disabled":""} value="${safe(r[5]||"0")}"/></label>
<label>Trefferschwelle<input type="number" min="0" max="1" step="0.05" data-criterion-row="${row}" data-criterion-col="G" value="${safe(r[6]||"0.65")}"/></label><small class="muted">ID: ${safe(r[0])}</small></div></details>`).join("")}</div></section>`).join("")}</div>
<details class="question-card"><summary><strong>+ Neue Frage hinzufügen</strong></summary><div class="question-fields">
<label>Titel<input id="questionTitle" placeholder="z. B. Veranstaltungsformat"/></label>
<label>Bereich<input id="questionCategory" value="Format"/></label>
<label>Beschreibung<textarea id="questionDescription" rows="3"></textarea></label>
<label>Fragetyp<select id="questionType"><option value="predicate">Wahrscheinlichkeit</option><option value="choice">Einzelauswahl mit Verteilung</option><option value="score">Bewertungsskala mit Verteilung</option></select></label>
<label id="newQuestionOptionsWrap" hidden>Antworten und Regeln<textarea id="questionOptions" rows="5" placeholder="Option | Wähle diese Antwort, wenn …"></textarea></label>
<label>Relevanzgewicht (nur Wahrscheinlichkeit)<input id="questionWeight" type="number" min="0" max="3" step="0.1" value="0"/></label>
<label>Trefferschwelle<input id="questionThreshold" type="number" min="0" max="1" step="0.05" value="0.65"/></label><button id="addQuestion" type="button">Frage hinzufügen</button></div></details></section>
 <section class="panel" data-view="metrics"><h2>KI-Metriken</h2><p class="hint">Vom jeweiligen KI-Anbieter gemeldete Tokens je Lauf. Kosten sind Schätzungen auf Basis der hinterlegten Preise, keine Anbieterrechnung.</p><div class="table-scroll"><table><thead><tr><th>Run</th><th>Input</th><th>Output</th><th>Thinking</th><th>Gesamt</th><th>Kosten (USD, geschätzt)</th></tr></thead><tbody>${runs.slice(1).filter(x=>x[0]).reverse().slice(0,20).map(r=>`<tr><td>${safe(r[0]||"")}</td><td>${safe(r[6]||"–")}</td><td>${safe(r[7]||"–")}</td><td>${safe(r[8]||"–")}</td><td>${safe(r[9]||"–")}</td><td>${safe(r[10]||"nicht konfiguriert")}</td></tr>`).join("")}</tbody></table></div></section><section class="panel" data-view="results"><h2>Klassifizierungsergebnisse</h2><p class="hint">Alle Events bleiben sichtbar – auch solche mit niedriger katholischer Relevanz. Ergebnisse und Einzelbewertungen je Run.</p><label><span>Run-ID auswählen</span><select id="runFilter">${[...new Set(history.slice(1).map(r=>r[0]).filter(Boolean))].reverse().map(id=>`<option value="${safe(id)}">Run ${safe(id)}</option>`).join("")}</select></label><label class="search-label"><span>Ergebnisse durchsuchen (ab 3 Zeichen, Contains + 1 Zeichen Abweichung)</span><input id="historySearch" type="search" placeholder="z. B. Gottesdienst oder Heilige Messe" autocomplete="off" /></label><p class="hint" id="matchCount" aria-live="polite"></p><div id="historyView"></div></section>
 <section class="panel" data-view="runs"><h2>Letzte Läufe</h2><div class="table-scroll"><table><thead><tr><th>Run-ID</th><th>Beginn</th><th>Ende</th><th>Status</th><th>Klassifiziert</th></tr></thead><tbody>${runs.slice(1).filter(x=>x[0]).reverse().slice(0,15).map(r=>`<tr>${r.slice(0,5).map(v=>`<td>${safe(v||"")}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>`:`<section class="panel"><h2>Google-Anmeldung erforderlich</h2><p>Der Google-Account benötigt Bearbeiterzugriff auf das Sheet. Es werden keine API-Schlüssel im Browser gespeichert.</p>${!CLIENT_ID?"<p class='error'>VITE_GOOGLE_CLIENT_ID ist noch nicht für den GitHub-Pages-Build konfiguriert.</p>":""}</section>`}
 <dialog id="reasonDialog" class="reason-dialog" aria-labelledby="reasonDialogTitle"><div class="reason-dialog-head"><h2 id="reasonDialogTitle">Begründung</h2><form method="dialog"><button type="submit">Schließen</button></form></div><p id="reasonDialogText"></p></dialog><footer>GoCath Proof of Concept · Keine automatische Ausführung</footer></main>`;
 document.querySelector<HTMLButtonElement>("#login")!.onclick=login;
 if(token){
 const setView=(view:string)=>{activeView=view;document.querySelectorAll<HTMLElement>("[data-view]").forEach(el=>el.classList.toggle("active",el.dataset.view===view));document.querySelectorAll<HTMLButtonElement>("[data-switch-view]").forEach(el=>el.setAttribute("aria-pressed",String(el.dataset.switchView===view)));};
 document.querySelectorAll<HTMLButtonElement>("[data-switch-view]").forEach(button=>button.onclick=()=>setView(button.dataset.switchView||"config"));
 setView(activeView);
 document.querySelectorAll<HTMLButtonElement>("[data-remove-tag]").forEach(button=>button.onclick=()=>{
   const entry=button.closest<HTMLElement>(".tag-entry");
   if(!entry)return;
   if(document.querySelectorAll(".tag-entry").length<=1){status("Mindestens ein Standard-Tag muss erhalten bleiben.",true);return;}
   const name=entry.querySelector(".tag span")?.textContent||"";
   if(!confirm('Standard-Tag „'+name+'“ löschen? Die Änderung wird sofort gespeichert.'))return;
   entry.remove();
   document.querySelector<HTMLButtonElement>("#saveTags")?.click();
 });
 const questionTabs=[...document.querySelectorAll<HTMLButtonElement>("[data-question-tab]")];
 const questionSections=[...document.querySelectorAll<HTMLElement>("[data-question-group]")];
 questionTabs.forEach(button=>button.onclick=()=>{
  const selected=button.dataset.questionTab;
  questionTabs.forEach(b=>b.setAttribute("aria-selected",String(b===button)));
  questionSections.forEach(section=>{section.hidden=section.dataset.questionGroup!==selected;});
 });
 const filter=document.querySelector<HTMLSelectElement>("#runFilter"); const view=document.querySelector<HTMLDivElement>("#historyView"); 
 const search=document.querySelector<HTMLInputElement>("#historySearch");
 const showHistory=()=>{if(!filter||!view)return; const source=history.slice(1).filter(r=>r[0]===filter.value);const term=search?.value.trim()||"";const rows=source.filter(r=>!term||norm(term).split(" ").every(part=>part.length>=3)&&matchesHistory(r,term,t));const count=document.querySelector("#matchCount");if(count)count.textContent=term&&norm(term).split(" ").some(part=>part.length<3)?"Mindestens 3 Zeichen je Suchwort eingeben":`${rows.length} von ${source.length} Veranstaltungen gefunden`;view.innerHTML=`<div class="table-scroll"><table><thead><tr><th>Veranstaltung</th><th>Relevanz</th><th>Format / Themen / Zielgruppen</th><th>Alte Tags</th><th>Begründung</th><th>Tokens</th><th>Kosten (USD)</th></tr></thead><tbody>${rows.map(r=>`<tr><td><a href="${safe(r[1])}" target="_blank" rel="noopener">${safe(r[2]||"")}</a></td><td>${(()=>{const ds=details.slice(1).filter(d=>d[0]===r[0]&&d[1]===r[1]);const status=ds[0]?.[11]||"nicht bewertet";const score=ds[0]?.[10];return safe(status)+" "+(score?Math.round(Number(score)*100)+" %":"");})()}</td><td>${(()=>{const ds=details.slice(1).filter(d=>d[0]===r[0]&&d[1]===r[1]).sort((a,b)=>Number(b[8]||0)-Number(a[8]||0));return ds.length?`<details><summary>${ds.filter(d=>d[9]==="true").length} Treffer · ${ds.length} Bewertungen</summary>${ds.map(d=>`<div class="answer-result"><span class="result-chip" title="${safe(d[12]||"")}">${safe(d[7]||"")} ${Math.round(Number(String(d[8]||0).replace(",","."))*100)} %</span>${answerDistribution(d[14]||"",d[13]||"predicate")}</div>`).join(" ")}</details>`:"–";})()}</td><td>${safe(r[3]||"")} ${safe(r[4]||"")}</td><td><button type="button" class="reason-button" data-reason-index="${rows.indexOf(r)}">Anzeigen</button></td><td>${safe(r[12]||"–")}</td><td>${safe(r[13]||"–")}</td></tr>`).join("")}</tbody></table></div>`;view.querySelectorAll<HTMLButtonElement>(".reason-button").forEach(button=>{button.onclick=()=>{const index=Number(button.dataset.reasonIndex);const dialog=document.querySelector<HTMLDialogElement>("#reasonDialog");const text=document.querySelector<HTMLElement>("#reasonDialogText");if(dialog&&text){text.textContent=rows[index]?.[5]||"Keine Begründung vorhanden.";dialog.showModal();}};});};if(filter){filter.onchange=showHistory;if(search)search.oninput=showHistory;showHistory();}
 const cols:Record<string,number>={B:1,C:2,D:3,E:4,F:5,G:6,H:7,I:8};
 const pending=new Set<string>();
 const writeQuestion=async(row:number,col:string,value:string)=>{
   const i=row-1,j=cols[col],address=col+row;
   if(criteria[i]?.[j]===value)return;
   if(pending.has(address))return;
   pending.add(address);status("Speichert …");
   try{await api(API+"/values/"+encodeURIComponent("Criteria!"+address)+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({values:[[value]]})});
     if(criteria[i])criteria[i][j]=value;status("Gespeichert");
   }catch(e){status("Nicht gespeichert: "+String(e),true);throw e;}
   finally{pending.delete(address);}
 };
 document.querySelectorAll<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>("[data-criterion-row]").forEach(input=>{
   const save=async()=>{
     const row=Number(input.dataset.criterionRow),col=input.dataset.criterionCol||"D";
     const select=document.querySelector<HTMLSelectElement>(`[data-criterion-row="${row}"][data-criterion-col="H"]`);
     const type=select?.value||"predicate";
     let value=input.type==="checkbox"?(input as HTMLInputElement).checked?"true":"false":input.value.trim();
     try{
       if(col==="I"){if(type==="predicate")return;value=encodeOptions(value,type);}
       if(col==="H"){
         if(value!=="predicate"){
           const editor=document.querySelector<HTMLTextAreaElement>(`[data-criterion-row="${row}"][data-criterion-col="I"]`);
           if(!editor)throw new Error("Antwortmöglichkeiten fehlen");
           const options=encodeOptions(editor.value,value);
           await writeQuestion(row,"I",options);
           await writeQuestion(row,"F","0");
         }
       }
       if(col==="F"&&type!=="predicate"&&Number(value)!==0)throw new Error("Für Auswahlfragen ist das Relevanzgewicht 0");
       if((col==="F"||col==="G")&&(!Number.isFinite(Number(value))||Number(value)<0||(col==="G"&&Number(value)>1)||(col==="F"&&Number(value)>3)))throw new Error("Ungültiger Zahlenwert");
       await writeQuestion(row,col,value);
       if(col==="H"){const parent=input.closest(".question-fields");const opt=parent?.querySelector<HTMLElement>(".option-editor");if(opt)opt.hidden=value==="predicate";
         const weight=parent?.querySelector<HTMLInputElement>('[data-criterion-col="F"]');if(weight){weight.disabled=value!=="predicate";if(value!=="predicate")weight.value="0";}}
     }catch(e){status(String(e),true);}
   };
   input.addEventListener(input.type==="checkbox"||input.tagName==="SELECT"?"change":"blur",save);
 });
 const newType=document.querySelector<HTMLSelectElement>("#questionType");
 newType?.addEventListener("change",()=>{
  const wrap=document.querySelector<HTMLElement>("#newQuestionOptionsWrap");
  if(wrap)wrap.hidden=newType.value==="predicate";
  const weight=document.querySelector<HTMLInputElement>("#questionWeight");
  if(weight){weight.disabled=newType.value!=="predicate";if(weight.disabled)weight.value="0";}
 });
 document.querySelector<HTMLButtonElement>("#addQuestion")?.addEventListener("click",async()=>{
   const title=document.querySelector<HTMLInputElement>("#questionTitle")?.value.trim()||"";
   const category=document.querySelector<HTMLInputElement>("#questionCategory")?.value.trim()||"Sonstiges";
   const description=document.querySelector<HTMLTextAreaElement>("#questionDescription")?.value.trim()||"";
   const type=newType?.value||"predicate";
   const weight=document.querySelector<HTMLInputElement>("#questionWeight")?.value||"0";
   const threshold=document.querySelector<HTMLInputElement>("#questionThreshold")?.value||"0.65";
   if(!title||!description){status("Titel und Beschreibung sind erforderlich",true);return;}
   if(criteria.slice(1).filter(r=>r[0]).length>=400){status("Maximal 400 Fragen möglich",true);return;}
   if(!Number.isFinite(Number(weight))||Number(weight)<0||Number(weight)>3||!Number.isFinite(Number(threshold))||Number(threshold)<0||Number(threshold)>1){status("Ungültiges Gewicht oder Schwelle",true);return;}
   try{
     const options=type==="predicate"?"":encodeOptions(document.querySelector<HTMLTextAreaElement>("#questionOptions")?.value||"",type);
     const ids=new Set(criteria.slice(1).map(r=>r[0]));
     let id="q_"+title.toLocaleLowerCase("de").normalize("NFKD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"").slice(0,35);
     if(id==="q_")id="q_new";
     const base=id;let suffix=2;while(ids.has(id))id=base+"_"+suffix++;
     const row=Math.max(2,criteria.length+1);
     const values=[[id,category,title,description,"true",type==="predicate"?weight:"0",threshold,type,options]];
     status("Speichert neue Frage …");
     await api(API+"/values/"+encodeURIComponent("Criteria!A"+row+":I"+row)+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({values})});
     await load();status("Frage hinzugefügt");
   }catch(e){status("Nicht gespeichert: "+String(e),true);}
 });
 // Save ordinary settings and legacy tag fields on blur/change.
 document.querySelectorAll<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>("[data-setting]").forEach(input=>{
   const save=async()=>{
     const index=Number(input.dataset.setting),row=index+2;
     const value=input.value;
     if(c[index]?.[1]===value)return;
     try{
       status("Speichert …");
       await api(API+"/values/"+encodeURIComponent("Config!B"+row)+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({values:[[value]]})});
       c[index][1]=value;
       status("Gespeichert");
     }catch(e){status("Nicht gespeichert: "+String(e),true);}
   };
   input.addEventListener(input.tagName==="SELECT"?"change":"blur",save);
 });
 document.querySelectorAll<HTMLInputElement>("[data-tag],[data-synonyms]").forEach(input=>{
   const save=async()=>{
     const isTag=input.hasAttribute("data-tag"),index=Number(isTag?input.dataset.tag:input.dataset.synonyms);
     const row=index+2,col=isTag?"B":"C",value=isTag?(input.checked?"true":"false"):input.value.trim();
     if(t[index]?.[isTag?1:2]===value)return;
     try{
       status("Speichert …");
       await api(API+"/values/"+encodeURIComponent("Tags!"+col+row)+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({values:[[value]]})});
       t[index][isTag?1:2]=value;
       status("Gespeichert");
     }catch(e){status("Nicht gespeichert: "+String(e),true);}
   };
   input.addEventListener(input.type==="checkbox"?"change":"blur",save);
 });
 document.querySelector<HTMLInputElement>("#newTag")?.addEventListener("keydown",e=>{
   if(e.key==="Enter"){e.preventDefault();document.querySelector<HTMLButtonElement>("#saveTags")?.click();}
 });
 const providerSelect=document.querySelector<HTMLSelectElement>('[data-config-key="classifier_provider"] select');
 const updateProviderFields=()=>{
   const provider=providerSelect?.value||"groq";
   const visibility:Record<string,string[]>={
     gemini_model:["gemini"],
     gemini_temperature:["gemini","groq"],
     openai_reasoning_effort:["openai"],
     cost_input_per_million_usd:["gemini","openai"],
     cost_output_per_million_usd:["gemini","openai"],
     cost_cached_input_per_million_usd:["gemini","openai"]
   };
   Object.entries(visibility).forEach(([key,providers])=>{
     const label=document.querySelector<HTMLElement>('[data-config-key="'+key+'"]');
     if(label)label.hidden=!providers.includes(provider);
   });
 };
 if(providerSelect){providerSelect.onchange=updateProviderFields;updateProviderFields();}
 document.querySelector<HTMLButtonElement>("#saveConfig")!.onclick=async()=>{try{const rows=c.map((r,i)=>[r[0],(document.querySelector<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>(`[data-setting="${i}"]`)!.value),r[2]||""]);await api(API+"/values/"+encodeURIComponent("Config!A2:C"+(rows.length+1))+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({range:"Config!A2:C"+(rows.length+1),majorDimension:"ROWS",values:rows})});status("Konfiguration gespeichert");await load();}catch(e){status(String(e),true)}};
 document.querySelector<HTMLButtonElement>("#saveTags")!.onclick=async()=>{try{const rows=Array.from(document.querySelectorAll<HTMLElement>(".tag-entry")).map(entry=>{const i=Number(entry.dataset.tagEntry);return [t[i][0],entry.querySelector<HTMLInputElement>(`[data-tag="${i}"]`)!.checked?"true":"false",entry.querySelector<HTMLInputElement>(`[data-synonyms="${i}"]`)!.value.trim()];});const name=document.querySelector<HTMLInputElement>("#newTag")!.value.trim();if(name&&!rows.some(x=>x[0].toLowerCase()===name.toLowerCase()))rows.push([name,"true",""]);if(!rows.length)throw new Error("Mindestens ein Standard-Tag ist erforderlich.");const oldCount=tags.slice(1).filter(x=>x[0]).length;const end=Math.max(rows.length,oldCount)+1;const padded=[...rows,...Array.from({length:Math.max(0,oldCount-rows.length)},()=>["","",""])];await api(API+"/values/"+encodeURIComponent("Tags!A2:C"+end)+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({range:"Tags!A2:C"+end,majorDimension:"ROWS",values:padded})});status("Tags gespeichert");await load();}catch(e){status(String(e),true)}};
 }
}
function login(){if(!CLIENT_ID){status("OAuth Client-ID fehlt. GitHub Variable VITE_GOOGLE_CLIENT_ID konfigurieren.",true);return;}
 if(!window.google?.accounts?.oauth2){status("Google Identity Services lädt noch; Seite neu laden.",true);return;}
 const client=window.google.accounts.oauth2.initTokenClient({client_id:CLIENT_ID,scope:"https://www.googleapis.com/auth/spreadsheets",prompt:"",callback:async(r:{access_token?:string,expires_in?:number,error?:string})=>{if(!r.access_token){status("Anmeldung fehlgeschlagen: "+(r.error||"unbekannt"),true);return;}token=r.access_token;sessionStorage.setItem(SESSION_KEY,JSON.stringify({accessToken:token,expiresAt:Date.now()+Math.max(0,Number(r.expires_in)||0)*1000}));try{await load();status("Google Sheets verbunden")}catch(e){status(String(e),true)}}});
 client.requestAccessToken();
}
render();
async function start(){
 if(token){await load();return;}
 // GIS is loaded asynchronously from Google's script.
 for(let attempt=0;attempt<30&&!window.google?.accounts?.oauth2;attempt++)
  await new Promise(resolve=>setTimeout(resolve,100));
 if(await reconnect()){render();await load();}
}
start().catch(e=>status(String(e),true));
