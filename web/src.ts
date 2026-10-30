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
let activeView="config";
let token=restoreSession(), config: string[][]=[], tags: string[][]=[], runs:string[][]=[], history:string[][]=[];
const app=document.querySelector<HTMLDivElement>("#app")!;
function safe(s:string):string {return s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");}
async function api(url:string,opts:RequestInit={}) {const r=await fetch(url,{...opts,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json",...(opts.headers||{})}});if(r.status===401){clearSession();render();throw new Error("Google-Sitzung abgelaufen. Bitte erneut mit Google anmelden.");}if(!r.ok)throw new Error("Google Sheets HTTP "+r.status+"; Zugriff und OAuth-Freigabe prüfen");return r.json();}
const read=async(range:string):Promise<string[][]>=>{const x=await api(API+"/values/"+encodeURIComponent(range));return x.values||[]};
async function load(){[config,tags,runs,history]=await Promise.all([read("Config!A1:C100"),read("Tags!A1:C300"),read("Runs!A1:K100"),read("ResultsHistory!A1:N500")]);render();}
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
function render(){
 const c=config.slice(1).filter(x=>x[0]); const t=tags.slice(1).filter(x=>x[0]);
 app.innerHTML=`<header><div class="brand"><span class="mark">✝</span><div><b>GoCath Tagging</b><small>Konfiguration & Ergebnisse · POC</small></div></div><span class="muted">${token?"Google Sheets verbunden":"Nicht verbunden"}</span></header>
 <main><section class="hero"><h1>Event-Klassifizierung</h1><p>Verwalte die Einstellungen für den manuell gestarteten GitHub-Actions-Runner. Alle Werte werden im Google Sheet gespeichert.</p>
 <div class="actions"><button id="login">${token?"Erneut autorisieren":"Mit Google anmelden"}</button><a href="https://github.com/weidmanngabriel/gocath-tag-poc/actions" target="_blank" rel="noopener">GitHub Actions öffnen ↗</a><a href="https://docs.google.com/spreadsheets/d/${SHEET}/edit" target="_blank" rel="noopener">Google Sheet öffnen ↗</a></div><p id="status" aria-live="polite"></p></section>
 ${token?`<nav class="section-tabs" aria-label="Dashboard-Bereiche">${[["config","Konfiguration"],["tags","Standard-Tags"],["metrics","Metriken"],["results","Ergebnisse"],["runs","Läufe"]].map(([id,label])=>`<button type="button" data-switch-view="${id}" aria-pressed="${activeView===id}">${label}</button>`).join("")}</nav><div class="columns"><section class="panel" data-view="config"><h2>Konfiguration</h2><p class="hint">Änderungen werden erst mit „Speichern“ übernommen.</p><div id="settings">${c.map((r,i)=>`<label data-config-key="${safe(r[0])}"><span>${safe(r[0]==="gemini_prompt"?"Klassifizierungs-Prompt (alle Anbieter)":r[0]==="gemini_temperature"?"Temperatur (Gemini / Groq)":r[0]==="openai_reasoning_effort"?"OpenAI Reasoning-Stufe":r[0]==="cost_input_per_million_usd"?"Input-Preis in USD / 1 Mio. Tokens":r[0]==="cost_output_per_million_usd"?"Output-Preis in USD / 1 Mio. Tokens":r[2]||r[0])}<small>${safe(r[0])}</small></span>${r[0]==="event_source"?`<select data-setting="${i}"><option value="gocath" ${r[1]==="gocath"?"selected":""}>GoCath – gocath.org/de/finde</option><option value="regnum_christi" ${r[1]==="regnum_christi"?"selected":""}>Regnum Christi – demnächst</option></select>`:r[0]==="classifier_provider"?`<select data-setting="${i}"><option value="groq" ${r[1]==="groq"?"selected":""}>Groq · GPT-OSS 20B</option><option value="gemini" ${r[1]==="gemini"?"selected":""}>Google Gemini</option><option value="openai" ${r[1]==="openai"?"selected":""}>OpenAI · GPT-6 Luna</option></select>`:r[0]==="openai_reasoning_effort"?`<select data-setting="${i}">${["none","low","medium","high"].map(v=>`<option value="${v}" ${r[1]===v?"selected":""}>${v}</option>`).join("")}</select>`:r[0]==="gemini_prompt"?`<textarea data-setting="${i}" rows="9">${safe(r[1]||"")}</textarea>`:`<input data-setting="${i}" value="${safe(r[1]||"")}" />`}</label>`).join("")}</div><button id="saveConfig">Konfiguration speichern</button></section>
 <section class="panel" data-view="tags"><h2>Standard-Tags</h2><p class="hint">Nur aktivierte Tags werden der ausgewählten KI zur Auswahl angeboten.</p><div class="tag-grid">${t.map((r,i)=>`<div class="tag-entry" data-tag-entry="${i}"><div class="tag-entry-header"><label class="tag"><input type="checkbox" data-tag="${i}" ${r[1]?.toLowerCase()==="true"?"checked":""}/><span>${safe(r[0])}</span></label><button type="button" class="remove-tag" data-remove-tag="${i}" aria-label="Standard-Tag ${safe(r[0])} löschen" title="Standard-Tag löschen">Löschen</button></div><input class="synonyms" data-synonyms="${i}" placeholder="Synonyme, mit Kommas getrennt" value="${safe(r[2]||"")}" aria-label="Synonyme für ${safe(r[0])}"/></div>`).join("")}</div><label class="add"><span>Neuen Tag ergänzen</span><input id="newTag" placeholder="z. B. Kirchenmusik"/></label><button id="saveTags">Tags speichern</button></section></div>
 <section class="panel" data-view="metrics"><h2>KI-Metriken</h2><p class="hint">Vom jeweiligen KI-Anbieter gemeldete Tokens je Lauf. Kosten sind Schätzungen auf Basis der hinterlegten Preise, keine Anbieterrechnung.</p><div class="table-scroll"><table><thead><tr><th>Run</th><th>Input</th><th>Output</th><th>Thinking</th><th>Gesamt</th><th>Kosten (USD, geschätzt)</th></tr></thead><tbody>${runs.slice(1).filter(x=>x[0]).reverse().slice(0,20).map(r=>`<tr><td>${safe(r[0]||"")}</td><td>${safe(r[6]||"–")}</td><td>${safe(r[7]||"–")}</td><td>${safe(r[8]||"–")}</td><td>${safe(r[9]||"–")}</td><td>${safe(r[10]||"nicht konfiguriert")}</td></tr>`).join("")}</tbody></table></div></section><section class="panel" data-view="results"><h2>Ergebnisse nach Run-ID</h2><p class="hint">Jeder manuelle Lauf speichert seine zehn Klassifizierungen separat. Zum Vergleichen die Run-ID auswählen.</p><label><span>Run-ID auswählen</span><select id="runFilter">${[...new Set(history.slice(1).map(r=>r[0]).filter(Boolean))].reverse().map(id=>`<option value="${safe(id)}">Run ${safe(id)}</option>`).join("")}</select></label><label class="search-label"><span>Ergebnisse durchsuchen (ab 3 Zeichen, Contains + 1 Zeichen Abweichung)</span><input id="historySearch" type="search" placeholder="z. B. Gottesdienst oder Heilige Messe" autocomplete="off" /></label><p class="hint" id="matchCount" aria-live="polite"></p><div id="historyView"></div></section>
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
   if(!confirm('Standard-Tag „'+name+'“ löschen? Die Änderung wird erst mit „Tags speichern“ übernommen.'))return;
   entry.remove();
   status("Tag zum Löschen markiert. Zum Übernehmen „Tags speichern“ klicken.");
 });
 const filter=document.querySelector<HTMLSelectElement>("#runFilter"); const view=document.querySelector<HTMLDivElement>("#historyView"); 
 const search=document.querySelector<HTMLInputElement>("#historySearch");
 const showHistory=()=>{if(!filter||!view)return; const source=history.slice(1).filter(r=>r[0]===filter.value);const term=search?.value.trim()||"";const rows=source.filter(r=>!term||norm(term).split(" ").every(part=>part.length>=3)&&matchesHistory(r,term,t));const count=document.querySelector("#matchCount");if(count)count.textContent=term&&norm(term).split(" ").some(part=>part.length<3)?"Mindestens 3 Zeichen je Suchwort eingeben":`${rows.length} von ${source.length} Veranstaltungen gefunden`;view.innerHTML=`<div class="table-scroll"><table><thead><tr><th>Veranstaltung</th><th>Standard-Tags</th><th>Weitere Tags</th><th>Begründung</th><th>Tokens</th><th>Kosten (USD)</th></tr></thead><tbody>${rows.map(r=>`<tr><td><a href="${safe(r[1])}" target="_blank" rel="noopener">${safe(r[2]||"")}</a></td><td>${safe(r[3]||"")}</td><td>${safe(r[4]||"")}</td><td><button type="button" class="reason-button" data-reason-index="${rows.indexOf(r)}">Anzeigen</button></td><td>${safe(r[12]||"–")}</td><td>${safe(r[13]||"–")}</td></tr>`).join("")}</tbody></table></div>`;view.querySelectorAll<HTMLButtonElement>(".reason-button").forEach(button=>{button.onclick=()=>{const index=Number(button.dataset.reasonIndex);const dialog=document.querySelector<HTMLDialogElement>("#reasonDialog");const text=document.querySelector<HTMLElement>("#reasonDialogText");if(dialog&&text){text.textContent=rows[index]?.[5]||"Keine Begründung vorhanden.";dialog.showModal();}};});};if(filter){filter.onchange=showHistory;if(search)search.oninput=showHistory;showHistory();}
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
if(token)load().catch(e=>status(String(e),true));
