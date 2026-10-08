import datetime as dt
import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from werkzeug.security import generate_password_hash, check_password_hash

SECRET = "change-this-secret"  # production mein environment variable use karo
engine = create_engine("sqlite:///jobs.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ---------- DATABASE TABLES ----------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    company = Column(String, nullable=False)
    role = Column(String, nullable=False)
    status = Column(String, default="Applied")
    owner_id = Column(Integer, ForeignKey("users.id"))


Base.metadata.create_all(engine)

app = FastAPI(title="Job Application Tracker")
oauth2 = OAuth2PasswordBearer(tokenUrl="login")


class RegisterIn(BaseModel):
    email: str
    password: str


class JobIn(BaseModel):
    company: str
    role: str
    status: str = "Applied"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        uid = int(jwt.decode(token, SECRET, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, uid)
    if not user:
        raise HTTPException(401, "User not found")
    return user


# ---------- AUTH APIs ----------
@app.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    if "@" not in body.email or len(body.password) < 4:
        raise HTTPException(400, "Enter a valid email and a password of 4+ characters")
    if db.query(User).filter_by(email=body.email).first():
        raise HTTPException(400, "Email already registered")
    db.add(User(email=body.email, password_hash=generate_password_hash(body.password)))
    db.commit()
    return {"message": "registered"}


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=form.username).first()
    if not user or not check_password_hash(user.password_hash, form.password):
        raise HTTPException(401, "Wrong email or password")
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2)
    token = jwt.encode({"sub": str(user.id), "exp": exp}, SECRET, algorithm="HS256")
    return {"access_token": token, "token_type": "bearer"}


# ---------- JOB APIs (sirf login kiye hue user ke liye) ----------
@app.post("/jobs", status_code=201)
def create_job(body: JobIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = Job(**body.model_dump(), owner_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"id": job.id, **body.model_dump()}


@app.get("/jobs")
def list_jobs(user: User = Depends(current_user), db: Session = Depends(get_db)):
    jobs = db.query(Job).filter_by(owner_id=user.id).order_by(Job.id.desc()).all()
    return [{"id": j.id, "company": j.company, "role": j.role, "status": j.status} for j in jobs]


@app.put("/jobs/{job_id}")
def update_job(job_id: int, body: JobIn, user: User = Depends(current_user),
               db: Session = Depends(get_db)):
    job = db.query(Job).filter_by(id=job_id, owner_id=user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    job.company, job.role, job.status = body.company, body.role, body.status
    db.commit()
    return {"id": job.id, **body.model_dump()}


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter_by(id=job_id, owner_id=user.id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    db.delete(job)
    db.commit()
    return {"deleted": job_id}


# ---------- FRONTEND ----------
PAGE = """
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobTrack - Job Application Tracker</title>
<style>
 *{box-sizing:border-box}
 body{margin:0;font-family:'Segoe UI',Arial,sans-serif;color:#1f2540;min-height:100vh;padding:24px 14px;
  background:linear-gradient(135deg,#ff6a88 0%,#8e44ad 55%,#3a7bd5 100%)}
 .wrap{max-width:1100px;margin:auto}
 .top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
 h1{color:#fff;margin:0;font-size:2rem}
 .sub{color:#f3e6ff;margin:4px 0 20px}
 .card{background:#fff;border-radius:18px;padding:20px;box-shadow:0 8px 24px rgba(0,0,0,.18)}
 input,select{width:100%;padding:11px;margin:5px 0;border:2px solid #e3e7f5;border-radius:10px;font-size:1rem;background:#fff}
 input:focus,select:focus{outline:none;border-color:#8e44ad}
 button{border:0;border-radius:10px;padding:11px 16px;font-size:1rem;color:#fff;cursor:pointer}
 button:hover{filter:brightness(1.1)}
 .primary{background:linear-gradient(135deg,#8e44ad,#3a7bd5)}
 .ghost{background:rgba(255,255,255,.25)}
 .auth{max-width:380px;margin:60px auto}
 .auth .btns{display:flex;gap:8px;margin-top:8px}.auth .btns button{flex:1}
 .msg{min-height:22px;font-size:.9rem;color:#d62839;margin-top:6px}.msg.ok{color:#1b9c5a}
 .stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:16px}
 .stat{border-radius:16px;padding:16px;color:#fff;box-shadow:0 8px 20px rgba(0,0,0,.18)}
 .stat b{display:block;font-size:1.8rem}
 .add{display:grid;grid-template-columns:1fr 1fr 180px auto;gap:8px;align-items:center;margin-bottom:16px}
 @media(max-width:760px){.add{grid-template-columns:1fr}}
 .board{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px}
 .col{background:#f6f7fd;border-radius:16px;padding:12px;min-height:160px}
 .col h4{margin:4px 0 10px;display:flex;justify-content:space-between}
 .col h4 span{background:#fff;border-radius:20px;padding:0 10px}
 .job{background:#fff;border-radius:12px;padding:12px;margin-bottom:10px;box-shadow:0 3px 10px rgba(0,0,0,.08)}
 .job b{display:block}.job small{color:#6b7394}
 .job .acts{display:flex;gap:6px;margin-top:8px}
 .job select{margin:0;padding:6px;font-size:.9rem}
 .del{background:#ffe3e6;color:#d62839;padding:6px 10px}
 .empty{color:#8b93b5;text-align:center;font-size:.9rem}
 .hide{display:none}
</style></head>
<body><div class="wrap">

 <div id="auth" class="card auth">
  <h2 style="margin-top:0">Welcome to JobTrack</h2>
  <p style="color:#6b7394">Login or create an account to track your job applications.</p>
  <input id="em" type="email" placeholder="Email">
  <input id="pw" type="password" placeholder="Password (min 4 characters)">
  <div class="msg" id="amsg"></div>
  <div class="btns">
   <button class="primary" onclick="login()">Login</button>
   <button style="background:#2ecc71" onclick="register()">Register</button>
  </div>
 </div>

 <div id="app" class="hide">
  <div class="top">
   <div><h1>JobTrack</h1><p class="sub">Har application ka hisaab, ek jagah</p></div>
   <button class="ghost" onclick="logout()">Logout</button>
  </div>
  <div class="stats" id="stats"></div>
  <div class="card add">
   <input id="co" placeholder="Company (e.g. TCS)">
   <input id="ro" placeholder="Role (e.g. Python Developer)">
   <select id="st"></select>
   <button class="primary" onclick="addJob()">Add job</button>
  </div>
  <div class="msg" id="jmsg" style="color:#fff"></div>
  <div class="board" id="board"></div>
 </div>
</div>

<script>
const ST=['Applied','Interview','Selected','Rejected'];
const COL={Applied:'#2196f3',Interview:'#ff9800',Selected:'#2ecc71',Rejected:'#e74c3c'};
const ICO={Applied:'📨',Interview:'🎤',Selected:'🎉',Rejected:'❌'};
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
let token=localStorage.getItem('tok')||'', JOBS=[];
$('st').innerHTML=ST.map(s=>`<option>${s}</option>`).join('');

function amsg(t,ok){$('amsg').textContent=t;$('amsg').className='msg'+(ok?' ok':'');}

async function api(path,opts={}){
  opts.headers=Object.assign({},opts.headers,{Authorization:'Bearer '+token});
  const r=await fetch(path,opts);
  if(r.status===401){logout();}
  return r;
}
async function login(){
  const r=await fetch('/login',{method:'POST',
    body:new URLSearchParams({username:$('em').value,password:$('pw').value})});
  if(!r.ok){amsg('Wrong email or password');return;}
  token=(await r.json()).access_token;
  localStorage.setItem('tok',token);
  show();
}
async function register(){
  const r=await fetch('/register',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email:$('em').value,password:$('pw').value})});
  const d=await r.json();
  if(!r.ok){amsg(typeof d.detail==='string'?d.detail:'Enter a valid email and password');return;}
  amsg('Account created! Now click Login.',true);
}
function logout(){token='';localStorage.removeItem('tok');$('app').classList.add('hide');$('auth').classList.remove('hide');}
function show(){$('auth').classList.add('hide');$('app').classList.remove('hide');load();}

async function load(){
  const r=await api('/jobs'); if(!r.ok)return;
  JOBS=await r.json();
  $('stats').innerHTML=`<div class="stat" style="background:linear-gradient(135deg,#667eea,#764ba2)"><b>${JOBS.length}</b>Total applied</div>`+
    ST.map(s=>`<div class="stat" style="background:${COL[s]}"><b>${JOBS.filter(j=>j.status===s).length}</b>${ICO[s]} ${s}</div>`).join('');
  $('board').innerHTML=ST.map(s=>{
    const items=JOBS.filter(j=>j.status===s);
    return `<div class="col" style="border-top:6px solid ${COL[s]}">
      <h4>${ICO[s]} ${s}<span>${items.length}</span></h4>
      ${items.map(j=>`<div class="job"><b>${esc(j.company)}</b><small>${esc(j.role)}</small>
        <div class="acts"><select onchange="move(${j.id},this.value)">
        ${ST.map(x=>`<option ${x===j.status?'selected':''}>${x}</option>`).join('')}</select>
        <button class="del" onclick="del(${j.id})">✕</button></div></div>`).join('')||'<div class="empty">Nothing here yet</div>'}
    </div>`;}).join('');
}
async function addJob(){
  $('jmsg').textContent='';
  if(!$('co').value.trim()||!$('ro').value.trim()){$('jmsg').textContent='Enter company and role';return;}
  await api('/jobs',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({company:$('co').value.trim(),role:$('ro').value.trim(),status:$('st').value})});
  $('co').value='';$('ro').value='';load();
}
async function move(id,status){
  const j=JOBS.find(x=>x.id===id);
  await api('/jobs/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({company:j.company,role:j.role,status})});
  load();
}
async function del(id){await api('/jobs/'+id,{method:'DELETE'});load();}

if(token)show();
</script></body></html>
"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home():
    return PAGE