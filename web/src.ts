import "./style.css";
declare global { interface Window { google?: { accounts: { oauth2: { initTokenClient: (settings: Record<string, unknown>) => { requestAccessToken: (opts?: Record<string,unknown>) => void } } } } } }
const SHEET="1HRyxPjLz2-WUEelplO1YAaO7gCYDyU_77DgUqEtGQ1w";
const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
const API="https://sheets.googleapis.com/v4/spreadsheets/"+SHEET;
let token="", config: string[][]=[], tags: string[][]=[], runs:string[][]=[];
const app=document.querySelector<HTMLDivElement>("#app")!;
function safe(s:string):string {return s.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#39;");}
async function api(url:string,opts:RequestInit={}) {const r=await fetch(url,{...opts,headers:{"Authorization":"Bearer "+token,"Content-Type":"application/json",...(opts.headers||{})}});if(!r.ok)throw new Error("Google Sheets HTTP "+r.status+"; Zugriff und OAuth-Freigabe prüfen");return r.json();}
const read=async(range:string):Promise<string[][]>=>{const x=await api(API+"/values/"+encodeURIComponent(range));return x.values||[]};
async function load(){[config,tags,runs]=await Promise.all([read("Config!A1:C100"),read("Tags!A1:B300"),read("Runs!A1:F100")]);render();}
function status(s:string,isError=false){const e=document.querySelector("#status");if(e){e.textContent=s;e.className=isError?"error":"";}}
function render(){
 const c=config.slice(1).filter(x=>x[0]); const t=tags.slice(1).filter(x=>x[0]);
 app.innerHTML=`<header><div class="brand"><span class="mark">✝</span><div><b>GoCath Tagging</b><small>Konfiguration & Ergebnisse · POC</small></div></div><span class="muted">${token?"Google Sheets verbunden":"Nicht verbunden"}</span></header>
 <main><section class="hero"><h1>Event-Klassifizierung</h1><p>Verwalte die Einstellungen für den manuell gestarteten GitHub-Actions-Runner. Alle Werte werden im Google Sheet gespeichert.</p>
 <div class="actions"><button id="login">${token?"Erneut autorisieren":"Mit Google anmelden"}</button><a href="https://github.com/weidmanngabriel/gocath-tag-poc/actions" target="_blank" rel="noopener">GitHub Actions öffnen ↗</a><a href="https://docs.google.com/spreadsheets/d/${SHEET}/edit" target="_blank" rel="noopener">Google Sheet öffnen ↗</a></div><p id="status" aria-live="polite"></p></section>
 ${token?`<div class="columns"><section class="panel"><h2>Konfiguration</h2><p class="hint">Änderungen werden erst mit „Speichern“ übernommen.</p><div id="settings">${c.map((r,i)=>`<label><span>${safe(r[2]||r[0])}<small>${safe(r[0])}</small></span>${r[0]==="gemini_prompt"?`<textarea data-setting="${i}" rows="9">${safe(r[1]||"")}</textarea>`:`<input data-setting="${i}" value="${safe(r[1]||"")}" />`}</label>`).join("")}</div><button id="saveConfig">Konfiguration speichern</button></section>
 <section class="panel"><h2>Standard-Tags</h2><p class="hint">Nur aktivierte Tags werden Gemini zur Auswahl angeboten.</p><div class="tag-grid">${t.map((r,i)=>`<label class="tag"><input type="checkbox" data-tag="${i}" ${r[1]?.toLowerCase()==="true"?"checked":""}/><span>${safe(r[0])}</span></label>`).join("")}</div><label class="add"><span>Neuen Tag ergänzen</span><input id="newTag" placeholder="z. B. Kirchenmusik"/></label><button id="saveTags">Tags speichern</button></section></div>
 <section class="panel"><h2>Letzte Läufe</h2><div class="table-scroll"><table><thead><tr><th>Run-ID</th><th>Beginn</th><th>Ende</th><th>Status</th><th>Klassifiziert</th></tr></thead><tbody>${runs.slice(1).filter(x=>x[0]).reverse().slice(0,15).map(r=>`<tr>${r.slice(0,5).map(v=>`<td>${safe(v||"")}</td>`).join("")}</tr>`).join("")}</tbody></table></div></section>`:`<section class="panel"><h2>Google-Anmeldung erforderlich</h2><p>Der Google-Account benötigt Bearbeiterzugriff auf das Sheet. Es werden keine API-Schlüssel im Browser gespeichert.</p>${!CLIENT_ID?"<p class='error'>VITE_GOOGLE_CLIENT_ID ist noch nicht für den GitHub-Pages-Build konfiguriert.</p>":""}</section>`}
 <footer>GoCath Proof of Concept · Keine automatische Ausführung</footer></main>`;
 document.querySelector<HTMLButtonElement>("#login")!.onclick=login;
 if(token){
 document.querySelector<HTMLButtonElement>("#saveConfig")!.onclick=async()=>{try{const rows=c.map((r,i)=>[r[0],(document.querySelector<HTMLInputElement>(`[data-setting="${i}"]`)!.value),r[2]||""]);await api(API+"/values/"+encodeURIComponent("Config!A2:C"+(rows.length+1))+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({range:"Config!A2:C"+(rows.length+1),majorDimension:"ROWS",values:rows})});status("Konfiguration gespeichert");await load();}catch(e){status(String(e),true)}};
 document.querySelector<HTMLButtonElement>("#saveTags")!.onclick=async()=>{try{const rows=t.map((r,i)=>[r[0],document.querySelector<HTMLInputElement>(`[data-tag="${i}"]`)!.checked?"true":"false"]);const name=document.querySelector<HTMLInputElement>("#newTag")!.value.trim();if(name&&!rows.some(x=>x[0].toLowerCase()===name.toLowerCase()))rows.push([name,"true"]);await api(API+"/values/"+encodeURIComponent("Tags!A2:B"+(rows.length+1))+"?valueInputOption=RAW",{method:"PUT",body:JSON.stringify({range:"Tags!A2:B"+(rows.length+1),majorDimension:"ROWS",values:rows})});status("Tags gespeichert");await load();}catch(e){status(String(e),true)}};
 }
}
function login(){if(!CLIENT_ID){status("OAuth Client-ID fehlt. GitHub Variable VITE_GOOGLE_CLIENT_ID konfigurieren.",true);return;}
 if(!window.google?.accounts?.oauth2){status("Google Identity Services lädt noch; Seite neu laden.",true);return;}
 const client=window.google.accounts.oauth2.initTokenClient({client_id:CLIENT_ID,scope:"https://www.googleapis.com/auth/spreadsheets",callback:async(r:{access_token?:string,error?:string})=>{if(!r.access_token){status("Anmeldung fehlgeschlagen: "+(r.error||"unbekannt"),true);return;}token=r.access_token;try{await load();status("Google Sheets verbunden")}catch(e){status(String(e),true)}}});
 client.requestAccessToken();
}
render();
