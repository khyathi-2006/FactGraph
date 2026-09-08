from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse

from factlayer.storage import *
from factlayer.config import UPLOAD_DIR
from factlayer.orchestrator import ingest_pdf, classify_all

app = FastAPI(title="FactGraph", version="1.0.0")


def db():
    connection = connect()
    initialize_schema(connection)
    return connection


@app.get("/api/documents")
def documents():
    return [x.model_dump() for x in list_documents(db())]


@app.get("/api/facts")
def facts(document_id: str | None = None):
    return [x.model_dump() for x in list_facts(db(), document_id=document_id)]


@app.get("/api/facts/{fact_id}/evidence")
def evidence(fact_id: str):
    item = get_evidence_for_fact(db(), fact_id)
    if not item:
        raise HTTPException(404, "Evidence not found")
    return item.model_dump()


@app.get("/api/relationships")
def relationships(include_unrelated: bool = False):
    return [x.model_dump() for x in list_relationships(db(), include_unrelated=include_unrelated)]


@app.get("/api/issues")
def issues():
    connection = db()
    rows = connection.execute(
        "SELECT issue_id, document_id, stage, page, detail, created_at "
        "FROM pipeline_issues ORDER BY issue_id DESC LIMIT 100"
    ).fetchall()
    return [dict(row) for row in rows]


@app.post("/api/upload")
def upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / Path(file.filename).name
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    try:
        document_id, facts_found, _ = ingest_pdf(target, db())
        return {
            "document_id": document_id,
            "status": "completed",
            "fact_count": len(facts_found),
        }
    except Exception as error:
        raise HTTPException(500, str(error))
    finally:
        try:
            if target.exists():
                target.unlink()
        except OSError:
            pass


@app.post("/api/classify")
def classify():
    relationships_found = classify_all(db())
    return {"relationships": [x.model_dump() for x in relationships_found]}


@app.get("/", response_class=HTMLResponse)
def home():
    return '''<!doctype html>
<html><head><title>FactGraph</title>
<style>
body{font-family:Arial,sans-serif;max-width:1150px;margin:32px auto;padding:0 20px;background:#fafafa;color:#222}
table{border-collapse:collapse;width:100%;margin:12px 0;background:white}td,th{border:1px solid #ddd;padding:8px;text-align:left;font-size:14px}th{background:#f1f3f5}
button,input{padding:9px;margin:4px}button{cursor:pointer}.message{padding:10px;margin:10px 0;border-radius:4px}.ok{background:#e8f5e9;color:#1b5e20}.error{background:#ffebee;color:#b71c1c}.muted{color:#666;font-size:13px}
</style></head><body>
<h1>FactGraph</h1><p>Evidence-based PDF fact extraction and relationship discovery.</p>
<form id="uploadForm"><input type="file" name="file" accept=".pdf" required><button type="submit">Upload & ingest</button></form>
<button id="classifyButton">Classify relationships</button>
<div id="message"></div>
<h2>Documents</h2><div id="documents"></div>
<h2>Facts</h2><div id="facts"></div>
<h2>Relationships</h2><div id="relationships"></div>
<h2>Pipeline Issues</h2><div id="issues" class="muted">No issues loaded.</div>
<script>
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function showMessage(text,type='ok'){document.getElementById('message').innerHTML='<div class="message '+type+'">'+esc(text)+'</div>'}
function table(rows,cols){return '<table><tr>'+cols.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr>'+rows.map(o=>'<tr>'+cols.map(c=>'<td>'+esc(o[c])+'</td>').join('')+'</tr>').join('')+'</table>'}
async function api(url,options){const r=await fetch(url,options);const data=await r.json().catch(()=>({detail:'Invalid server response'}));if(!r.ok)throw new Error(data.detail||'Request failed');return data}
async function load(){
 try{
  const [docs,facts,rels,issues]=await Promise.all([api('/api/documents'),api('/api/facts'),api('/api/relationships'),api('/api/issues')]);
  document.getElementById('documents').innerHTML=table(docs,['filename','page_count','status','status_detail','fact_count']);
  document.getElementById('facts').innerHTML=table(facts,['subject','predicate','value','period_label']);
  document.getElementById('relationships').innerHTML=table(rels,['relation','reasoning','confidence']);
  document.getElementById('issues').innerHTML=issues.length?table(issues,['stage','page','detail','created_at']):'No pipeline issues.';
 }catch(e){showMessage(e.message,'error')}
}
document.getElementById('uploadForm').onsubmit=async e=>{e.preventDefault();showMessage('Uploading and processing PDF...');try{const data=await api('/api/upload',{method:'POST',body:new FormData(e.target)});showMessage('Completed: '+data.fact_count+' facts extracted.');e.target.reset();await load()}catch(err){showMessage('Upload/ingestion failed: '+err.message,'error');await load()}};
document.getElementById('classifyButton').onclick=async()=>{try{const data=await api('/api/classify',{method:'POST'});showMessage('Classification completed: '+data.relationships.length+' relationships added.');await load()}catch(err){showMessage('Classification failed: '+err.message,'error')}};
load();
</script></body></html>'''
