"""
Lead Scraper - Web UI
---------------------
Put this file in the SAME folder as business_scraper.py, then run:

    pip install flask selenium webdriver-manager
    python app.py

It opens http://127.0.0.1:5000 in your browser.
"""

import csv
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, Response, jsonify, request

from business_scraper import setup_driver, collect_place_urls, extract_place, place_key
from social import find_social_links, SOCIAL_FIELDS

OUT_FIELDS = ["name", "address", "phone", "website", "maps_url", "search"] + SOCIAL_FIELDS
AUTOSAVE_FILE = "leads_latest.csv"

app = Flask(__name__)
lock = threading.Lock()
state = {
    "running": False,
    "stop": False,
    "status": "Idle",
    "rows": [],
    "log": [],
    "total_urls": 0,
    "done": 0,
    "version": 0,
}


def log(msg):
    with lock:
        state["log"].append(msg)
        state["log"] = state["log"][-200:]


def autosave():
    with lock:
        rows = list(state["rows"])
    with open(AUTOSAVE_FILE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=OUT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def enrich(row):
    """Background task: look up social links + email from the business website."""
    try:
        info = find_social_links(row.get("website", ""))
    except Exception:
        info = {}
    with lock:
        row.update(info)
        state["version"] += 1


def run_job(queries, limit, headless, find_social=True):
    max_total = limit if limit > 0 else 10**6
    seen_urls, seen_biz = set(), set()
    driver = None
    pool = ThreadPoolExecutor(max_workers=4) if find_social else None
    try:
        driver = setup_driver(headless)
        for query in queries:
            if state["stop"] or len(state["rows"]) >= max_total:
                break
            with lock:
                state["status"] = f"Collecting listings: {query}"
            log(f"Searching: {query}")
            urls = collect_place_urls(driver, query, max_total * 2)
            urls = [u for u in urls if place_key(u) not in seen_urls]
            log(f"  {len(urls)} new listings found")
            with lock:
                state["total_urls"] += len(urls)
                state["status"] = f"Extracting details: {query}"

            for u in urls:
                if state["stop"] or len(state["rows"]) >= max_total:
                    break
                seen_urls.add(place_key(u))
                with lock:
                    state["done"] += 1
                try:
                    row = extract_place(driver, u)
                except Exception as e:
                    log(f"  skipped one ({type(e).__name__})")
                    continue
                if not row:
                    continue
                key = (row["name"].lower(), row["address"].lower())
                if key in seen_biz:
                    continue
                seen_biz.add(key)
                row["search"] = query
                row.update({f: "" for f in SOCIAL_FIELDS})
                with lock:
                    state["rows"].append(row)
                    state["version"] += 1
                    n = len(state["rows"])
                if pool and row.get("website"):
                    pool.submit(enrich, row)
                log(f"[{n}] {row['name']}")
                if n % 25 == 0:
                    autosave()
    except Exception as e:
        log(f"ERROR: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        if pool:
            with lock:
                state["status"] = "Finishing social media lookups..."
            pool.shutdown(wait=True, cancel_futures=state["stop"])
        autosave()
        with lock:
            state["running"] = False
            state["status"] = "Stopped" if state["stop"] else "Finished"
        log(f"Done. {len(state['rows'])} results saved to {AUTOSAVE_FILE}")


@app.route("/")
def index():
    return Response(HTML, mimetype="text/html")


@app.route("/start", methods=["POST"])
def start():
    data = request.get_json(force=True)
    category = (data.get("category") or "").strip()
    areas = [a.strip() for a in (data.get("areas") or "").splitlines() if a.strip()]
    extra = [q.strip() for q in (data.get("queries") or "").splitlines() if q.strip()]
    if category and areas:
        queries = [f"{category} in {a}" for a in areas]
    else:
        queries = []
    queries += extra
    if not queries:
        return jsonify(ok=False, error="Enter a category and at least one area (or custom queries)."), 400
    with lock:
        if state["running"]:
            return jsonify(ok=False, error="A job is already running."), 400
        state.update(running=True, stop=False, status="Starting...", rows=[],
                     log=[], total_urls=0, done=0)
    t = threading.Thread(
        target=run_job,
        args=(queries, int(data.get("limit") or 0), bool(data.get("headless", True)),
              bool(data.get("find_social", True))),
        daemon=True,
    )
    t.start()
    return jsonify(ok=True, queries=queries)


@app.route("/stop", methods=["POST"])
def stop():
    state["stop"] = True
    return jsonify(ok=True)


@app.route("/status")
def status():
    with lock:
        return jsonify(running=state["running"], status=state["status"],
                       count=len(state["rows"]), total_urls=state["total_urls"],
                       done=state["done"], version=state["version"], log=state["log"][-60:])


@app.route("/results")
def results():
    with lock:
        return jsonify(rows=list(state["rows"]))


HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lead Scraper</title>
<style>
:root{--bg:#f5f6f8;--card:#fff;--text:#1d2330;--muted:#6b7385;--line:#e2e5ec;--accent:#2b6cff;--danger:#d93b3b;--ok:#1f9d55}
@media(prefers-color-scheme:dark){:root{--bg:#14171e;--card:#1c2029;--text:#e8ebf2;--muted:#8d95a8;--line:#2c3240;--accent:#5b8dff;--danger:#ff6b6b;--ok:#4cc27f}}
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 system-ui,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--text)}
header{padding:16px 24px;border-bottom:1px solid var(--line);background:var(--card);font-size:18px;font-weight:600}
main{max-width:1300px;margin:0 auto;padding:20px;display:grid;gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
h2{margin:0 0 12px;font-size:15px}
label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
input[type=text],input[type=number],textarea,select{width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--text);font:inherit}
textarea{min-height:90px;resize:vertical}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
button{padding:8px 16px;border:0;border-radius:6px;background:var(--accent);color:#fff;font:inherit;font-weight:600;cursor:pointer}
button.sec{background:transparent;color:var(--text);border:1px solid var(--line)}
button.danger{background:var(--danger)}
button:disabled{opacity:.5;cursor:not-allowed}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;margin:8px 0}
.bar>div{height:100%;width:0;background:var(--ok);transition:width .3s}
#log{font:12px/1.5 ui-monospace,Consolas,monospace;color:var(--muted);max-height:130px;overflow:auto;white-space:pre-wrap}
.tablewrap{overflow:auto;max-height:640px;border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
td.wrap{white-space:normal;min-width:220px}
th{position:sticky;top:0;background:var(--card);cursor:pointer;user-select:none;font-size:12px;text-transform:uppercase;color:var(--muted)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.pill{font-size:11px;padding:2px 8px;border-radius:10px;background:var(--bg);border:1px solid var(--line);color:var(--muted)}
.chk{display:flex;align-items:center;gap:6px;margin-top:22px}
</style></head><body>
<header>Lead Scraper</header>
<main>

<section class="card">
  <h2>1. Search</h2>
  <div class="grid">
    <div><label>Category (what to find)</label><input type="text" id="category" placeholder="cafe, dentist, hair salon..."></div>
    <div><label>Max results (0 = no limit)</label><input type="number" id="limit" value="0" min="0"></div>
    <div class="chk"><input type="checkbox" id="headless" checked><label style="margin:0">Hide browser (headless)</label></div>
    <div class="chk"><input type="checkbox" id="findSocial" checked><label style="margin:0">Find social media &amp; email (slower)</label></div>
  </div>
  <div class="grid" style="margin-top:12px">
    <div><label>Areas, one per line (each becomes "category in area")</label>
      <textarea id="areas" placeholder="Centrs Riga&#10;Agenskalns Riga&#10;Teika Riga&#10;Purvciems Riga&#10;Imanta Riga"></textarea></div>
    <div><label>Optional: extra custom queries, one per line</label>
      <textarea id="queries" placeholder="restaurant near Riga Central Market"></textarea></div>
  </div>
  <div class="row" style="margin-top:12px">
    <button id="startBtn" onclick="startJob()">Start scraping</button>
    <button id="stopBtn" class="danger" onclick="stopJob()" disabled>Stop</button>
    <span id="statusTxt" class="pill">Idle</span>
    <span id="countTxt" class="pill">0 results</span>
  </div>
  <div class="bar"><div id="barFill"></div></div>
  <div id="log"></div>
</section>

<section class="card">
  <h2>2. Filter results</h2>
  <div class="grid">
    <div><label>Name contains</label><input type="text" id="fName" placeholder="e.g. coffee"></div>
    <div><label>Name does NOT contain</label><input type="text" id="fExName" placeholder="e.g. starbucks, narvesen"></div>
    <div><label>Address contains</label><input type="text" id="fAddr" placeholder="e.g. Brivibas"></div>
    <div><label>Search / area it came from</label><select id="fSearch"><option value="">All</option></select></div>
    <div><label>Phone</label>
      <select id="fPhone"><option value="">Any</option><option value="has">Has phone</option><option value="none">No phone</option><option value="mobile">Mobile only (+371 2...)</option></select></div>
    <div><label>Website</label>
      <select id="fWeb"><option value="">Any</option><option value="has">Has any website</option><option value="none">No website</option><option value="own">Own website only</option><option value="social">Social media page only</option></select></div>
    <div><label>Chains / duplicates</label>
      <select id="fChain"><option value="">Any</option><option value="unique">Unique names only</option><option value="chain">Repeated names only (chains)</option></select></div>
    <div><label>Complete leads</label>
      <select id="fComplete"><option value="">Any</option><option value="all">Has phone AND website</option><option value="phoneNoWeb">Has phone, NO website</option></select></div>
    <div><label>Social media</label>
      <select id="fSocial"><option value="">Any</option><option value="has">Has any social</option><option value="none">No social found</option>
        <option value="facebook">Has Facebook</option><option value="instagram">Has Instagram</option><option value="tiktok">Has TikTok</option>
        <option value="linkedin">Has LinkedIn</option><option value="youtube">Has YouTube</option><option value="twitter">Has X / Twitter</option></select></div>
    <div><label>Email</label>
      <select id="fEmail"><option value="">Any</option><option value="has">Has email</option><option value="none">No email</option></select></div>
    <div><label>Sort by</label>
      <select id="fSort"><option value="">Scrape order</option><option value="name">Name A-Z</option><option value="address">Address A-Z</option><option value="search">Search / area</option></select></div>
  </div>
  <div class="row" style="margin-top:12px">
    <button class="sec" onclick="clearFilters()">Clear filters</button>
    <button onclick="exportCSV()">Export filtered CSV</button>
    <button class="sec" onclick="copyCol('phone')">Copy phones</button>
    <button class="sec" onclick="copyCol('website')">Copy websites</button>
    <button class="sec" onclick="copyCol('email')">Copy emails</button>
    <span id="shownTxt" class="pill">Showing 0 of 0</span>
  </div>
</section>

<section class="card">
  <div class="tablewrap"><table>
    <thead><tr>
      <th onclick="setSort('name')">Name</th><th onclick="setSort('address')">Address</th>
      <th onclick="setSort('phone')">Phone</th><th onclick="setSort('website')">Website</th>
      <th onclick="setSort('search')">Search</th><th>Social media</th><th onclick="setSort('email')">Email</th><th>Map</th>
    </tr></thead>
    <tbody id="tbody"></tbody>
  </table></div>
</section>

</main>
<script>
let ALL = [], VIEW = [], lastCount = -1, lastVer = -1, polling = null;
const $ = id => document.getElementById(id);
const SOCIAL = /(facebook|instagram|linktr\.ee|tiktok|twitter|x\.com|youtube|linkedin|vk\.com|draugiem|tripadvisor|booking\.com|wolt|bolt\.eu|foursquare)/i;

function esc(s){const d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML}
function digits(p){return (p||'').replace(/\D/g,'')}
function isMobile(p){let d=digits(p); if(d.startsWith('371'))d=d.slice(3); return d.length===8&&d[0]==='2'}
const PLATFORMS=[['facebook','FB'],['instagram','IG'],['tiktok','TT'],['linkedin','IN'],['youtube','YT'],['twitter','X']];
function hasSocial(r){return PLATFORMS.some(p=>r[p[0]])}
function socialCell(r){
  const links=PLATFORMS.filter(p=>r[p[0]]).map(p=>`<a href="${esc(r[p[0]])}" target="_blank" rel="noopener" title="${esc(r[p[0]])}">${p[1]}</a>`);
  return '<td>'+links.join(' &middot; ')+'</td>';
}
function webType(w){if(!w)return 'none'; return SOCIAL.test(w)?'social':'own'}

async function startJob(){
  const body={category:$('category').value,areas:$('areas').value,queries:$('queries').value,
    limit:$('limit').value,headless:$('headless').checked,find_social:$('findSocial').checked};
  const r=await fetch('/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json();
  if(!j.ok){alert(j.error);return}
  ALL=[];lastCount=-1;applyFilters();startPolling();
}
async function stopJob(){await fetch('/stop',{method:'POST'});}

function startPolling(){ if(polling)clearInterval(polling); polling=setInterval(poll,1500); poll(); }
async function poll(){
  const s=await (await fetch('/status')).json();
  $('statusTxt').textContent=s.status;
  $('countTxt').textContent=s.count+' results';
  $('startBtn').disabled=s.running; $('stopBtn').disabled=!s.running;
  const pct=s.total_urls?Math.min(100,Math.round(s.done/s.total_urls*100)):0;
  $('barFill').style.width=pct+'%';
  const lg=$('log'); lg.textContent=s.log.join('\n'); lg.scrollTop=lg.scrollHeight;
  if(s.count!==lastCount||s.version!==lastVer){
    lastCount=s.count;lastVer=s.version;
    const r=await (await fetch('/results')).json(); ALL=r.rows; refreshSearchOptions(); applyFilters();
  }
  if(!s.running && polling){clearInterval(polling);polling=null;}
}

function refreshSearchOptions(){
  const sel=$('fSearch'), cur=sel.value;
  const vals=[...new Set(ALL.map(r=>r.search))];
  sel.innerHTML='<option value="">All</option>'+vals.map(v=>`<option>${esc(v)}</option>`).join('');
  sel.value=cur;
}

function applyFilters(){
  const name=$('fName').value.toLowerCase().trim();
  const ex=$('fExName').value.toLowerCase().split(',').map(s=>s.trim()).filter(Boolean);
  const addr=$('fAddr').value.toLowerCase().trim();
  const search=$('fSearch').value, ph=$('fPhone').value, web=$('fWeb').value;
  const chain=$('fChain').value, comp=$('fComplete').value, sort=$('fSort').value;
  const soc=$('fSocial').value, em=$('fEmail').value;
  const counts={}; ALL.forEach(r=>{const k=r.name.toLowerCase();counts[k]=(counts[k]||0)+1});

  VIEW=ALL.filter(r=>{
    const n=r.name.toLowerCase();
    if(name&&!n.includes(name))return false;
    if(ex.some(e=>n.includes(e)))return false;
    if(addr&&!(r.address||'').toLowerCase().includes(addr))return false;
    if(search&&r.search!==search)return false;
    if(ph==='has'&&!r.phone)return false;
    if(ph==='none'&&r.phone)return false;
    if(ph==='mobile'&&!isMobile(r.phone))return false;
    const wt=webType(r.website);
    if(web==='has'&&wt==='none')return false;
    if(web==='none'&&wt!=='none')return false;
    if(web==='own'&&wt!=='own')return false;
    if(web==='social'&&wt!=='social')return false;
    if(chain==='unique'&&counts[n]>1)return false;
    if(chain==='chain'&&counts[n]<2)return false;
    if(comp==='all'&&!(r.phone&&r.website))return false;
    if(comp==='phoneNoWeb'&&!(r.phone&&!r.website))return false;
    if(soc==='has'&&!hasSocial(r))return false;
    if(soc==='none'&&hasSocial(r))return false;
    if(soc&&!['has','none'].includes(soc)&&!r[soc])return false;
    if(em==='has'&&!r.email)return false;
    if(em==='none'&&r.email)return false;
    return true;
  });
  if(sort)VIEW.sort((a,b)=>(a[sort]||'').localeCompare(b[sort]||''));
  render();
}

function setSort(col){$('fSort').value=['name','address','search'].includes(col)?col:'';
  if(col==='phone'||col==='website'){VIEW.sort((a,b)=>(a[col]||'').localeCompare(b[col]||''));render();return}
  applyFilters()}

function render(){
  $('shownTxt').textContent=`Showing ${VIEW.length} of ${ALL.length}`;
  $('tbody').innerHTML=VIEW.map(r=>`<tr>
    <td>${esc(r.name)}</td><td class="wrap">${esc(r.address)}</td><td>${esc(r.phone)}</td>
    <td>${r.website?`<a href="${esc(r.website)}" target="_blank" rel="noopener">${esc(r.website.replace(/^https?:\/\/(www\.)?/,'').slice(0,40))}</a>`:''}</td>
    <td><span class="pill">${esc(r.search)}</span></td>
    ${socialCell(r)}<td>${esc(r.email)}</td>
    <td><a href="${esc(r.maps_url)}" target="_blank" rel="noopener">open</a></td></tr>`).join('');
}

function clearFilters(){
  ['fName','fExName','fAddr'].forEach(i=>$(i).value='');
  ['fSearch','fPhone','fWeb','fChain','fComplete','fSort','fSocial','fEmail'].forEach(i=>$(i).value='');
  applyFilters();
}
['fName','fExName','fAddr'].forEach(i=>$(i).addEventListener('input',applyFilters));
['fSearch','fPhone','fWeb','fChain','fComplete','fSort','fSocial','fEmail'].forEach(i=>$(i).addEventListener('change',applyFilters));

function exportCSV(){
  const cols=['name','address','phone','website','facebook','instagram','tiktok','linkedin','youtube','twitter','email','maps_url','search'];
  const q=v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"';
  const csv='\uFEFF'+[cols.join(',')].concat(VIEW.map(r=>cols.map(c=>q(r[c])).join(','))).join('\r\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
  a.download='leads_filtered.csv';a.click();
}
function copyCol(c){
  const t=VIEW.map(r=>r[c]).filter(Boolean).join('\n');
  navigator.clipboard.writeText(t).then(()=>alert(`Copied ${t?t.split('\n').length:0} ${c} values`));
}

// resume view if a job is already running (page refresh)
poll().then(()=>{});
</script></body></html>
"""

if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
