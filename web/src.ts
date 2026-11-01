import "./style.css";
declare global {interface Window {google?:{accounts:{oauth2:{initTokenClient:(options:Record<string,unknown>)=>{requestAccessToken:()=>void}}}}}}
const SHEET="1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w";
const API="https://sheets.googleapis.com/v4/spreadsheets/"+SHEET;
const CLIENT_ID=import.meta.env.VITE_GOOGLE_CLIENT_ID as string|undefined;
const SCOPE="https://www.googleapis.com/auth/spreadsheets";
const STORE="gocath_sheets_oauth_session", REMEMBER="gocath_sheets_oauth_remembered_v1";
type Session={accessToken:string,expiresAt:number,clientId?:string,scope?:string};
function readSession(storage:Storage,key:string):Session|null{
 try{const value=JSON.parse(storage.getItem(key)||"null") as Session|null;
 if(value&&value.accessToken&&value.expiresAt>Date.now()+30000&&value.clientId===CLIENT_ID&&value.scope===SCOPE)return value;
 storage.removeItem(key);}catch{}return null;
}
const session=readSession(sessionStorage,STORE)||readSession(localStorage,REMEMBER);
let token=session?.accessToken||"", rows:string[][]=[], configRows:string[][]=[], activeView:"criteria"|"config"|"runs"="criteria", search="", activeGroup="";
const root=document.querySelector<HTMLDivElement>("#app")!;
const esc=(s:unknown)=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]||c));
function notify(message:string,error=false){const el=document.querySelector<HTMLElement>("#status");if(el){el.textContent=message;el.className=error?"error":"";}}
async function api(range:string,body?:unknown){
 const response=await fetch(API+"/values/"+encodeURIComponent(range)+(body?"?valueInputOption=RAW":""),{method:body?"PUT":"GET",headers:{Authorization:"Bearer "+token,"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
 if(response.status===401){logout();throw Error("Google-Sitzung abgelaufen. Bitte erneut anmelden.");}
 if(!response.ok)throw Error("Google Sheets HTTP "+response.status);return response.json();
}
async function load(){const [criteria,settings]=await Promise.all([api("Criteria!A1:I1500"),api("Config!A1:B500")]);rows=criteria.values||[];configRows=settings.values||[];render();notify("Kriterien und Konfiguration geladen.");}
function logout(){token="";sessionStorage.removeItem(STORE);localStorage.removeItem(REMEMBER);render();}
function formatOptions(raw:string){try{return (JSON.parse(raw||"[]") as Array<{value?:string,label?:string,description?:string}>).map(o=>(o.value||o.label||"")+" | "+(o.description||"")).join("\n");}catch{return raw;}}
function encodeOptions(raw:string,type:string){const result=raw.split("\n").map(s=>s.trim()).filter(Boolean).map(line=>{const [head,...parts]=line.split("|");const key=head.trim();return type==="score"?{label:key,description:parts.join("|").trim()}:{value:key,description:parts.join("|").trim()};});const max=type==="choice"?255:10;if(result.length<2||result.length>max)throw Error("Erwartet 2 bis "+max+" Antwortoptionen.");const keys=result.map(x=>("value" in x?x.value:x.label));if(keys.some(x=>!x)||new Set(keys).size!==keys.length)throw Error("Antwortoptionen müssen eindeutige Namen haben.");return JSON.stringify(result);}
function editor(row:string[],idx:number){const n=idx+1,type=row[7]||"predicate";return `<details class="question-card"><summary><strong>${esc(row[2]||row[0])}</strong><span class="question-type">${esc(type==="predicate"?"Wahrscheinlichkeit":type==="choice"?"Einzelauswahl":"Bewertungsskala")}</span></summary><div class="question-fields">

<label>Titel<input data-row="${n}" data-col="C" value="${esc(row[2])}"></label>
<label>Entscheidungsregel<textarea rows="3" data-row="${n}" data-col="D">${esc(row[3])}</textarea></label>

<label>Relevanzgewicht<input type="number" min="0" max="3" step="0.1" data-row="${n}" data-col="F" value="${esc(row[5]||"0")}" ${type!=="predicate"?"disabled":""}></label>
<label>Trefferschwelle<input type="number" min="0" max="1" step="0.05" data-row="${n}" data-col="G" value="${esc(row[6]||"0.65")}"></label>
<label>Fragetyp<select data-row="${n}" data-col="H">${["predicate","choice","score"].map(t=>`<option value="${t}" ${t===type?"selected":""}>${t}</option>`).join("")}</select></label>
<label>Antwortoptionen (Name | Beschreibung)<textarea rows="4" data-row="${n}" data-col="I">${esc(formatOptions(row[8]||""))}</textarea></label>
<div class="criterion-delete"><button type="button" class="delete-question" data-delete-row="${n}" data-delete-id="${esc(row[0])}">Frage löschen</button></div></div></details>`;}
function groupedQuestions(items:Array<{r:string[],i:number}>):string {
 const groups=new Map<string,Array<{r:string[],i:number}>>();
 for(const item of items){const name=item.r[1]?.trim()||"Sonstiges";if(!groups.has(name))groups.set(name,[]);groups.get(name)!.push(item);}
 const names=[...groups.keys()].sort((a,b)=>a.localeCompare(b,"de"));
 if(!names.includes(activeGroup))activeGroup=names[0]||"";
 return `<div class="question-tabs" role="tablist" aria-label="Fragebogenbereiche">${names.map((name,i)=>`<button type="button" role="tab" data-group="${esc(name)}" aria-selected="${name===activeGroup}">${esc(name)} <span>${groups.get(name)!.length}</span></button>`).join("")}</div>
 <div class="question-groups">${names.map(name=>`<section class="question-group" data-panel="${esc(name)}" role="tabpanel" ${name!==activeGroup?"hidden":""}><div class="question-group-heading"><h3>${esc(name)}</h3><p>${groups.get(name)!.length} Fragen · alphabetisch sortiert</p></div><div class="question-list">${groups.get(name)!.sort((a,b)=>(a.r[2]||"").localeCompare(b.r[2]||"","de")).map(x=>editor(x.r,x.i)).join("")}</div></section>`).join("")}</div>`;
}
function bindGroups(){
 document.querySelectorAll<HTMLButtonElement>("[data-group]").forEach(button=>button.addEventListener("click",()=>{activeGroup=button.dataset.group||"";document.querySelectorAll<HTMLElement>("[data-panel]").forEach(panel=>panel.hidden=panel.dataset.panel!==activeGroup);document.querySelectorAll<HTMLButtonElement>("[data-group]").forEach(tab=>tab.setAttribute("aria-selected",String(tab.dataset.group===activeGroup)));const selected=document.querySelector("#selectedCategory");if(selected)selected.textContent=activeGroup;}));
}
function configEditor(){return `<div class="config-list">${configRows.slice(1).map((r,i)=>r[0]?`<label class="config-entry"><span><strong>${esc(r[0])}</strong></span><textarea data-config-row="${i+2}" rows="${r[1]?.length>130?7:2}">${esc(r[1]||"")}</textarea></label>`:"").join("")}</div><p class="hint">Werte werden beim Verlassen des Feldes im Google Sheet gespeichert. Technische Prompt-Regeln sind nicht hier editierbar.</p>`;}
let runView:"classification"|"tagging"="classification";
type RcRun={kind?:string;tagged?:number;run_id:string;started_at:string;mode?:string;source_count?:number;queued?:number;attempted?:number;classified?:number;failed?:number;usage?:{total_tokens?:number};cost_usd_estimated?:number};
const RUNS_URL="https://raw.githubusercontent.com/weidmanngabriel/gocath-tag-poc/rc-data/runs.json";
function runChart(items:RcRun[],value:(r:RcRun)=>number,title:string){
 const max=Math.max(1,...items.map(value)),step=650/Math.max(1,items.length),width=Math.min(24,step*0.65);
 return `<svg class="rc-history-chart" viewBox="0 0 680 160" role="img" aria-label="${esc(title)} pro Lauf"><line x1="20" y1="132" x2="670" y2="132" stroke="#cbd9d1"/>${items.map((r,i)=>{const h=Math.max(0,value(r))/max*115;return `<rect x="${20+i*step+(step-width)/2}" y="${132-h}" width="${width}" height="${h}" rx="2" fill="#397a61"><title>${esc(r.run_id)}: ${value(r)}</title></rect>`;}).join("")}<text x="20" y="12" font-size="11" fill="#61756b">${max.toLocaleString("de-DE")}</text><text x="20" y="152" font-size="11" fill="#61756b">${esc(items[0]?.started_at.slice(0,10)||"")}</text><text x="670" y="152" font-size="11" text-anchor="end" fill="#61756b">${esc(items[items.length-1]?.started_at.slice(0,10)||"")}</text></svg>`;
}
async function loadRuns(){
 const host=document.querySelector<HTMLElement>("#runsHistory");if(!host)return;
 host.textContent="Lade Laufhistorie …";
 try{
  const response=await fetch(RUNS_URL,{cache:"no-store"});if(!response.ok)throw Error("HTTP "+response.status);
  const payload=await response.json() as {runs?:RcRun[]};
  if(!Array.isArray(payload.runs))throw Error("Ungültiges runs.json-Format");
  const all=payload.runs.filter(r=>r.run_id&&r.started_at&&(runView==="tagging"?r.kind==="tagging":r.kind!=="tagging")).sort((a,b)=>a.started_at.localeCompare(b.started_at));
  if(!all.length){host.innerHTML=`<p class="hint">Noch keine ${runView==="tagging"?"Tagging-":"Klassifizierungs-"}Läufe gespeichert. Ältere Tagging-Läufe werden nicht rückwirkend geschätzt.</p>`;return;}
  const n=(x:number)=>x.toLocaleString("de-DE");const sum=(f:(r:RcRun)=>number)=>all.reduce((a,r)=>a+f(r),0);
  const latest=all.slice(-30);const charts:[string,(r:RcRun)=>number][]=[[runView==="tagging"?"Getaggt":"Klassifiziert",r=>runView==="tagging"?(r.tagged||0):(r.classified||0)],["Fehler",r=>r.failed||0],["Tokens",r=>r.usage?.total_tokens||0],["Kosten (USD, geschätzt)",r=>r.cost_usd_estimated||0]];
  host.innerHTML=`<p class="hint">${runView==="tagging"?"Tagging":"Klassifizierung"}-Historie aus rc-data/runs.json. Kosten sind Schätzungen, keine Rechnungsbeträge. Fehlt eine konfigurierte Preisgrundlage, werden keine Kosten ausgewiesen.</p><div class="rc-kpis"><div><small>Läufe</small><b>${n(all.length)}</b></div><div><small>Verarbeitet</small><b>${n(sum(r=>r.attempted||0))}</b></div><div><small>${runView==="tagging"?"Getaggt":"Klassifiziert"}</small><b>${n(sum(r=>runView==="tagging"?(r.tagged||0):(r.classified||0)))}</b></div><div><small>Fehler</small><b>${n(sum(r=>r.failed||0))}</b></div><div><small>Tokens</small><b>${n(sum(r=>r.usage?.total_tokens||0))}</b></div><div><small>Kosten (USD)*</small><b>${all.some(r=>r.cost_usd_estimated==null)?"–":sum(r=>r.cost_usd_estimated||0).toFixed(4)}</b></div></div><div class="rc-charts">${charts.map(([name,fn])=>`<div><h3>${esc(name)}</h3>${runChart(latest,fn,name)}</div>`).join("")}</div><h3>Letzte Läufe</h3><div class="table-scroll"><table><thead><tr><th>Datum</th><th>Run-Nummer</th><th>Modus</th><th>Geprüft</th><th>Verarbeitet</th><th>${runView==="tagging"?"Getaggt":"Klassifiziert"}</th><th>Fehler</th><th>Tokens</th><th>Kosten USD*</th></tr></thead><tbody>${[...all].reverse().slice(0,30).map(r=>`<tr><td>${esc(new Date(r.started_at).toLocaleString("de-DE"))}</td><td><a target="_blank" rel="noopener noreferrer" href="https://github.com/weidmanngabriel/gocath-tag-poc/actions/runs/${encodeURIComponent(r.run_id)}">${esc(r.run_id)}</a></td><td>${esc(r.mode||"–")}</td><td>${n(r.source_count||0)}</td><td>${n(r.attempted||0)}</td><td>${n(runView==="tagging"?(r.tagged||0):(r.classified||0))}</td><td>${n(r.failed||0)}</td><td>${n(r.usage?.total_tokens||0)}</td><td>${r.cost_usd_estimated==null?"–":r.cost_usd_estimated.toFixed(5)}</td></tr>`).join("")}</tbody></table></div>`;
 }catch(e){host.textContent="Run-Historie konnte nicht geladen werden: "+String(e);}
}
function render(){
 const matches=rows.slice(1).map((r,i)=>({r,i:i+1})).filter(x=>x.r[0]&&[x.r[0],x.r[1],x.r[2],x.r[3]].join(" ").toLowerCase().includes(search.toLowerCase()));
 root.innerHTML=`<header><div class="brand"><span class="mark">✝</span><div><b>GoCath · Criteria</b><small>RC-Fragebogen bearbeiten</small></div></div><span class="muted">${token?"Google Sheets verbunden":"Nicht verbunden"}</span></header><main><section class="hero"><h1>RC-Verwaltung</h1><p>Fragen werden direkt im Google Sheet gespeichert. Semantische Änderungen erfordern einen bewusst gestarteten reclassify-Lauf.</p><div class="actions"><button id="login">${token?"Erneut anmelden":"Mit Google anmelden"}</button>${token?'<button id="logout">Abmelden</button>':""}<a href="/rc/">RC-Katalog</a><a href="https://docs.google.com/spreadsheets/d/${SHEET}/edit" target="_blank" rel="noopener">Google Sheet</a></div>${!token?'<label><input type="checkbox" id="remember"> Auf diesem Gerät bis zum Token-Ablauf angemeldet bleiben</label>':""}<p id="status" aria-live="polite"></p></section>${token?`<nav class="main-tabs" role="tablist" aria-label="Verwaltungsbereiche"><button type="button" data-main-view="criteria" aria-selected="${activeView==="criteria"}">Kriterien</button><button type="button" data-main-view="config" aria-selected="${activeView==="config"}">Konfiguration</button><button type="button" data-main-view="runs" aria-selected="${activeView==="runs"}">Runs</button></nav><section class="panel" ${activeView!=="criteria"?"hidden":""}><h2>Kriterien (${matches.length})</h2><input id="search" type="search" placeholder="Kriterien suchen" value="${esc(search)}"><p class="hint">Bestehende Fragen ändern und bei Verlassen des Feldes speichern. Neue Fragen direkt hier hinzufügen; IDs bleiben unverändert.</p><div id="questions">${groupedQuestions(matches)}</div><details class="question-card"><summary><strong>+ Neue Frage hinzufügen</strong></summary><div class="question-fields"><label>Titel<input id="newTitle" placeholder="Titel der Frage"></label><p class="hint">Bereich: <strong id="selectedCategory">${esc(activeGroup||"Bitte zuerst einen Bereich auswählen")}</strong></p><label>Entscheidungsregel<textarea id="newDescription" rows="3"></textarea></label><label>Fragetyp<select id="newType"><option value="predicate">Wahrscheinlichkeit</option><option value="choice">Einzelauswahl</option><option value="score">Bewertungsskala</option></select></label><label>Antwortoptionen (Name | Beschreibung)<textarea id="newOptions" rows="4"></textarea></label><label>Relevanzgewicht<input id="newWeight" type="number" min="0" max="3" step="0.1" value="0"></label><label>Trefferschwelle<input id="newThreshold" type="number" min="0" max="1" step="0.05" value="0.65"></label><button id="addQuestion" type="button">Frage hinzufügen</button></div></details></section><section class="panel" ${activeView!=="config"?"hidden":""}><h2>Konfiguration</h2>${configEditor()}</section><section class="panel" ${activeView!=="runs"?"hidden":""}><h2>Runs</h2><nav class="run-tabs" role="tablist" aria-label="Run-Typ"><button type="button" data-run-view="classification" aria-selected="${runView==="classification"}">Klassifizierungen</button><button type="button" data-run-view="tagging" aria-selected="${runView==="tagging"}">Tagging</button></nav><div id="runsHistory">Lade Laufhistorie …</div></section>`:""}</main>`;
 document.querySelector<HTMLButtonElement>("#login")?.addEventListener("click",login);
 document.querySelector<HTMLButtonElement>("#logout")?.addEventListener("click",logout);
 document.querySelector<HTMLInputElement>("#search")?.addEventListener("input",e=>{
 search=(e.target as HTMLInputElement).value;
 const matches=rows.slice(1).map((r,i)=>({r,i:i+1})).filter(x=>x.r[0]&&[x.r[0],x.r[1],x.r[2],x.r[3]].join(" ").toLowerCase().includes(search.toLowerCase()));
 const container=document.querySelector("#questions");if(container)container.innerHTML=groupedQuestions(matches);bindGroups();bindFields();
 });
 document.querySelectorAll<HTMLButtonElement>("[data-main-view]").forEach(el=>el.addEventListener("click",()=>{activeView=el.dataset.mainView==="config"?"config":el.dataset.mainView==="runs"?"runs":"criteria";render();}));
 document.querySelectorAll<HTMLTextAreaElement>("[data-config-row]").forEach(el=>el.addEventListener("change",async()=>{const row=Number(el.dataset.configRow);const previous=configRows[row-1]?.[1]||"";const value=el.value;if(value===previous)return;try{notify("Speichert …");await api("Config!B"+row,{values:[[value]]});configRows[row-1][1]=value;notify("Konfiguration gespeichert.");}catch(e){el.value=previous;notify("Nicht gespeichert: "+String(e),true);}}));
 document.querySelector<HTMLButtonElement>("#addQuestion")?.addEventListener("click",addQuestion);
 bindGroups();
 bindFields();
 document.querySelectorAll<HTMLButtonElement>("[data-run-view]").forEach(el=>el.addEventListener("click",()=>{runView=el.dataset.runView==="tagging"?"tagging":"classification";render();}));
 if(activeView==="runs")void loadRuns();
}
function bindFields(){
 document.querySelectorAll<HTMLButtonElement>("[data-delete-row]").forEach(button=>button.addEventListener("click",async()=>{
  const row=Number(button.dataset.deleteRow),id=button.dataset.deleteId||"";
  if(!row||rows[row-1]?.[0]!==id){notify("Frage konnte nicht eindeutig zugeordnet werden. Neu laden.",true);return;}
  if(!window.confirm(`Frage „${rows[row-1][2]||id}“ wirklich dauerhaft löschen? Diese Aktion kann nicht rückgängig gemacht werden.`))return;
  button.disabled=true;
  try{
   const meta=await fetch(API+"?fields=sheets(properties(sheetId,title))",{headers:{Authorization:"Bearer "+token}});
   if(!meta.ok)throw Error("Tabelleninformationen nicht verfügbar ("+meta.status+")");
   const info=await meta.json();const sheet=info.sheets?.find((x:{properties:{title:string,sheetId:number}})=>x.properties.title==="Criteria");
   if(!sheet)throw Error("Criteria-Tabelle fehlt");
   const url=API+":batchUpdate";const response=await fetch(url,{method:"POST",headers:{Authorization:"Bearer "+token,"Content-Type":"application/json"},body:JSON.stringify({requests:[{deleteDimension:{range:{sheetId:sheet.properties.sheetId,dimension:"ROWS",startIndex:row-1,endIndex:row}}}]})});
   if(!response.ok)throw Error("Google Sheets HTTP "+response.status);
   await load();notify("Frage gelöscht.");
  }catch(e){button.disabled=false;notify("Löschen fehlgeschlagen: "+String(e),true);}
 }));
 document.querySelectorAll<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>("[data-row]").forEach(el=>el.addEventListener("change",async()=>{
 const row=Number(el.dataset.row),col=el.dataset.col!,pos=col.charCodeAt(0)-65,current=rows[row-1]?.[pos]||"";
 let value=el instanceof HTMLInputElement&&el.type==="checkbox"?(el.checked?"true":"false"):el.value.trim();
 try{const type=col==="H"?value:rows[row-1]?.[7]||"predicate";
 if(col==="I"){if(type==="predicate")return;value=encodeOptions(value,type);}
 if(col==="F"||col==="G"){const n=Number(value);if(!Number.isFinite(n)||n<0||(col==="G"&&n>1)||(col==="F"&&n>3)||(col==="F"&&type!=="predicate"&&n!==0))throw Error("Ungültiger Zahlenwert.");}
 if(col==="H"&&type!=="predicate"){const optionEl=document.querySelector<HTMLTextAreaElement>(`[data-row="${row}"][data-col="I"]`);const options=encodeOptions(optionEl?.value||"",type);await api("Criteria!I"+row,{values:[[options]]});rows[row-1][8]=options;await api("Criteria!F"+row,{values:[["0"]]});rows[row-1][5]="0";}
 if(value===current)return;
 notify("Speichert …");await api("Criteria!"+col+row,{values:[[value]]});rows[row-1][pos]=value;notify("Gespeichert.");if(col==="H")render();
 }catch(e){notify("Nicht gespeichert: "+String(e),true);el.value=col==="I"?formatOptions(current):current;}
 }));
}
async function addQuestion(){
 const value=(id:string)=>(document.querySelector<HTMLInputElement|HTMLTextAreaElement|HTMLSelectElement>("#"+id)?.value||"").trim();
 const title=value("newTitle"),category=activeGroup,description=value("newDescription");
 const type=value("newType")||"predicate",weight=Number(value("newWeight")),threshold=Number(value("newThreshold"));
 if(!title||!category||!description){notify("Titel, Bereich und Entscheidungsregel sind erforderlich.",true);return;}
 if(!Number.isFinite(weight)||weight<0||weight>3||!Number.isFinite(threshold)||threshold<0||threshold>1){notify("Gewicht oder Trefferschwelle ungültig.",true);return;}
 let options="[]";
 try{if(type!=="predicate")options=encodeOptions(value("newOptions"),type);}catch(e){notify(String(e),true);return;}
 const slug=title.toLowerCase().normalize("NFKD").replace(/[\\u0300-\\u036f]/g,"").replace(/[^a-z0-9]+/g,"_").replace(/^_|_$/g,"").slice(0,55);
 const ids=new Set(rows.slice(1).map(r=>r[0]));
 let newId="rc_"+slug,index=2;while(ids.has(newId)){newId="rc_"+slug+"_"+index++;}
 const newRow=[newId,category,title,description,"true",type==="predicate"?String(weight):"0",String(threshold),type,options];
 try{
  notify("Speichert neue Frage …");
  const response=await fetch(API+"/values/"+encodeURIComponent("Criteria!A:I")+":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",{method:"POST",headers:{Authorization:"Bearer "+token,"Content-Type":"application/json"},body:JSON.stringify({values:[newRow]})});
  if(!response.ok)throw Error("Google Sheets HTTP "+response.status);
  await load();notify("Frage hinzugefügt: "+newId);
 }catch(e){notify("Nicht gespeichert: "+String(e),true);}
}
function login(){
 if(!CLIENT_ID||!window.google?.accounts?.oauth2){notify("Google OAuth nicht verfügbar. Client-ID oder Google-Skript prüfen.",true);return;}
 const remember=Boolean(document.querySelector<HTMLInputElement>("#remember")?.checked);
 window.google.accounts.oauth2.initTokenClient({client_id:CLIENT_ID,scope:SCOPE,prompt:"",callback:async(r:{access_token?:string,expires_in?:number,error?:string})=>{
 if(!r.access_token){notify("Anmeldung fehlgeschlagen: "+(r.error||"unbekannt"),true);return;}
 token=r.access_token;const entry:Session={accessToken:token,expiresAt:Date.now()+Number(r.expires_in||0)*1000,clientId:CLIENT_ID,scope:SCOPE};if(r.expires_in){sessionStorage.setItem(STORE,JSON.stringify(entry));if(remember)localStorage.setItem(REMEMBER,JSON.stringify(entry));else localStorage.removeItem(REMEMBER);}
 try{await load();}catch(e){notify(String(e),true);}
 }}).requestAccessToken();
}
render();if(token)load().catch(e=>notify(String(e),true));
